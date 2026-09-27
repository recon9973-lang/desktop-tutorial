#!/usr/bin/env python3
"""행정안전부 주민등록 인구를 **API 로** 받아 온다(러너 전용).

왜 만드나: 인구는 달마다 바뀐다. 손으로 파일을 올리면 그때뿐이고 다음 달이면 낡는다.
사장님 지시 2026-09-27: «인구는 계속 변하는 데이터인데, 파일로 올리는건 장기적 관점에서
허점이 많아. api 데이터 활용 방안을 마련해»

지금까지 인구는 ANSEO 사본에 들어 있는 파일을 읽어 쓰고 있다. 그 사본에 세종이 통째로
빠져 있어 세종만 손으로 채웠다. API 로 바꾸면 그 구멍도 메워지고 달마다 새로 받을 수 있다.

[실측 2026-09-26] `apis.data.go.kr/1741000/admmPpltnHhStus` 는 https/http × 경로 셋 ×
값 꼴 셋 = 열두 번 모두 무응답이었다. 그래서 **주소를 외워 쓰지 않고 두드려 찾는다.**

`--mode probe` 로 어느 주소가 답하는지 먼저 알아내고, 알아낸 대로 `--mode collect` 한다.
"""
import argparse, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

OUT = pathlib.Path("data/market")
RAW = OUT / "raw"
KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
calls = 0


def get(url: str, timeout: int = 20, cap: int | None = 3000):
    global calls
    calls += 1
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, (body[:cap] if cap else body), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:cap or 3000], time.time() - t0
    except Exception as e:                                   # noqa: BLE001
        return 0, str(e).encode(), time.time() - t0


def k() -> str:
    return KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")


# ── 두드려 볼 곳 ────────────────────────────────────────────────────────────
# 셋으로 나눈다: ① 호스트가 살아 있나 ② 자료 목록을 물어볼 수 있나
# ③ 인구 자료 자체를 받을 수 있나. ①이 죽으면 ②③은 볼 것도 없다.
HOSTS = ["https://apis.data.go.kr", "https://api.odcloud.kr",
         "https://www.data.go.kr", "https://kosis.kr",
         "https://sgisapi.kostat.go.kr"]

# 파일 자료를 포털이 API 로 바꿔 주는 통로. 자료번호로 부른다.
#   15097972 지역별(행정동) 성별 연령별 주민등록 인구수  ← 나이대가 여기 있다
#   15108065 행정동별(통반단위) 주민등록 인구 및 세대현황 ← 동별 인구·남녀
#   15059351 공공데이터포털목록조회서비스              ← 주소를 «찾는» 데 쓴다
ODCLOUD = ["15097972", "15108065", "15107303", "15059351"]

# 기관이 직접 여는 통로. 앞 판에서 무응답이던 것도 한 번 더 본다(그때는 답이 없었다고만 안다).
AGENCY = [
    "https://apis.data.go.kr/1741000/admmPpltnHhStus/getAdmmPpltnHhStus",
    "https://apis.data.go.kr/1741000/admmSexdstnAgrdePpltnStus/getAdmmSexdstnAgrdePpltnStus",
    "https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList",
]


