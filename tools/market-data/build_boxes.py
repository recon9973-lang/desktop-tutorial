#!/usr/bin/env python3
"""시군구마다 «좌표 네모»(경계 상자)와 한가운데를 구한다.

카카오 지도는 검색어에 지역 이름을 넣는 방식이 잘 안 맞는다
([실측 2026-09-19] 「강원 고성군 피부과」가 0건, 「강원 강릉시 한의원」도 0건).
지역은 이름이 아니라 **좌표**로 주는 것이 맞다.

바탕: ANSEO 의 통계청 SGIS 행정동 경계 점 172,167개.
나가는 곳: data/market/sggu_boxes.json
"""
import gzip, json, pathlib, collections, csv, sys

ANSEO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/veo-platform")
POP = ANSEO / "apps/api/data/population"
OUT = pathlib.Path("data/market/sggu_boxes.json")
SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
              "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
              "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
              "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
              "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
              "경상남도": "경남", "제주특별자치도": "제주"}


def main() -> int:
    pop = json.load(gzip.open(POP / "mois_dong_population.json.gz", "rt", encoding="utf-8"))
    pts = json.load(gzip.open(POP / "admdongkor_dong_points.json.gz", "rt", encoding="utf-8"))
    where = {c: (SIDO_SHORT.get(s, s), g) for c, s, g in
             zip(pop["dong_code"], pop["sido_name"], pop["sigungu_name"])}
    # 상권표의 시군구 이름(정식)으로 묶는다 — 카카오에 보낼 단위와 같아야 한다.
    box = collections.defaultdict(lambda: [999.0, 999.0, -999.0, -999.0])
    for i, dong in enumerate(pts["p_dong"]):
        code = pts["dong_code"][dong]
        k = where.get(code)
        if not k:
            continue
        lat, lng = pts["lat"][i], pts["lng"][i]
        b = box[k]
        b[0] = min(b[0], lng); b[1] = min(b[1], lat)
        b[2] = max(b[2], lng); b[3] = max(b[3], lat)

    rows = list(csv.DictReader(open("data/market/market_sggu.csv", encoding="utf-8")))
    out, miss = {}, []
    for r in rows:
        k = (r["시도"], r["시군구_정식"])
        if k in box:
            b = box[k]
        else:   # 심평원은 통으로, 행안부는 구로 쪼갠 자리(화성시) → 조각들을 합쳐 감싼다
            parts = [v for kk, v in box.items()
                     if kk[0] == r["시도"] and kk[1].split()[0] == r["시군구_정식"]]
            if not parts:
                miss.append(k); continue
            b = [min(p[0] for p in parts), min(p[1] for p in parts),
                 max(p[2] for p in parts), max(p[3] for p in parts)]
        out[f"{r['시도']}|{r['시군구']}"] = {
            "정식": r["시군구_정식"],
            "rect": [round(b[0], 6), round(b[1], 6), round(b[2], 6), round(b[3], 6)],
            "중심": [round((b[0] + b[2]) / 2, 6), round((b[1] + b[3]) / 2, 6)],
            "가로km": round((b[2] - b[0]) * 88.8, 1), "세로km": round((b[3] - b[1]) * 111.0, 1),
        }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"네모 {len(out)}개 → {OUT} ({OUT.stat().st_size/1024:.0f}KB) · 못 구한 곳 {miss or '없음'}")
    big = sorted(out.items(), key=lambda x: -x[1]["가로km"] * x[1]["세로km"])
    print("가장 큰 네모 3:", [(k, f"{v['가로km']}×{v['세로km']}km") for k, v in big[:3]])
    print("서울 강남구:", out.get("서울|강남구"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
