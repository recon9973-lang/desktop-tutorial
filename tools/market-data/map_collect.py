#!/usr/bin/env python3
"""네이버·카카오 지도(로컬) API → 지역 × 진료과 «검색 노출 경쟁» 원자료.

심평원 수치가 «실제 개설 기관 수»라면, 이쪽은 «검색했을 때 몇 곳이 잡히는가» —
마케팅에서 실제로 싸우는 면이다. 둘을 나란히 두면 노출 경쟁률이 나온다.

- 네이버 지역검색: 상위 5곳(노출 상위)만. 키 NAVER_CLIENT_ID/SECRET.
  ⚠️ [실측 2026-09-18] 이 API 의 total 은 display 상한에 묶여 5 로 돌아온다 —
  «몇 곳이 있나»를 세는 데는 쓸 수 없다. 밀집도는 심평원, 검색 노출 수는 카카오로 센다.
- 카카오 로컬 키워드검색(category_group_code=HP8=병원):
  meta.total_count + 상위 5곳. 키 KAKAO_REST_API_KEY.
키가 없는 쪽은 조용히 건너뛴다(목업으로 채우지 않는다).

산출: data/market/raw/naver_local.jsonl · data/market/raw/kakao_local.jsonl
"""
import argparse, json, os, pathlib, time, urllib.parse, urllib.request

OUT = pathlib.Path("data/market/raw")
NID, NSEC = os.environ.get("NAVER_CLIENT_ID", ""), os.environ.get("NAVER_CLIENT_SECRET", "")
KAKAO = os.environ.get("KAKAO_REST_API_KEY", "")

# 마케팅에서 실제로 돈이 도는 진료과 위주. 필요하면 --terms 로 바꾼다.
TERMS = ["피부과", "성형외과", "치과", "한의원", "정형외과", "안과", "산부인과",
         "비뇨의학과", "내과", "소아청소년과", "이비인후과", "정신건강의학과",
         "신경외과", "재활의학과", "다이어트 한의원", "치과교정"]


def fetch(url: str, headers: dict, tries: int = 4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                return {"_error": str(e)}
            time.sleep(2 ** i)
    return {"_error": "unreachable"}


def load_done(path: pathlib.Path) -> set:
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                d = json.loads(line); done.add((d["region"], d["term"]))
            except Exception:  # noqa: BLE001
                pass
    return done


def regions() -> list[str]:
    """상권표의 시군구를 «지도에서 찾히는 이름»으로 돌려준다.

    심평원 표기(「고양덕양구」)로는 지도가 못 찾는다. 행안부 정식 표기
    (「고양시 덕양구」)를 쓴 `시군구_정식` 칸을 쓴다.
    """
    import csv
    p = pathlib.Path("data/market/market_sggu.csv")
    if not p.exists():
        return []
    out = []
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nm = (r.get("시군구_정식") or r["시군구"]).strip()
            if nm:
                out.append(f"{r['시도']} {nm}")
    return sorted(set(out))


def run_naver(regs, terms, limit):
    if not (NID and NSEC):
        print("[naver] 키 없음 — 건너뜀"); return
    path = OUT / "naver_local.jsonl"; done = load_done(path); n = 0
    with path.open("a", encoding="utf-8") as f:
        for reg in regs:
            for t in terms:
                if (reg, t) in done:
                    continue
                if n >= limit:
                    print("[naver] 한도 도달 — 다음 실행에서 이어받는다"); return
                q = urllib.parse.quote(f"{reg} {t}")
                d = fetch(f"https://openapi.naver.com/v1/search/local.json?query={q}&display=5",
                          {"X-Naver-Client-Id": NID, "X-Naver-Client-Secret": NSEC})
                n += 1
                rec = {"region": reg, "term": t,
                       "total": d.get("total"), "error": d.get("_error"),
                       "top": [{"name": i.get("title", "").replace("<b>", "").replace("</b>", ""),
                                "category": i.get("category"), "address": i.get("roadAddress")}
                               for i in d.get("items", [])]}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
                time.sleep(0.12)
            print(f"  [naver] {reg} (누적 {n})")


def run_kakao(regs, terms, limit):
    if not KAKAO:
        print("[kakao] KAKAO_REST_API_KEY 없음 — 건너뜀(키를 저장소 시크릿에 넣으면 같이 받는다)")
        return
    path = OUT / "kakao_local.jsonl"; done = load_done(path); n = 0
    with path.open("a", encoding="utf-8") as f:
        for reg in regs:
            for t in terms:
                if (reg, t) in done:
                    continue
                if n >= limit:
                    print("[kakao] 한도 도달 — 다음 실행에서 이어받는다"); return
                q = urllib.parse.quote(f"{reg} {t}")
                d = fetch("https://dapi.kakao.com/v2/local/search/keyword.json"
                          f"?query={q}&category_group_code=HP8&size=5",
                          {"Authorization": f"KakaoAK {KAKAO}"})
                n += 1
                meta = d.get("meta", {}) if isinstance(d, dict) else {}
                rec = {"region": reg, "term": t,
                       "total": meta.get("total_count"), "pageable": meta.get("pageable_count"),
                       "error": d.get("_error"),
                       "top": [{"name": i.get("place_name"), "category": i.get("category_name"),
                                "address": i.get("road_address_name"),
                                "x": i.get("x"), "y": i.get("y")}
                               for i in d.get("documents", [])]}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
                time.sleep(0.08)
            print(f"  [kakao] {reg} (누적 {n})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="both", choices=["naver", "kakao", "both"])
    ap.add_argument("--limit", type=int, default=4000, help="이번 실행 최대 호출 수(소스별)")
    ap.add_argument("--terms", default="", help="쉼표로 구분. 비우면 기본 16개 과목")
    ap.add_argument("--regions", default="", help="쉼표로 구분. 비우면 심평원 마스터의 전 시군구")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    terms = [t.strip() for t in a.terms.split(",") if t.strip()] or TERMS
    regs = [r.strip() for r in a.regions.split(",") if r.strip()] or regions()
    if not regs:
        print("지역 목록이 없다 — 먼저 build_anseo.py 로 data/market/market_sggu.csv 를 만들어라")
        return 2
    print(f"지역 {len(regs)} × 검색어 {len(terms)} = {len(regs)*len(terms):,}쌍")
    if a.source in ("naver", "both"):
        run_naver(regs, terms, a.limit)
    if a.source in ("kakao", "both"):
        run_kakao(regs, terms, a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
