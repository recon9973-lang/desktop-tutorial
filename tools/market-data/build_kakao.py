#!/usr/bin/env python3
"""카카오 지도에서 훑어 온 병원을 시군구 × 분류로 센다(네트워크 안 씀).

카카오 분류는 «소비자가 지도에서 보는 정체»다. 심평원의 「내건 과목」과 달리,
한 곳에 하나만 붙는다. 그래서 «이 동네에 피부과로 보이는 곳이 몇 곳인가»를 센다.

지역은 카카오가 준 **도로명주소**로 가른다 — 훑을 때 쓴 네모는 옆 동네가 섞이므로
네모로 나누면 안 된다.

나가는 곳: data/market/market_kakao.csv
"""
import csv, json, pathlib, collections

SRC = pathlib.Path("data/market/raw/kakao_probe.jsonl")
OUT = pathlib.Path("data/market/market_kakao.csv")
SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
              "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
              "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
              "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북",
              "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북",
              "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
              "제주특별자치도": "제주", "전남광주통합특별시": "전남"}
# 프랜차이즈 이름이 분류 자리에 오는 곳이 있다 — 과목으로 되돌린다.
BRAND = {"CNP차앤박피부과": "피부과", "이지함피부과": "피부과", "CU클린업 피부과": "피부과",
         "성장클리닉": "소아청소년과"}
SKIP = {"동물병원"}   # 사람 병원이 아니다


SHORT = set(SIDO_SHORT.values())


def region_of(addr: str) -> tuple[str, str] | None:
    """주소 앞머리는 두 가지로 온다 — 「서울 서초구」와 「강원특별자치도 강릉시」. 둘 다 받는다."""
    t = (addr or "").split()
    if len(t) < 2:
        return None
    sido = SIDO_SHORT.get(t[0]) or (t[0] if t[0] in SHORT else None)
    if not sido:
        return None
    if sido == "세종":
        return ("세종", "세종시")
    # 「경기도 고양시 덕양구 …」처럼 시 아래 구가 있는 자리
    if len(t) >= 3 and t[1].endswith("시") and t[2].endswith("구"):
        return (sido, f"{t[1]} {t[2]}")
    return (sido, t[1])


def main() -> int:
    if not SRC.exists():
        print(f"훑은 자료가 없다: {SRC}"); return 2
    rows = list(csv.DictReader(open("data/market/market_sggu.csv", encoding="utf-8")))
    # 행안부 정식 이름 → 심평원 표기(표의 열쇠)
    key_of = {(r["시도"], r["시군구_정식"]): (r["시도"], r["시군구"]) for r in rows}
    for r in rows:   # 화성시처럼 심평원이 통으로 가진 자리는 구 이름도 받아 준다
        key_of.setdefault((r["시도"], r["시군구"]), (r["시도"], r["시군구"]))

    cnt = collections.defaultdict(collections.Counter)
    seen, total, unmatched = set(), 0, collections.Counter()
    for line in SRC.open(encoding="utf-8"):
        try:
            p = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        leaf = (p.get("cat") or "").split(">")[-1].strip()
        leaf = BRAND.get(leaf, leaf)
        if not leaf or leaf in SKIP:
            continue
        reg = region_of(p.get("addr") or "")
        if not reg:
            continue
        k = key_of.get(reg)
        if not k:
            k = key_of.get((reg[0], reg[1].split()[0]))   # 「고양시 덕양구」→「고양시」
        if not k:
            unmatched[reg] += 1; continue
        cnt[k][leaf] += 1
        total += 1

    leaves = sorted({c for v in cnt.values() for c in v})
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["시도", "시군구", "지도_병원계"] + [f"지도_{c}" for c in leaves])
        for (sido, sggu) in sorted(cnt):
            v = cnt[(sido, sggu)]
            w.writerow([sido, sggu, sum(v.values())] + [v.get(c, 0) for c in leaves])
    print(f"지도에 오른 병원 {total:,}곳 · 시군구 {len(cnt)} · 분류 {len(leaves)} → {OUT}")
    if unmatched:
        print(f"주소를 못 맞춘 곳 {sum(unmatched.values()):,}: {dict(unmatched.most_common(6))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
