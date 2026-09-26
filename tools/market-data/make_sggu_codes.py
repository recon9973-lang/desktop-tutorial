#!/usr/bin/env python3
"""표의 252 자리 ↔ 공공 API 에 물을 때 쓰는 코드표(`data/market/sggu_codes.csv`).

왜 따로 만드나: 러너에는 ANSEO 사본이 없다. 한 번 만들어 저장소에 담아 둔다.

왜 한 자리에 코드가 여럿인가 — **자료마다 행정구역 시점이 다르다.**
인구(2026-06-30)는 개편 전 이름·코드이고, 나이대·경계·상가정보는 2026-07 개편 뒤다
(「전남광주통합특별시」· 인천 제물포구/영종구/검단구/서해구 · 화성 4개 구).
그래서 **옛 코드와 새 코드를 함께 담고**, 값을 받아 본 뒤 «답이 오는 쪽» 을 쓴다.
[실측 2026-09-26] 옛 코드로 물으면 전남 22곳·광주 5구·인천 3구가 «자료 없음» 으로 온다.

인천은 1:1 로 갈리지 않는다 — 옛 중구·동구가 제물포구·영종구로 다시 갈렸다.
그래서 그 둘만 **행정동 단위** 로 묻고 옛 구로 다시 더한다
([확인] 옛 중구 13동 = 영종구 6 + 제물포구 7, 옛 동구 11동 = 제물포구 11).
"""
import csv, gzip, json, pathlib, re, sys, collections

ANSEO = pathlib.Path("/home/user/veo-platform")
POP = ANSEO / "apps/api/data/population"
OUT = pathlib.Path("data/market")
SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
              "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
              "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
              "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
              "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
              "경상남도": "경남", "제주특별자치도": "제주"}
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}
SPLIT_GU = {"제물포구", "영종구"}          # 옛 중구·동구가 섞여 있다
# 이름만 바뀐 곳은 그대로 옛 이름으로 돌린다(둘 다 옛 서구 안이다).
RENAME = {("인천", "서해구"): ("인천", "서구"), ("인천", "검단구"): ("인천", "서구")}
flat = lambda s: re.sub(r"[ .·]", "", s)


def load(p):
    return json.load(gzip.open(p, "rt", encoding="utf-8"))


def main() -> int:
    if not POP.exists():
        print(f"ANSEO 자료가 없다: {POP}"); return 2
    pop, age = load(POP / "mois_dong_population.json.gz"), load(
        POP / "mois_dong_population_age.json.gz")

    table = [(r["시도"], r["시군구"]) for r in
             csv.DictReader((OUT / "market_sggu.csv").open(encoding="utf-8-sig"))]
    tset = set(table)

    def fit(sido: str, sggu: str) -> tuple[str, str]:
        """행안부 이름을 표 이름 꼴로. 고양시덕양구 → 고양덕양구, 화성 4구 → 화성시."""
        g = sggu.replace(" ", "")
        m = re.match(r"^(.+?)시(.+구)$", g)
        if m:
            g = m.group(1) + m.group(2)
        if (sido, g) in RENAME:
            return RENAME[(sido, g)]
        if (sido, g) in tset:
            return (sido, g)
        for s2, g2 in tset:
            if s2 == sido and g2.endswith("시") and g.startswith(g2[:-1]):
                return (s2, g2)
        return (sido, g)

    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def add(key, code, what, why):
        if (key[0], key[1], code) in seen:
            return
        seen.add((key[0], key[1], code))
        rows.append({"시도": key[0], "시군구": key[1], "코드": code,
                     "무엇": what, "왜": why})

    # ── ① 옛 코드(인구 자료 기준) ──
    for code, sd, sg in zip(pop["dong_code"], pop["sido_name"], pop["sigungu_name"]):
        add(fit(SIDO_SHORT.get(sd, sd), sg), code[:5], "signguCd", "개편 전")

    # ── ② 새 코드(나이대 자료 기준 · 2026-07 개편 뒤) ──
    old_incheon = {flat(d): g for sd, g, d in
                   zip(pop["sido_name"], pop["sigungu_name"], pop["dong_name"])
                   if sd == "인천광역시"}
    for code, sd, sg, dg in zip(age["dong_code"], age["sido_name"],
                                age["sigungu_name"], age["dong_name"]):
        if sd == "인천광역시" and sg in SPLIT_GU:
            gu = old_incheon.get(flat(dg))          # 옛 중구인지 동구인지 이름으로 가른다
            if gu:
                add(("인천", gu), code[:8], "adongCd", f"개편 후 {sg} {dg}")
            continue
        sido = SIDO_SHORT.get(sd, sd)
        if sd == "전남광주통합특별시":
            sido = "광주" if sg in GWANGJU_GU else "전남"
        add(fit(sido, sg), code[:5], "signguCd", "개편 후")

    # ── ③ 2026년에 생긴 구를 옛 자료가 모를 때를 대비한 시 코드 ──
    add(("경기", "화성시"), "41590", "signguCd", "구 생기기 전 시 코드")

    sj = OUT / "raw/sangga_codes.json"          # 세종은 행안부 동별 자료에 없다
    if sj.exists():
        for c in (json.loads(sj.read_text(encoding="utf-8"))
                  .get("세종_시군구코드") or {}):
            add(("세종", "세종시"), c, "signguCd", "상가자료에서 찾은 코드")

    keys = {(r["시도"], r["시군구"]) for r in rows}
    missing, extra = tset - keys, keys - tset
    if missing:
        print(f"코드를 못 만든 자리 {len(missing)}: {sorted(missing)}")
    if extra:
        print(f"표에 없는 자리가 생겼다 {len(extra)}: {sorted(extra)}")

    rows.sort(key=lambda r: (r["시도"], r["시군구"], r["무엇"], r["코드"]))
    with (OUT / "sggu_codes.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["시도", "시군구", "코드", "무엇", "왜"])
        w.writeheader(); w.writerows(rows)

    per = collections.Counter((r["시도"], r["시군구"]) for r in rows)
    print(f"{OUT/'sggu_codes.csv'} — 자리 {len(per)}곳 · 코드 {len(rows)}개")
    print("코드가 여럿인 자리 " + str(sum(1 for v in per.values() if v > 1)) + ":")
    for k, v in sorted(per.items(), key=lambda x: -x[1])[:6]:
        print(f"   {k[0]} {k[1]} — {v}개")
    return 0 if not (missing or extra) else 1


if __name__ == "__main__":
    sys.exit(main())
