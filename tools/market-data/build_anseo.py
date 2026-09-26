#!/usr/bin/env python3
"""ANSEO(veo-platform)에 이미 있는 전수 자료로 «지역별 병의원 상권표» 를 만든다.

읽는 것 (모두 ANSEO 저장소 · 네트워크 안 씀)
  apps/api/data/hira/2026-06/basis.csv.gz     전국 요양기관 79,772곳
  apps/api/data/hira/2026-06/subjects.csv.gz  기관별 진료과목 434,777건
  apps/api/data/population/mois_dong_population.json.gz      행정동 인구(2026-06-30)
  apps/api/data/population/mois_dong_population_age.json.gz  행정동 5세 단위 인구(2026-08-31)
  apps/api/data/population/admdongkor_dong_points.json.gz    행정동 면적

만드는 것 (data/market/)
  market_sggu.csv     시군구 한 줄 = 인구·면적·병의원 수·종별·밀집도·미용 겸업
  market_subject.csv  시군구 × 진료과목 (전문 / 겸업 / 합계로 나눠 센다)
  market_dong.csv     행정동 인구·연령·면적

«전문»과 «겸업»을 왜 나누나 [실측 2026-09-18]
  피부과를 내건 의원 16,981곳 가운데 피부과 전문의가 있는 곳은 1,599곳뿐이다.
  나머지 15,382곳은 내과·가정의학과·소아청소년과 원장이 피부·미용을 겸하는 곳이다.
  전국 의원 37,800곳의 **40%(15,208곳)** 가 피부과 또는 성형외과를 내걸고 있고,
  그 비율은 지역마다 광주 광산구 58% ↔ 대구 수성구 22% 로 벌어진다.
  «표시기관수» 하나로만 보면 이 판이 통째로 안 보인다. 그래서 셋으로 나눠 센다.

출처: 건강보험심사평가원 「전국 병의원 및 약국 현황」(공공누리 제1유형·출처표시) ·
      행정안전부 「주민등록 인구통계」 · 통계청 SGIS 행정동 경계.

이름 맞추기에서 주의한 것
  · 심평원은 광역시 이름을 시군구 앞에 붙인다(「대구동구」). 떼어 낸다.
  · 광주광역시 기관은 심평원 시도코드가 「전남」이다(원본 그대로). 구 이름으로 갈라낸다.
  · 심평원 「고양덕양구」 = 행안부 「고양시 덕양구」. 첫 낱말의 시/군 을 떼어 맞춘다.
  · 세종은 행안부 동별 자료에 없다 → 인구 «—».
"""
import csv, gzip, json, pathlib, sys, collections

ANSEO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/veo-platform")
OUT = pathlib.Path("data/market")
DASH = "—"
HIRA_DIR = ANSEO / "apps/api/data/hira/2026-06"
POP_DIR = ANSEO / "apps/api/data/population"

SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
              "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
              "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
              "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
              "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
              "경상남도": "경남", "제주특별자치도": "제주"}
METRO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산"]
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}
# 의료기관과 보건기관을 가른다 — 상권은 «장사하는 병의원» 이 기준이다.
CLINIC_KINDS = {"상급종합", "종합병원", "병원", "요양병원", "정신병원", "의원",
                "치과병원", "치과의원", "한방병원", "한의원", "조산원"}


def read_csv_gz(p: pathlib.Path) -> list[dict]:
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def load_json_gz(p: pathlib.Path) -> dict:
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


# 「부산진구」는 부산 + 진구 가 아니라 그 자체가 구 이름이다. 앞을 떼면 안 되는 자리.
KEEP_WHOLE = {"부산진구"}


def hira_region(r: dict) -> tuple[str, str]:
    """심평원 한 줄에서 (시도, 시군구) 를 원본 그대로가 아니라 «맞는 자리»로 돌려준다."""
    sido, sggu = r["시도코드명"].strip(), r["시군구코드명"].strip()
    if sido == "세종시":
        return "세종", "세종시"
    if sggu.startswith("광주") and sggu[2:] in GWANGJU_GU:
        return "광주", sggu[2:]
    if sggu in KEEP_WHOLE:
        return sido, sggu
    for m in METRO:
        if sido == m and sggu.startswith(m) and len(sggu) > len(m):
            return m, sggu[len(m):]
    return sido, sggu


