#!/usr/bin/env python3
"""세어 둔 상가정보(`raw/sangga_counts.jsonl`) → 업종별 상권 표(`market_sangga.csv`).

왜 있나: 심평원은 «병원이 몇 곳인가» 만 말해 준다. 그 동네가 학원가인지 먹자골목인지
오피스인지는 말해 주지 않는다. 상가정보가 그것을 말해 준다 — 병원 마케팅에서
«우리 환자가 이 동네에 사는가» 를 판단하는 자리다.

출처: 소상공인시장진흥공단 상가(상권)정보 · 기준월 202606 (공공데이터포털)
"""
import collections, csv, json, pathlib, sys

OUT = pathlib.Path("data/market")
RAW = OUT / "raw"
DASH = "—"

# 표에 실을 업종 — (칼럼 이름, 갈래, 업종코드). 이름은 화면에 그대로 나간다.
LCLS = [("음식", "대", "I2"), ("소매", "대", "G2"), ("수리·개인", "대", "S2"),
        ("교육", "대", "P1"), ("과학·기술", "대", "M1"), ("예술·스포츠", "대", "R1"),
        ("부동산", "대", "L1"), ("보건의료", "대", "Q1"), ("숙박", "대", "I1"),
        ("시설관리·임대", "대", "N1")]
MCLS = [("이용·미용", "중", "S207"), ("욕탕·신체관리", "중", "S208"),
        ("의약·화장품", "중", "G215"), ("일반교육", "중", "P105"),
        ("기타교육", "중", "P106"), ("병원", "중", "Q101"), ("의원", "중", "Q102"),
        ("기타보건", "중", "Q104"), ("스포츠", "중", "R103"), ("주점", "중", "I211"),
        ("카페", "중", "I212"), ("부동산서비스", "중", "L102"),
        ("경영컨설팅", "중", "M107"), ("의복소매", "중", "G209")]


def main() -> int:
    path = RAW / "sangga_counts.jsonl"
    if not path.exists():
        print(f"{path} 가 없다 — 러너로 `sangga` 를 먼저 돌린다"); return 2

    # (시도,시군구) → 코드 → 갈래·업종 → 점포수
    box: dict = collections.defaultdict(lambda: collections.defaultdict(dict))
    bad = 0
    for line in path.open(encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:  # noqa: BLE001
            bad += 1; continue
        v = d.get("점포수")
        if v is None and d.get("resultCode") == "03":
            v = 0          # rc=03 은 «그 업종이 한 곳도 없다» 다. 못 잰 것이 아니다.
        box[(d["시도"], d["시군구"])][d["코드"]][(d["갈래"], d["업종코드"])] = (
            int(v) if isinstance(v, (int, str)) and str(v).isdigit() else None)

    # 인구·심평원 의원 수는 이미 있는 표에서 가져온다 — 다시 세지 않는다.
    pop, hira = {}, {}
    mp = OUT / "market_sggu.csv"
    with mp.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    order = [(r["시도"], r["시군구"]) for r in rows]
    for r in rows:
        k = (r["시도"], r["시군구"])
        pop[k] = int(r["인구"]) if r["인구"].isdigit() else None
        hira[k] = {"의원": int(r["종별_의원"] or 0), "병의원": int(r["병의원_계"] or 0)}

    def pick(codes: dict) -> dict:
        """한 자리에 코드가 여럿이다 — 옛 코드와 개편 뒤 코드를 함께 물었기 때문이다.
        **답이 온 코드만** 골라 합친다(옛 코드는 «자료 없음» 으로 온다).
        인천 중구·동구는 행정동 코드가 여럿이라 실제로 더해진다.
        한 코드라도 답을 못 받았으면 그 칸은 «—» 로 둔다 — 모자란 합을 싣지 않는다."""
        live = {c: v for c, v in codes.items()
                if (v.get(("전체", "")) or 0) > 0}
        if not live:
            return {}
        agg: dict = {}
        for v in live.values():
            for key in {k for d in live.values() for k in d}:
                n = v.get(key, None)
                if n is None or agg.get(key, 0) is None:
                    agg[key] = None
                else:
                    agg[key] = agg.get(key, 0) + n
        return agg

    hdr = (["시도", "시군구", "인구", "점포_계", "인구1만명당_점포"]
           + [f"업종_{n}" for n, _, _ in LCLS]
           + [f"비율%_{n}" for n, _, _ in LCLS]
           + [f"중_{n}" for n, _, _ in MCLS]
           + ["미용업소_1만명당", "학원_1만명당", "카페_1만명당", "헬스_1만명당",
              "오피스_1만명당", "상가_의원", "심평원_의원"])
    out, filled = [], 0
    for k in order:
        agg = pick(box.get(k, {}))
        tot = agg.get(("전체", ""))
        p = pop.get(k)
        row = {"시도": k[0], "시군구": k[1], "인구": p if p else DASH,
               "점포_계": tot if tot is not None else DASH,
               "인구1만명당_점포": round(tot / p * 10000, 1) if tot and p else DASH}
        if tot:
            filled += 1
        for nm, kind, code in LCLS:
            v = agg.get((kind, code))
            row[f"업종_{nm}"] = v if v is not None else DASH
            row[f"비율%_{nm}"] = round(v / tot * 100, 1) if v is not None and tot else DASH
        for nm, kind, code in MCLS:
            v = agg.get((kind, code))
            row[f"중_{nm}"] = v if v is not None else DASH

        def per(*names) -> object:
            vals = [agg.get((kd, cd)) for nm, kd, cd in MCLS if nm in names]
            if not p or any(v is None for v in vals) or not vals:
                return DASH
            return round(sum(vals) / p * 10000, 1)

        row["미용업소_1만명당"] = per("이용·미용", "욕탕·신체관리")
        row["학원_1만명당"] = per("일반교육", "기타교육")
        row["카페_1만명당"] = per("카페")
        row["헬스_1만명당"] = per("스포츠")
        row["오피스_1만명당"] = per("경영컨설팅")
        # 두 숫자를 나란히 둔다. 나눈 값은 싣지 않는다 — 상가자료는 «간판 달고 장사하는
        # 자리»를, 심평원은 «허가받은 기관»을 세므로 서울에서는 상가 쪽이 더 많고
        # 시골에서는 적다. 나눠 놓으면 「등록률」로 잘못 읽힌다.
        row["상가_의원"] = sg if (sg := agg.get(("중", "Q102"))) is not None else DASH
        row["심평원_의원"] = hira[k]["의원"]
        out.append(row)

    with (OUT / "market_sangga.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader(); w.writerows(out)

    print(f"{OUT/'market_sangga.csv'} — {len(out)}줄 (점포 수가 있는 자리 {filled})")
    if bad:
        print(f"못 읽은 줄 {bad}")
    blanks = [f"{r['시도']} {r['시군구']}" for r in out if r["점포_계"] == DASH]
    if blanks:
        print(f"점포 수를 못 받은 자리 {len(blanks)}: " + ", ".join(blanks[:20]))
    got = [r for r in out if r["점포_계"] != DASH]
    if got:
        print(f"전국 점포 {sum(r['점포_계'] for r in got):,}곳")
        for key in ("인구1만명당_점포", "미용업소_1만명당", "학원_1만명당"):
            rk = sorted([r for r in got if r[key] != DASH], key=lambda r: -r[key])[:3]
            print(f"  {key} 많은 곳: " + ", ".join(
                f"{r['시도']} {r['시군구']} {r[key]}" for r in rk))
    return 0


if __name__ == "__main__":
    sys.exit(main())
