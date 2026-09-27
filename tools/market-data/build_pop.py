#!/usr/bin/env python3
"""API 로 받아 온 인구 원자료 → 행정동 인구표(`data/market/population_dong.csv`).

왜 있나: 인구는 달마다 바뀐다. 파일을 손으로 올리면 그때뿐이라 API 로 바꿨다
(사장님 지시 2026-09-27). 이 표가 있으면 `build_anseo.py` 가 ANSEO 사본 대신 이것을 쓴다.

원자료: `raw/pop_rows.jsonl` — 행정동 한 줄에 계·남자·여자와 **한 살 단위** 나이 칸 222개.
출처: 행정안전부 「지역별(행정동) 성별 연령별 주민등록 인구수」 · 공공데이터포털(15097972)

[실측 2026-09-27] 3,619개 동 · 전국 51,084,159명 · 기준 2026-08-31 ·
**세종 25개 동이 들어 있다**(ANSEO 사본에는 통째로 빠져 있어 손으로 채워야 했다).

이름 맞추기: 이 자료는 2026-07 개편 **뒤** 이름을 쓴다(「전남광주통합특별시」·
인천 제물포구/영종구/검단구/서해구). 표는 개편 **전** 이름 252곳이라 되돌려 맞춘다.
옛 중구·동구는 제물포구·영종구에 섞여 있어 **행정동 이름으로** 가른다.
"""
import collections, csv, gzip, json, pathlib, re, sys

OUT = pathlib.Path("data/market")
RAW = OUT / "raw"
DASH = "—"
SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
              "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
              "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
              "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
              "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
              "경상남도": "경남", "제주특별자치도": "제주"}
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}
RENAME = {("인천", "서해구"): "서구", ("인천", "검단구"): "서구"}
SPLIT_GU = {"제물포구", "영종구"}          # 옛 중구·동구가 섞여 있다
flat = lambda s: re.sub(r"[ .·,]", "", s or "")


def age_of(col: str) -> int | None:
    """「35세남자」 → 35 · 「110세이상 여자」 → 110 · 그 밖은 None."""
    m = re.match(r"^(\d+)세(?:이상)?\s*(남자|여자)$", col)
    return int(m.group(1)) if m else None


def main() -> int:
    # 원자료는 16MB 라 러너가 눌러 담는다. 눌린 것도 그냥 읽는다.
    src = RAW / "pop_rows.jsonl"
    gz = RAW / "pop_rows.jsonl.gz"
    if src.exists():
        lines = src.open(encoding="utf-8")
    elif gz.exists():
        lines = gzip.open(gz, "rt", encoding="utf-8")
    else:
        print(f"{src}(.gz) 가 없다 — 러너로 `pop` 을 먼저 돌린다"); return 2
    rows = [json.loads(l) for l in lines]
    if not rows:
        print("원자료가 비었다"); return 2

    cols = list(rows[0])
    ages = [(c, a, c.endswith("여자")) for c in cols if (a := age_of(c)) is not None]
    print(f"원자료 {len(rows):,}줄 · 나이 칸 {len(ages)}개 · "
          f"기준 {rows[0].get('기준연월')}")

    # 옛 인천 중구·동구를 가르려면 «그 동이 옛 어느 구였나» 가 필요하다.
    # 지금 행정동 표에 그 답이 들어 있다(개편 전 이름으로 만들어 뒀다).
    # 표에 있는 252 자리 — 새로 이름을 만들지 않고 이 자리로만 돌린다.
    table = set()
    sp = OUT / "market_sggu.csv"
    if sp.exists():
        with sp.open(encoding="utf-8-sig") as f:
            table = {(r["시도"], r["시군구"]) for r in csv.DictReader(f)}

    old_incheon = {}
    dp = OUT / "market_dong.csv"
    if dp.exists():
        with dp.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["시도"] == "인천":
                    old_incheon[flat(r["행정동"])] = r["시군구"]

    def region(r: dict) -> tuple[str, str]:
        sido = SIDO_SHORT.get(r["시도명"], r["시도명"])
        sggu = (r["시군구명"] or "").strip()
        if r["시도명"] == "전남광주통합특별시":
            sido = "광주" if sggu in GWANGJU_GU else "전남"
        if not sggu:                                  # 세종은 시 아래가 없다
            return sido, "세종시"
        if sido == "인천" and sggu in SPLIT_GU:        # 옛 중구·동구가 섞여 있다
            return sido, old_incheon.get(flat(r["읍면동명"]), sggu)
        if (sido, sggu) in RENAME:
            return sido, RENAME[(sido, sggu)]
        g = sggu.replace(" ", "")
        m = re.match(r"^(.+?)시(.+구)$", g)           # 고양시 덕양구 → 고양덕양구
        if m:
            joined = m.group(1) + m.group(2)
            if not table or (sido, joined) in table:
                return sido, joined
            # 표에 구가 없고 시 한 줄만 있으면 시로 묶는다(화성 4개 구 → 화성시)
            if (sido, m.group(1) + "시") in table:
                return sido, m.group(1) + "시"
            return sido, joined
        return sido, g

    out, bad = [], 0
    for r in rows:
        sido, sggu = region(r)
        band = collections.Counter()
        w2049 = 0
        for c, a, is_w in ages:
            v = r.get(c) or 0
            if a < 10:    band["0~9"] += v
            elif a < 20:  band["10~19"] += v
            elif a < 40:  band["20~39"] += v
            elif a < 60:  band["40~59"] += v
            if a >= 65:   band["65+"] += v
            if is_w and 20 <= a < 50: w2049 += v
        tot = r.get("계") or 0
        if tot and abs(sum(r.get(c) or 0 for c, _, _ in ages) - tot) > 1:
            bad += 1
        out.append({"시도": sido, "시군구": sggu, "행정동": r["읍면동명"],
                    "행정동코드": r["행정기관코드"], "인구": tot,
                    "남": r.get("남자") or 0, "여": r.get("여자") or 0,
                    **{f"인구_{k}": band[k] for k in
                       ("0~9", "10~19", "20~39", "40~59", "65+")},
                    "인구_여20~49": w2049, "기준연월": r.get("기준연월", "")})

    hdr = list(out[0])
    with (OUT / "population_dong.csv").open("w", newline="",
                                            encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader(); w.writerows(out)

    by_sido = collections.Counter()
    for r in out:
        by_sido[r["시도"]] += r["인구"]
    print(f"{OUT/'population_dong.csv'} — {len(out):,}줄 · "
          f"전국 {sum(by_sido.values()):,}명 · 시도 {len(by_sido)}곳")
    if bad:
        print(f"[살핌] 나이 칸 합이 「계」와 어긋난 줄 {bad}개")
    sj = [r for r in out if r["시도"] == "세종"]
    if sj:
        print(f"[세종] {len(sj)}개 동 · {sum(r['인구'] for r in sj):,}명 · "
              f"65세 이상 {sum(r['인구_65+'] for r in sj):,}명")
    return 0


if __name__ == "__main__":
    sys.exit(main())