def pop_variants(name: str) -> set[str]:
    """행안부 「고양시 덕양구」 → {고양시덕양구, 고양덕양구} — 심평원 표기와 맞춘다."""
    flat = name.replace(" ", "")
    out = {flat}
    parts = name.split()
    if len(parts) == 2:
        out.add(parts[0].rstrip("시군") + parts[1])
    return out


def rollup(sggu: str) -> str:
    """「고양시 덕양구」·「덕양구」 같은 자치구를 «시» 로 묶는다(사장님 시트와 맞추려고)."""
    p = sggu.split()
    return p[0] if len(p) == 2 and p[0].endswith("시") else sggu


def main() -> int:
    if not HIRA_DIR.exists():
        print(f"ANSEO 자료가 없다: {HIRA_DIR}\n"
              f"  git clone --depth 1 https://github.com/recon9973-lang/veo-platform {ANSEO}")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)

    # ── 인구 ──
    pop = load_json_gz(POP_DIR / "mois_dong_population.json.gz")
    age = load_json_gz(POP_DIR / "mois_dong_population_age.json.gz")
    pts = load_json_gz(POP_DIR / "admdongkor_dong_points.json.gz")
    area_by_dong = dict(zip(pts["dong_code"], pts["area_km2"]))

    dong_rows, sggu_pop = [], collections.defaultdict(
        lambda: {"인구": 0, "남": 0, "여": 0, "면적": 0.0, "동수": 0,
                 "0~9": 0, "10~19": 0, "20~39": 0, "40~59": 0, "65+": 0, "여20~49": 0})
    age_by_dong = {c: i for i, c in enumerate(age["dong_code"])}
    G = {"0~9": range(0, 2), "10~19": range(2, 4), "20~39": range(4, 8),
         "40~59": range(8, 12), "65+": range(13, 21)}
    key_of = {}
    for i, code in enumerate(pop["dong_code"]):
        sido = SIDO_SHORT.get(pop["sido_name"][i], pop["sido_name"][i])
        sggu = pop["sigungu_name"][i]
        k = (sido, sggu)
        key_of.setdefault(k, k)
        a = area_by_dong.get(code)
        d = {"시도": sido, "시군구": sggu, "행정동": pop["dong_name"][i], "행정동코드": code,
             "인구": pop["total"][i], "남": pop["male"][i], "여": pop["female"][i],
             "최근증감": pop["delta"][i], "면적_km2": a if a is not None else DASH}
        s = sggu_pop[k]
        s["인구"] += d["인구"]; s["남"] += d["남"]; s["여"] += d["여"]; s["동수"] += 1
        if a:
            s["면적"] += a
        j = age_by_dong.get(code)
        if j is not None:
            m, w = age["male"][j], age["female"][j]
            for g, rng in G.items():
                v = sum(m[b] + w[b] for b in rng)
                d[f"인구_{g}"] = v; s[g] += v
            v = sum(w[b] for b in range(4, 10))
            d["인구_여20~49"] = v; s["여20~49"] += v
        else:
            for g in G:
                d[f"인구_{g}"] = DASH
            d["인구_여20~49"] = DASH
        dong_rows.append(d)

    # ── 세종 메우기 ──
    # 행안부 행정동 자료에 세종이 통째로 빠져 있다. 사장님이 행안부 화면에서 읽어 주신
    # 값을 따로 둔 파일에서 가져와 채운다(출처·기준월은 그 파일에 적혀 있다).
    # 면적은 SGIS 경계 자료에 세종이 있어 거기서 센다. 나이대는 어디에도 없어 «—» 로 둔다.
    sj = pathlib.Path("data/market/sejong_population.json")
    if sj.exists():
        d = json.loads(sj.read_text(encoding="utf-8"))
        k = (d["시도"], d["시군구"])
        if not sggu_pop[k]["인구"]:
            sejong_area = sum(a for c, nm, a in zip(pts["dong_code"], pts["dong_name"],
                                                    pts["area_km2"]) if nm.startswith("세종"))
            sggu_pop[k].update({"인구": d["총인구"], "남": d["남"], "여": d["여"],
                                "면적": round(sejong_area, 1), "동수": 24})
            print(f"[세종] 행안부 {d['기준월']} 값을 넣었다 — 인구 {d['총인구']:,} · "
                  f"면적 {sejong_area:.1f}km² (나이대는 자료가 없어 «—»)")

    # ── 심평원 ──
    basis = read_csv_gz(HIRA_DIR / "basis.csv.gz")
    raw_keys = {hira_region(r) for r in basis}
    # 화성처럼 「화성시」와 「화성동탄구」가 **함께** 있는 자리가 있다. 그대로 두면
    # 인구를 두 번 센다(화성 99.9만이 경기 합계에 덧붙었다 · 이 방이 한 번 틀렸다).
    # 시 이름이 구 이름들의 머리이면 한 덩어리(시)로 묶는다.
    canon = {}
    for sido in {k[0] for k in raw_keys}:
        names = {k[1] for k in raw_keys if k[0] == sido}
        for city in [n for n in names if n.endswith("시")]:
            stem = city[:-1]
            kids = [n for n in names if n != city and n.startswith(stem)]
            for n in kids + ([city] if kids else []):
                canon[(sido, n)] = (sido, city)

    region_of, sggu_h = {}, collections.defaultdict(
        lambda: {"계": 0, "의료기관": 0, "의사수": 0, "종별": collections.Counter()})
    for r in basis:
        k = hira_region(r)
        k = canon.get(k, k)
        region_of[r["암호화요양기호"]] = k
        h = sggu_h[k]
        kind = r["종별코드명"].strip()
        h["계"] += 1
        h["종별"][kind] += 1
        if kind in CLINIC_KINDS:
            h["의료기관"] += 1
        try:
            h["의사수"] += int(r["총의사수"] or 0)
        except ValueError:
            pass

    # 인구 이름 ↔ 심평원 이름 맞추기
    var2pop = {}
    for k in list(sggu_pop):
        for v in pop_variants(k[1]):
            var2pop[(k[0], v)] = k
    roll2pop = collections.defaultdict(list)
    for k in sggu_pop:
        roll2pop[(k[0], rollup(k[1]))].append(k)
    matched, merged, unmatched = {}, {}, []
    for k in sggu_h:
        hit = var2pop.get((k[0], k[1].replace(" ", "")))
        if hit:
            matched[k] = hit
            continue
        group = roll2pop.get((k[0], k[1]))   # 심평원은 통으로, 행안부는 구로 쪼갠 자리(화성시)
        if group:
            merged[k] = group
            continue
        unmatched.append(k)

    def pop_of(k):
        """맞은 자리 하나, 또는 쪼개진 여럿을 더한 것."""
        if k in matched:
            return sggu_pop[matched[k]]
        if k in merged:
            out = collections.Counter()
            for g in merged[k]:
                for f, v in sggu_pop[g].items():
                    out[f] += v
            return dict(out)
        return None

    # ── 시군구 × 진료과목 ──
    subj = read_csv_gz(HIRA_DIR / "subjects.csv.gz")
    cnt = collections.defaultdict(lambda: {"기관": 0, "전문기관": 0, "전문의": 0})
    subj_of = collections.defaultdict(dict)   # 기관 → {과목: 그 과 전문의 수}
    for r in subj:
        k = region_of.get(r["암호화요양기호"])
        nm = r["진료과목코드명"].strip()
        try:
            n_sp = int(r["과목별 전문의수"] or 0)
        except ValueError:
            n_sp = 0
        subj_of[r["암호화요양기호"]][nm] = n_sp
        if not k:
            continue
        c = cnt[(k, nm)]
        c["기관"] += 1
        c["전문의"] += n_sp
        if n_sp > 0:          # 그 과 전문의가 실제로 있는 곳
            c["전문기관"] += 1

    # ── 의원의 미용(피부·성형) 겸업 ──
    beauty = collections.defaultdict(lambda: {"의원": 0, "겸업": 0, "일반의": 0})
    for r in basis:
        if r["종별코드명"].strip() != "의원":
            continue
        k = canon.get(hira_region(r), hira_region(r))
        b = beauty[k]
        b["의원"] += 1
        m = subj_of.get(r["암호화요양기호"], {})
        if ("피부과" in m or "성형외과" in m) and not m.get("피부과") and not m.get("성형외과"):
            b["겸업"] += 1
            try:
                if int(r["의과전문의 인원수"] or 0) == 0:
                    b["일반의"] += 1
            except ValueError:
                pass

    kinds = sorted({k for h in sggu_h.values() for k in h["종별"]})
    rows = []
    for k in sorted(sggu_h):
        h = sggu_h[k]
        p = pop_of(k)
        n, pop_n = h["의료기관"], (p["인구"] if p else 0)
        row = {"시도": k[0], "시군구": k[1],
               "시군구_정식": matched[k][1] if k in matched else
                              (merged[k][0][1].split()[0] if k in merged else k[1]),
               "시군구_묶음": rollup(matched[k][1]) if k in matched else k[1],
               "인구": pop_n or DASH,
               "남": p["남"] if p else DASH, "여": p["여"] if p else DASH,
               "면적_km2": round(p["면적"], 1) if p and p["면적"] else DASH,
               "병의원_계": n, "보건기관_포함_계": h["계"], "의사수": h["의사수"],
               "인구1만명당_병의원": round(n / pop_n * 10000, 1) if pop_n else DASH,
               "1개소당_인구": round(pop_n / n) if pop_n and n else DASH,
               "km2당_병의원": round(n / p["면적"], 1) if p and p["면적"] else DASH,
               "65세이상_비율%": round(p["65+"] / pop_n * 100, 1) if pop_n and p["65+"] else DASH,
               "20~39_비율%": round(p["20~39"] / pop_n * 100, 1) if pop_n and p["20~39"] else DASH,
               "여성20~49": p["여20~49"] if p and p["여20~49"] else DASH,
               "의원수": beauty[k]["의원"],
               "미용겸업_의원수": beauty[k]["겸업"],
               "미용겸업_비율%": round(beauty[k]["겸업"] / beauty[k]["의원"] * 100, 1)
                                 if beauty[k]["의원"] else DASH,
               "겸업중_일반의원장": beauty[k]["일반의"]}
        for kk in kinds:
            row[f"종별_{kk}"] = h["종별"].get(kk, 0)
        rows.append(row)
    with (OUT / "market_sggu.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    srows = []
    for (k, nm), c in sorted(cnt.items()):
        p = pop_of(k)
        pop_n = p["인구"] if p else 0
        srows.append({"시도": k[0], "시군구": k[1], "진료과목": nm,
                      "표시기관수": c["기관"], "전문기관수": c["전문기관"],
                      "겸업기관수": c["기관"] - c["전문기관"],
                      "과목전문의수": c["전문의"],
                      "인구": pop_n or DASH,
                      "인구1만명당": round(c["기관"] / pop_n * 10000, 2) if pop_n else DASH,
                      "1개소당_인구": round(pop_n / c["기관"]) if pop_n else DASH})
    with (OUT / "market_subject.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(srows[0].keys())); w.writeheader(); w.writerows(srows)

    with (OUT / "market_dong.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dong_rows[0].keys()))
        w.writeheader(); w.writerows(dong_rows)

    # 인천 중구·동구를 되찾기 위한 기준점 — 지도 주소는 2026-07 개편 이름(제물포구·영종구)을
    # 쓰는데 심평원은 옛 이름이라 그대로는 못 가른다. 심평원 기관의 좌표를 기준점으로 남겨,
    # 지도에서 받은 곳을 «가장 가까운 심평원 기관»의 구로 돌린다.
    # [검증 2026-09-26] 이름까지 같아 확실한 213곳 전부가 이 방법과 같은 구로 떨어졌다(100%).
    pts = [{"x": float(r["좌표(X)"]), "y": float(r["좌표(Y)"]), "구": r["시군구코드명"][2:]}
           for r in basis
           if r["시도코드명"] == "인천" and r["시군구코드명"] in ("인천중구", "인천동구")
           and r["종별코드명"] in CLINIC_KINDS and r["좌표(X)"]]
    (OUT / "incheon_old_points.json").write_text(
        json.dumps({"설명": "인천 옛 중구·동구 기준점(심평원 2026-06 병의원 좌표)",
                    "점": pts}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"시군구 {len(rows)}행 · 시군구×과목 {len(srows)}행 · 행정동 {len(dong_rows)}행")
    print(f"인천 옛 구 기준점 {len(pts)}개")
    print(f"인구와 못 맞춘 시군구 {len(unmatched)}: {unmatched}")
    print(f"전국 병의원 {sum(r['병의원_계'] for r in rows):,} (보건기관 포함 {len(basis):,})")
    print(f"진료과목 종류 {len({nm for (_, nm) in cnt}):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