def probe() -> int:
    print(f"열쇠 {'있음' if KEY else '없음'}\n")
    tried = []

    def note(무엇, url, st, body, sec, 메모=""):
        txt = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
        row = {"무엇": 무엇, "주소": url.replace(k(), "<열쇠>"), "http": st,
               "걸린초": round(sec, 1), "맛보기": " ".join(txt.split())[:300], "메모": 메모}
        tried.append(row)
        print(f"[{st:>3}] {sec:5.1f}s {무엇:<34} {row['맛보기'][:110]}")

    print("── ① 호스트가 답하나 ──")
    for h in HOSTS:
        st, b, s = get(h, timeout=12, cap=200)
        note(f"호스트 {h.split('//')[1]}", h, st, b, s)

    print("\n── ② 파일 자료를 API 로 (api.odcloud.kr) ──")
    for lid in ODCLOUD:
        for path in (f"/api/{lid}/v1", f"/api/{lid}/v1/uddi:"):
            url = f"https://api.odcloud.kr{path}?page=1&perPage=5&serviceKey={k()}"
            st, b, s = get(url)
            note(f"odcloud {lid}{path[len('/api/'+lid):]}", url, st, b, s)

    print("\n── ③ 기관이 직접 여는 통로 ──")
    for base in AGENCY:
        url = (f"{base}?serviceKey={k()}&type=json&pageNo=1&numOfRows=5"
               f"&pIndex=1&pSize=5")
        st, b, s = get(url, timeout=25)
        note(f"기관 {base.split('/')[-1]}", url, st, b, s)

    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "pop_probe.json").write_text(
        json.dumps({"시도한 것": tried, "두드린 날": time.strftime("%Y-%m-%d")},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [t for t in tried if t["http"] == 200]
    print(f"\n답한 곳 {len(ok)}개:")
    for t in ok:
        print(f"  {t['무엇']} — {t['맛보기'][:150]}")
    print(f"호출 {calls}회 → {RAW/'pop_probe.json'}")
    return 0


# 소개 화면에서 주소를 읽어 올 자료들. 번호는 포털 주소에 그대로 들어 있다.
PAGES = {
    "15097972": "지역별(행정동) 성별 연령별 주민등록 인구수",
    "15108065": "행정동별(통반단위) 주민등록 인구 및 세대현황",
    "15107303": "통계연보_지역별 주민등록인구",
    "15108092": "도로명별 주민등록 인구 및 세대현황",
    "15051059": "심평원_전국 병의원 및 약국 현황",
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def find() -> int:
    """포털 **소개 화면에서 요청주소를 읽어 온다** — 외워 쓰지 않는다.

    [실측 2026-09-27 · 러너] `www.data.go.kr` 이 200 으로 답한다(2026-09-18 에는
    안 열렸다고 적혀 있었다 — 그때는 정말 안 열렸는지 다시 봐야 한다).
    화면 글 속에 `apis.data.go.kr/...` 과 `api.odcloud.kr/api/<번호>/v1/uddi:<긴번호>`
    가 그대로 들어 있어, 그것을 뽑아 두면 다음부터 기계가 바로 부를 수 있다.
    """
    found = {}
    for pk, nm in PAGES.items():
        got = {"이름": nm, "주소후보": [], "uddi": [], "오퍼레이션": []}
        for kind in ("openapi", "fileData"):
            url = f"https://www.data.go.kr/data/{pk}/{kind}.do"
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept-Language": "ko"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    st, html = r.status, r.read().decode("utf-8", "replace")
            except Exception as e:                          # noqa: BLE001
                print(f"  [{pk} {kind}] 못 열었다 — {e}"); continue
            got["주소후보"] += re.findall(r"https?://apis?\.(?:data\.go\.kr|odcloud\.kr)"
                                      r"[A-Za-z0-9_\-/.:]{4,120}", html)
            got["uddi"] += re.findall(r"uddi:[0-9a-fA-F\-]{8,60}", html)
            got["오퍼레이션"] += re.findall(r"\bget[A-Z][A-Za-z0-9]{3,40}\b", html)
            print(f"  [{st}] {pk} {kind} — 글자 {len(html):,} · "
                  f"주소 {len(got['주소후보'])} · uddi {len(got['uddi'])}")
        for key in ("주소후보", "uddi", "오퍼레이션"):
            got[key] = sorted(set(got[key]))[:12]
        found[pk] = got
        print(f"{pk} {nm}")
        for key in ("주소후보", "uddi", "오퍼레이션"):
            if got[key]:
                print(f"   {key}: {got[key]}")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "pop_endpoints.json").write_text(
        json.dumps({"찾은 것": found, "찾은 날": time.strftime("%Y-%m-%d"),
                    "어디서": "공공데이터포털 소개 화면(www.data.go.kr)"},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {RAW/'pop_endpoints.json'}")
    return 0


def call_odcloud(pk: str, uddi: str, page: int = 1, per: int = 5,
                 extra: dict = None, cap: int | None = 2500):
    """cap 은 «맛보기만 볼 때» 쓴다. 받아 담을 때는 반드시 통째로 읽는다 —
    [실측 2026-09-27] 2,500바이트에서 자르는 바람에 200 으로 잘 온 답을
    «망가진 글» 로 읽고 한 판이 접혔다. 상가정보 때도 같은 실수를 했다(4,000바이트)."""
    q = {"page": page, "perPage": per, "serviceKey": KEY}
    q.update(extra or {})
    url = (f"https://api.odcloud.kr/api/{pk}/v1/{uddi}?"
           + urllib.parse.urlencode(q, quote_via=urllib.parse.quote))
    return url, *get(url, timeout=90, cap=cap)


def try_them() -> int:
    """찾아 둔 주소로 실제로 불러 본다. 무엇이 «주소가 틀림»이고 무엇이
    «활용신청이 안 됨»인지 갈라 적는다 — 고칠 사람이 다르기 때문이다."""
    src = RAW / "pop_endpoints.json"
    if not src.exists():
        print("찾아 둔 주소가 없다 — `--mode find` 를 먼저 돌린다"); return 2
    found = json.loads(src.read_text(encoding="utf-8"))["찾은 것"]
    out = []
    for pk, g in found.items():
        for uddi in g["uddi"]:
            url, st, body, sec = call_odcloud(pk, uddi)
            txt = body.decode("utf-8", "replace")
            flat = " ".join(txt.split())
            판정 = ("받아진다" if st == 200 else
                  "활용신청이 안 됐다" if "등록되지" in flat or "NOT_REGISTERED" in flat
                  else "주소가 틀렸다" if "없습니다" in flat or "not found" in flat.lower()
                  else f"http {st}")
            out.append({"자료번호": pk, "이름": g["이름"], "uddi": uddi,
                        "http": st, "판정": 판정, "맛보기": flat[:400]})
            print(f"[{st:>3}] {pk} {g['이름'][:28]:<28} {판정:<16} {flat[:110]}")
    (RAW / "pop_try.json").write_text(
        json.dumps({"불러 본 것": out, "불러 본 날": time.strftime("%Y-%m-%d")},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [o for o in out if o["http"] == 200]
    need = [o for o in out if o["판정"] == "활용신청이 안 됐다"]
    print(f"\n받아지는 자료 {len(ok)}개 · 활용신청이 필요한 자료 {len(need)}개")
    for o in need:
        print(f"   신청할 것: https://www.data.go.kr/data/{o['자료번호']}/  ({o['이름']})")
    print(f"→ {RAW/'pop_try.json'}")
    return 0


# 인구를 받아 올 자료. [실측 2026-09-27] 이 주소는 «열쇠가 신청 안 됐다»(-4)로 답했다 —
# 주소 자체는 맞다는 뜻이다(다른 자료들은 «서비스가 없다»(-3)로 답했다).
POP_PK = "15097972"
POP_UDDI = "uddi:5beebd9e-8733-44f8-817f-9cfa03548b7a"


def collect(limit: int) -> int:
    """행정동 × 성별 × 연령 인구를 통째로 받아 `raw/pop_rows.jsonl` 에 쌓는다.

    **칸 이름을 외워 쓰지 않는다** — 첫 장을 받아 «무슨 칸이 오는지» 적어 두고,
    표로 짜는 일(`build_pop.py`)은 그것을 보고 한다. 끊기면 이어받는다.
    """
    path = RAW / "pop_rows.jsonl"
    RAW.mkdir(parents=True, exist_ok=True)
    done = sum(1 for _ in path.open(encoding="utf-8")) if path.exists() else 0
    per = 1000
    page = done // per + 1
    print(f"이미 받은 줄 {done:,} → {page}쪽부터 (한 쪽 {per}줄)")

    url, st, body, sec = call_odcloud(POP_PK, POP_UDDI, page=1, per=1, cap=None)
    if st != 200:
        txt = body.decode("utf-8", "replace")
        print(f"못 받는다 [{st}] {txt[:200]}")
        print(f"→ 활용신청: https://www.data.go.kr/data/{POP_PK}/fileData.do "
              f"(오른쪽 위 「활용신청」 · 사장님 브라우저에서만 된다)")
        return 2
    first = json.loads(body.decode("utf-8", "replace"))
    total = first.get("totalCount")
    cols = sorted((first.get("data") or [{}])[0].keys())
    print(f"전체 {total:,}줄 · 칸 {len(cols)}개")
    print("칸 이름: " + ", ".join(cols))
    (RAW / "pop_columns.json").write_text(
        json.dumps({"칸": cols, "전체줄수": total, "자료번호": POP_PK,
                    "받은 날": time.strftime("%Y-%m-%d"),
                    "출처": "행정안전부 지역별(행정동) 성별 연령별 주민등록 인구수 "
                          "· 공공데이터포털"}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    n = 0
    with path.open("a", encoding="utf-8") as f:
        while done < (total or 0):
            if n >= limit:
                print("한도 도달 — 다음 판에서 이어받는다"); break
            url, st, body, sec = call_odcloud(POP_PK, POP_UDDI, page=page, per=per,
                                              cap=None)
            n += 1
            if st != 200:
                print(f"[{st}] {page}쪽에서 멈췄다 — {body[:160]}"); break
            rows = json.loads(body.decode("utf-8", "replace")).get("data") or []
            if not rows:
                print(f"{page}쪽이 비었다 — 끝"); break
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            done += len(rows); page += 1
            print(f"  {page-1}쪽 {len(rows)}줄 (누적 {done:,}/{total:,})")
            f.flush()
            time.sleep(0.1)
    print(f"호출 {calls}회 → {path} ({done:,}줄)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="probe",
                    choices=["probe", "find", "try", "collect"])
    ap.add_argument("--limit", type=int, default=200, help="이번 판에 받을 쪽 수")
    a = ap.parse_args()
    if a.mode == "find":
        return find()               # 이 길은 열쇠가 없어도 된다
    if a.mode in ("try", "collect"):
        if not KEY:
            print("DATA_GO_KR_SERVICE_KEY 없음 — 중단"); return 2
        return try_them() if a.mode == "try" else collect(a.limit)
    if not KEY:
        print("DATA_GO_KR_SERVICE_KEY 없음 — 중단"); return 2
    return probe()


if __name__ == "__main__":
    sys.exit(main())
