#!/usr/bin/env python3
"""표 셋을 화면(웹)이 바로 읽을 수 있는 작은 묶음으로 만든다.

행을 그대로 싣지 않고 «열 이름은 한 번, 값은 배열» 로 눌러 담는다 — 같은 내용이
10분의 1 크기가 된다. 나가는 곳: data/market/screen/{regions,subjects}.json
"""
import csv, json, pathlib, collections

OUT = pathlib.Path("data/market/screen")
SRC = pathlib.Path("data/market")
num = lambda v: None if v in ("—", "", None) else float(v)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sg = list(csv.DictReader((SRC / "market_sggu.csv").open(encoding="utf-8")))
    sj = list(csv.DictReader((SRC / "market_subject.csv").open(encoding="utf-8")))
    kk_path = SRC / "market_kakao.csv"
    kk = {(r["시도"], r["시군구"]): r for r in
          csv.DictReader(kk_path.open(encoding="utf-8"))} if kk_path.exists() else {}
    kk_cols = [c[3:] for c in (next(iter(kk.values())).keys() if kk else []) 
               if c.startswith("지도_") and c != "지도_병원계"]
    # 업종별 상권(소상공인 상가정보) — 없으면 그 자리는 그냥 빈다.
    sa_path = SRC / "market_sangga.csv"
    sa = {(r["시도"], r["시군구"]): r for r in
          csv.DictReader(sa_path.open(encoding="utf-8-sig"))} if sa_path.exists() else {}
    sa_l = [c[3:] for c in (next(iter(sa.values())).keys() if sa else [])
            if c.startswith("업종_")]
    sa_m = [c[2:] for c in (next(iter(sa.values())).keys() if sa else [])
            if c.startswith("중_")]
    kinds = [c[3:] for c in sg[0] if c.startswith("종별_")]

    regions, index = [], {}
    for i, r in enumerate(sg):
        index[(r["시도"], r["시군구"])] = i
        regions.append([
            r["시도"], r["시군구"], num(r["인구"]), int(r["병의원_계"]),
            num(r["인구1만명당_병의원"]), num(r["면적_km2"]), num(r["km2당_병의원"]),
            num(r["65세이상_비율%"]), num(r["20~39_비율%"]), num(r["여성20~49"]),
            int(r["의사수"]), [int(r[f"종별_{k}"]) for k in kinds],
            int(r["의원수"]), int(r["미용겸업_의원수"]),
            num(r["미용겸업_비율%"]), int(r["겸업중_일반의원장"]),
            int(k["지도_병원계"]) if (k := kk.get((r["시도"], r["시군구"]))) else None,
            [int(k[f"지도_{c}"]) for c in kk_cols] if k else None,
            num(a["점포_계"]) if (a := sa.get((r["시도"], r["시군구"]))) else None,
            [num(a[f"업종_{c}"]) for c in sa_l] if a else None,
            [num(a[f"중_{c}"]) for c in sa_m] if a else None,
        ])

    names, nidx = [], {}
    per = collections.defaultdict(list)
    for r in sj:
        nm = r["진료과목"]
        if nm not in nidx:
            nidx[nm] = len(names); names.append(nm)
        ri = index.get((r["시도"], r["시군구"]))
        if ri is None:
            continue
        per[ri].append([nidx[nm], int(r["표시기관수"]), int(r["전문기관수"]),
                        int(r["과목전문의수"])])

    nat_pop = sum(x[2] or 0 for x in regions)
    nat_n = sum(x[3] for x in regions)
    nat_subj = [0] * len(names)      # 내건 곳
    nat_spec = [0] * len(names)      # 전문의 있는 곳
    for rows in per.values():
        for si, c, sc, _ in rows:
            nat_subj[si] += c; nat_spec[si] += sc

    payload = {
        "기준": {"병의원": "심평원 2026-06", "인구": "행안부 2026-06-30",
                 "나이": "행안부 2026-08-31", "면적": "SGIS 2026-07-01"},
        "열": ["시도", "시군구", "인구", "병의원", "인구1만명당", "면적km2", "km2당",
               "65세이상%", "20~39%", "여성20~49", "의사수", "종별",
               "의원수", "미용겸업", "미용겸업%", "겸업중일반의", "지도계", "지도분류",
               "점포계", "업종", "중업종"],
        "지도분류이름": kk_cols,
        "업종이름": sa_l,
        "중업종이름": sa_m,
        "종별이름": kinds,
        "전국": {"인구": nat_pop, "병의원": nat_n,
                 "인구1만명당": round(nat_n / nat_pop * 10000, 2),
                 "의원": sum(x[12] for x in regions),
                 "미용겸업": sum(x[13] for x in regions),
                 "점포": sum(x[18] or 0 for x in regions) or None,
                 # 업종 지수(전국=100)의 기준 인구는 «업종 값이 있는 자리의 인구» 다.
                 # 값이 없는 자리 인구까지 넣으면 전국 평균이 낮아져 지수가 다 부풀어 오른다.
                 "업종기준인구": sum(x[2] or 0 for x in regions if x[18] is not None),
                 # 업종별 전국 합 — 지역 지수(전국=100)의 기준선.
                 "업종": [sum((x[19] or [0] * len(sa_l))[i] or 0 for x in regions)
                          for i in range(len(sa_l))],
                 "중업종": [sum((x[20] or [0] * len(sa_m))[i] or 0 for x in regions)
                            for i in range(len(sa_m))]},
        "지역": regions,
    }
    (OUT / "regions.json").write_text(json.dumps(payload, ensure_ascii=False,
                                                 separators=(",", ":")), encoding="utf-8")
    (OUT / "subjects.json").write_text(json.dumps(
        {"이름": names, "전국표시기관수": nat_subj, "전국전문기관수": nat_spec,
         "전국인구": nat_pop,
         "지역별": {str(k): v for k, v in sorted(per.items())}},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for p in (OUT / "regions.json", OUT / "subjects.json"):
        print(f"{p} {p.stat().st_size / 1024:.0f}KB")
    print(f"지역 {len(regions)} · 과목 {len(names)} · 종별 {len(kinds)} · "
          f"업종 대분류 {len(sa_l)} · 중분류 {len(sa_m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
