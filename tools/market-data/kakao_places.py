#!/usr/bin/env python3
"""카카오 지도의 병원을 통째로 훑어, 카카오가 붙인 «분류»를 읽는다(러너 전용).

왜 이렇게 하나 [실측 2026-09-19]
  ① 검색어에 지역 이름을 넣는 방식은 안 맞는다 — 「강원 고성군 피부과」 0건,
     「강원 강릉시 한의원」 0건. 지역은 말이 아니라 **좌표**로 줘야 한다.
  ② 좌표 네모만 주면 옆 동네가 섞인다(강남구 네모 9.7×8.3km 안에 서초·송파가 든다).
     그래서 **네모로 훑되, 받은 곳마다 도로명주소의 시군구로 다시 가른다.**
  ③ 카카오는 한 번에 45곳까지만 준다. 그래서 네모를 넷으로 쪼개기를 반복해
     45곳 아래로 내려온 네모만 실제로 훑는다(사분 나누기).

얻는 것: 지도에 오른 병원 한 곳마다 — 이름 · **카카오 분류**(「의료,건강 > 병원 > 피부과」)
· 도로명주소 · 좌표. 심평원의 「내건 과목」과 달리 이것은 **소비자가 지도에서 보는 정체**다.

나가는 곳: data/market/raw/kakao_places.jsonl (이어받기 됨)
"""
import argparse, json, os, pathlib, time, urllib.parse, urllib.request

OUT = pathlib.Path("data/market/raw")
KEY = os.environ.get("KAKAO_REST_API_KEY", "").strip()
API_CAT = "https://dapi.kakao.com/v2/local/search/category.json"
API_KEY_ = "https://dapi.kakao.com/v2/local/search/keyword.json"
PAGE_MAX, SIZE = 3, 15          # 카카오가 한 네모에 주는 최대 = 45곳
KOREA = (124.5, 32.9, 132.1, 38.7)   # 좌하 x,y · 우상 x,y
calls = 0


def get(params: dict, tries: int = 4):
    global calls
    base = API_KEY_ if "query" in params else API_CAT
    url = base + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            calls += 1
            req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {KEY}"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:       # 초당 한도 — 잠깐 쉬고 다시
                time.sleep(1.5 * (i + 1)); continue
            if i == tries - 1:
                return {"_error": f"HTTP {e.code}"}
            time.sleep(1.5 ** i)
        except Exception as e:      # noqa: BLE001
            if i == tries - 1:
                return {"_error": str(e)}
            time.sleep(1.5 ** i)
    return {"_error": "unreachable"}


def rect(b) -> str:
    return f"{b[0]:.6f},{b[1]:.6f},{b[2]:.6f},{b[3]:.6f}"


QUERY = ""   # 비우면 병원 분류(HP8)로 훑고, 채우면 그 낱말로 훑는다(한의원 등).


def _params(box, size, page):
    p = {"rect": rect(box), "size": size, "page": page}
    if QUERY:
        p["query"] = QUERY
    else:
        p["category_group_code"] = "HP8"
    return p


def sweep(box, out, seen, depth=0, max_depth=14, log=None):
    """네모 하나를 훑는다. 45곳을 넘으면 넷으로 쪼갠다."""
    d = get(_params(box, 1, 1))
    if "_error" in d:
        (log or print)(f"  실패 {rect(box)} {d['_error']}")
        return
    total = d.get("meta", {}).get("total_count", 0)
    if total == 0:
        return
    if total > PAGE_MAX * SIZE and depth < max_depth:
        mx, my = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        for q in ((box[0], box[1], mx, my), (mx, box[1], box[2], my),
                  (box[0], my, mx, box[3]), (mx, my, box[2], box[3])):
            sweep(q, out, seen, depth + 1, max_depth, log)
        return
    for page in range(1, PAGE_MAX + 1):
        d = get(_params(box, SIZE, page))
        if "_error" in d:
            break
        for it in d.get("documents", []):
            pid = it.get("id")
            if pid in seen:
                continue
            seen.add(pid)
            out.write(json.dumps({
                "id": pid, "name": it.get("place_name"),
                "cat": it.get("category_name"),
                "addr": it.get("road_address_name") or it.get("address_name"),
                "x": it.get("x"), "y": it.get("y"), "tel": it.get("phone"),
            }, ensure_ascii=False) + "\n")
        if d.get("meta", {}).get("is_end", True):
            break
    out.flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default="", help="시험할 네모 «x1,y1,x2,y2» (비우면 전국)")
    ap.add_argument("--max-depth", type=int, default=14)
    ap.add_argument("--query", default="", help="낱말로 훑기(한의원 등). 비우면 병원 분류로 훑는다")
    ap.add_argument("--out", default="", help="나갈 파일 이름(비우면 자동)")
    a = ap.parse_args()
    if not KEY:
        print("KAKAO_REST_API_KEY 없음 — 중단(지어내지 않는다)"); return 2
    OUT.mkdir(parents=True, exist_ok=True)
    global QUERY
    QUERY = a.query.strip()
    path = OUT / (a.out or (f"kakao_{QUERY}.jsonl" if QUERY else
                            ("kakao_probe.jsonl" if a.probe else "kakao_places.jsonl")))
    seen = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                seen.add(json.loads(line)["id"])
            except Exception:  # noqa: BLE001
                pass
    box = tuple(float(v) for v in a.probe.split(",")) if a.probe else KOREA
    print(f"훑을 네모 {rect(box)} · 이미 받은 곳 {len(seen):,}")
    t0 = time.time()
    with path.open("a", encoding="utf-8") as f:
        sweep(box, f, seen, max_depth=a.max_depth)
    print(f"받은 곳 {len(seen):,} · 호출 {calls:,}회 · {time.time()-t0:.0f}초 → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
