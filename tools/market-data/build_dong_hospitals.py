#!/usr/bin/env python3
"""병원 좌표 × 행정동 경계 → **읍면동 단위 병의원 수**.

왜 있나: 구 하나는 너무 넓다. 의원 하나가 실제로 받는 손님은 걸어서·차로 몇 분 거리에
산다. 「강남구에 병원이 3,142곳」보다 「역삼1동에 몇 곳」이 자리를 고르는 데 쓸모 있다.

어떻게: 심평원 자료에 **기관마다 좌표가 들어 있다**(`좌표(X)`·`좌표(Y)`). 통계청 행정동
자료에는 **동마다 안쪽을 고르게 찍은 점**이 50개쯤 들어 있다(동마다 140m 안팎 눈금).
병원 좌표에서 **가장 가까운 점**을 찾아 그 동으로 돌린다 — 인천 옛 중구·동구를 가를 때
쓴 것과 같은 방법이다.

[한 번 잘못 짚었다] 그 점들이 «경계를 차례로 이은 고리» 인 줄 알고 «고리 안에 있나» 로
세어 보니 76,322곳 중 56,083곳이 어느 고리에도 안 들어갔다. 고리로 잰 넓이가 적혀 있는
넓이의 15%밖에 안 된다 — 고리가 아니라 안쪽 점이다.

동 경계 근처에서는 눈금만큼(140m 안팎, 시골은 더) 어긋날 수 있다. 그래서
**심평원이 스스로 적어 둔 시군구와 맞는지 전부 대조**하고 그 비율을 함께 적는다.

출처: 심평원 「전국 병의원 및 약국 현황」 2026-06(공공누리 1유형·출처표시) ·
      통계청 SGIS 행정동 경계 2026-07-01
"""
import collections, csv, gzip, json, math, pathlib, re, statistics, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_anseo import hira_region      # 심평원 자리 셈은 한 군데서만 한다

ANSEO = pathlib.Path("/home/user/veo-platform")
HIRA = ANSEO / "apps/api/data/hira/2026-06/basis.csv.gz"
PTS = ANSEO / "apps/api/data/population/admdongkor_dong_points.json.gz"
OUT = pathlib.Path("data/market")
DASH = "—"
CLINIC_KINDS = {"상급종합", "종합병원", "병원", "요양병원", "정신병원", "의원",
                "치과병원", "치과의원", "한방병원", "한의원", "조산원"}
SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
              "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
              "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
              "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
              "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
              "경상남도": "경남", "제주특별자치도": "제주"}
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}
# 2026-07 개편으로 이름만 바뀐 자리 — 경계 자료는 새 이름, 심평원은 옛 이름을 쓴다.
# 옛 중구·동구 ↔ 제물포구·영종구 는 1:1 이 아니라 섞였다(한쪽으로만 맞춰 본다).
INCHEON_NEW = {"서해구": "서구", "검단구": "서구", "영종구": "중구", "제물포구": None}
# 새 이름 → 심평원이 쓰는 옛 이름. 제물포구는 옛 중구·동구가 섞여 있어 둘 다에 넣는다.
INCHEON_OLD = {("인천", "서해구"): ("인천", "서구"), ("인천", "검단구"): ("인천", "서구"),
               ("인천", "영종구"): ("인천", "중구")}


def read_hira() -> list[dict]:
    rows = [l for l in gzip.open(HIRA, "rt", encoding="utf-8-sig") if not l.startswith("#")]
    return list(csv.DictReader(rows))


def nearest_index(lng: list, lat: list, keep=None, cell: float = 0.02):
    """좌표를 격자에 담아 «가장 가까운 점» 을 빨리 찾게 한다.
    `keep` 을 주면 그 점들만 담는다 — 시군구 안에서만 찾게 할 때 쓴다."""
    g = collections.defaultdict(list)
    for i in (keep if keep is not None else range(len(lng))):
        g[(int(lng[i] / cell), int(lat[i] / cell))].append(i)
    return g, cell


def nearest(x: float, y: float, lng: list, lat: list, grid: dict, cell: float):
    """가까운 칸부터 넓혀 가며 찾는다. 한 칸 넓힐 때마다 «이보다 가까운 것은 없다» 를 본다."""
    gx, gy = int(x / cell), int(y / cell)
    best, bi = float("inf"), None
    for ring in range(0, 12):
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if ring and max(abs(dx), abs(dy)) != ring:
                    continue            # 새로 생긴 테두리만 본다
                for i in grid.get((gx + dx, gy + dy), ()):
                    d = (lng[i] - x) ** 2 + ((lat[i] - y) * 1.24) ** 2
                    if d < best:
                        best, bi = d, i
        if bi is not None and best <= (ring * cell) ** 2:
            break
    return bi, math.sqrt(best) * 88 if bi is not None else None


def main() -> int:
    if not HIRA.exists() or not PTS.exists():
        print(f"ANSEO 자료가 없다: {ANSEO}"); return 2
    d = json.load(gzip.open(PTS, "rt", encoding="utf-8"))
    codes, names = d["dong_code"], d["dong_name"]
    lng, lat, p_dong = d["lng"], d["lat"], d["p_dong"]
    print(f"행정동 {len(codes):,}개 · 안쪽 점 {len(lng):,}개")

    # 동 이름 → 표의 (시도, 시군구) 자리.
    # 경계 자료는 「경기도 고양시덕양구 주교동」 꼴이고 심평원은 「고양덕양구」다.
    # 구 앞의 «시» 를 떼어 같은 꼴로 만든다.
    def region_of(nm: str) -> tuple[str, str]:
        p = nm.split(" ")
        sido, sggu = p[0], (p[1] if len(p) > 2 else "")
        m = re.match(r"^(.+?)시(.+구)$", sggu)
        if m:
            sggu = m.group(1) + m.group(2)
        if sido == "전남광주통합특별시":
            return ("광주" if sggu in GWANGJU_GU else "전남"), sggu
        return SIDO_SHORT.get(sido, sido), sggu

    # ── 시군구마다 제 점만 모아 둔다 ──
    # 심평원은 기관마다 시군구를 확실히 적어 둔다. 동은 몰라도 구는 안다.
    # 그래서 **그 구 안에서만** 가장 가까운 점을 찾는다 — 구 경계에서 옆 구로 넘어가는
    # 일이 아예 없어진다([실측] 안 그러면 강남↔서초 경계에서만 144곳이 넘어갔다).
    by_sggu: dict = collections.defaultdict(list)
    for pi, di in enumerate(p_dong):
        k = region_of(names[di])
        by_sggu[k].append(pi)
        if k == ("인천", "제물포구"):     # 옛 중구·동구가 섞여 있다 — 둘 다의 후보로 둔다
            by_sggu[("인천", "중구")].append(pi)
            by_sggu[("인천", "동구")].append(pi)
        elif (alt := INCHEON_OLD.get(k)):  # 이름만 바뀐 자리
            by_sggu[alt].append(pi)
    index = {k: nearest_index(lng, lat, v) for k, v in by_sggu.items()}
    gall = nearest_index(lng, lat)        # 구를 못 찾았을 때 쓰는 전국 격자

    basis = read_hira()
    clinics = [r for r in basis if r["종별코드명"].strip() in CLINIC_KINDS]
    print(f"병의원 {len(clinics):,}곳(보건기관 제외)")

    hit = collections.Counter()          # 행정동 index → 곳 수
    kinds = collections.defaultdict(collections.Counter)
    stat = collections.Counter()
    checked = agree = 0
    miss, renamed = collections.Counter(), collections.Counter()
    dists: list = []
    for r in clinics:
        try:
            x, y = float(r["좌표(X)"]), float(r["좌표(Y)"])
        except (ValueError, KeyError):
            stat["좌표 없음"] += 1; continue
        if not (124 < x < 132 and 33 < y < 39):
            stat["좌표가 나라 밖"] += 1; continue
        want = hira_region(r)
        grid, cell = index.get(want, gall)
        if want not in index:
            stat["그 구의 경계 자료가 없음"] += 1
        pi, dist = nearest(x, y, lng, lat, grid, cell)
        if dist is not None:
            dists.append(dist)
        if pi is None:
            stat["가까운 점이 없음"] += 1; continue
        i = p_dong[pi]
        hit[i] += 1
        kinds[i][r["종별코드명"].strip()] += 1
        stat["자리 찾음"] += 1
        if dist is not None and dist > 2:
            stat["가장 가까운 점이 2km 넘게 떨어짐"] += 1
        # 심평원이 스스로 적어 둔 자리와 맞는지 — 이것이 이 표의 신뢰도다
        want, got = hira_region(r), region_of(names[i])
        checked += 1
        same = want == got
        if not same and want[0] == "인천" == got[0]:
            # 같은 곳의 새 이름이면 어긋난 것이 아니다
            alt = INCHEON_NEW.get(got[1])
            same = (alt == want[1]) or (got[1] == "제물포구"
                                        and want[1] in ("중구", "동구"))
            if same:
                renamed[(want[1], got[1])] += 1
        if same:
            agree += 1
        else:
            miss[(want, got)] += 1

    print("\n[어떻게 됐나] " + " · ".join(f"{k} {v:,}" for k, v in stat.items()))
    pct = agree / checked * 100 if checked else 0
    print(f"[대조] 심평원이 적어 둔 시군구와 같은 곳: {agree:,} / {checked:,} = {pct:.1f}%")
    if renamed:
        print("   그중 «같은 곳의 새 이름» 으로 친 것: "
              + " · ".join(f"{a}→{b} {c:,}" for (a, b), c in renamed.most_common()))
    if miss:
        print("[어긋난 자리 많은 순]")
        for (w, g), c in miss.most_common(6):
            print(f"   심평원 {w[0]} {w[1]} ↔ 경계 {g[0]} {g[1]} — {c:,}곳")
    if pct < 100:
        print("→ 구 안에서만 찾는데도 구가 어긋났다. 이 값을 싣지 않는다."); return 1
    print(f"[거리] 그 동의 점까지: 가운데값 {statistics.median(dists)*1000:.0f}m · "
          f"1km 넘는 곳 {sum(1 for d in dists if d > 1):,} / {len(dists):,}")
    print("[알아 둘 것] 구는 심평원이 적어 둔 대로라 틀릴 수 없다. **동은 좌표로 어림한 값**이다 —"
          "\n   심평원은 법정동(창신동)을, 경계 자료는 행정동(창신1동)을 쓰고 둘을 잇는 표가 없어"
          "\n   이름으로는 대조할 수 없다. 동 경계에서 140m 안팎은 어긋날 수 있다.")

    def rollup_sggu(sido: str, g: str, table: set) -> str:
        """행정동 표의 「수원시 장안구」를 시군구 표의 「수원장안구」 꼴로.
        화성처럼 시군구 표에 구가 없고 시 한 줄만 있으면 시로 묶는다
        ([실측] 이걸 안 해서 화성 1,008곳이 통째로 0으로 보였다)."""
        g = re.sub(r"[ ·]", "", g)
        m = re.match(r"^(.+?)시(.+구)$", g)
        if m:
            if (sido, m.group(1) + m.group(2)) in table:
                return m.group(1) + m.group(2)
            if (sido, m.group(1) + "시") in table:
                return m.group(1) + "시"
            return m.group(1) + m.group(2)
        return g

    def sggu_key(g: str) -> str:
        g = re.sub(r"[ ·]", "", g)
        m = re.match(r"^(.+?)시(.+구)$", g)
        return (m.group(1) + m.group(2)) if m else g

    # 행정동 인구 표와 붙인다 — 이름으로 맞춘다(코드는 개편 때문에 어긋난다)
    dong = list(csv.DictReader((OUT / "market_dong.csv").open(encoding="utf-8-sig")))
    # 이름이 양쪽에서 조금씩 다르다 — 「창신제1동」↔「창신1동」, 「두류1.2동」↔「두류1,2동」.
    # 한쪽을 고쳐 맞추면 「홍제1동」이 「홍1동」이 된다(한 번 그렇게 망가뜨렸다).
    # 그래서 **고치지 말고 두 꼴을 다 만들어** 하나라도 겹치면 같은 동으로 본다.
    def keys(s: str) -> set:
        a = re.sub(r"[ .·,]", "", s)
        return {a, re.sub(r"제(\d)", r"\1", a)}
    by_name: dict = collections.defaultdict(list)
    for i, nm in enumerate(names):
        sido, _ = region_of(nm)
        for k in keys(nm.split(" ")[-1]):
            by_name[(sido, k)].append(i)

    kind_cols = ["의원", "치과의원", "한의원", "병원", "종합병원", "요양병원"]
    out, matched = [], 0
    for r in dong:
        cands = sorted({i for k in keys(r["행정동"])
                        for i in by_name.get((r["시도"], k), ())})
        if len(cands) > 1:      # 같은 시도에 같은 동 이름이 둘 — 시군구까지 맞춘다
            # 행정동 표는 「수원시 장안구」, 경계 쪽은 「수원장안구」 — 같은 꼴로 만든다.
            # [실측] 이걸 안 맞춰서 「정자1동」처럼 겹치는 이름 29줄이 비어 있었다.
            want = sggu_key(r["시군구"])
            def same(g: str) -> bool:
                g = sggu_key(g)
                # 표는 「화성시」 한 줄인데 경계는 「화성동탄구」처럼 구로 갈려 있다.
                # 시 이름이 구 이름의 머리이면 같은 자리로 본다
                # ([실측] 이걸 안 해서 화성 반월동 39곳이 비어 있었다).
                return g == want or (want.endswith("시") and g.startswith(want[:-1]))
            narrowed = [i for i in cands if same(region_of(names[i])[1])]
            cands = narrowed or cands
        row = dict(r)
        if len(cands) == 1:
            i = cands[0]; matched += 1
            row["병의원_계"] = hit.get(i, 0)
            for k in kind_cols:
                row[f"종별_{k}"] = kinds[i][k]
            p = float(r["인구"]) if r["인구"] not in ("", DASH) else 0
            row["인구1만명당_병의원"] = round(hit.get(i, 0) / p * 10000, 1) if p else DASH
        else:
            row["병의원_계"] = DASH
            for k in kind_cols:
                row[f"종별_{k}"] = DASH
            row["인구1만명당_병의원"] = DASH
        out.append(row)

    hdr = list(dong[0]) + ["병의원_계", "인구1만명당_병의원"] + [f"종별_{k}" for k in kind_cols]
    with (OUT / "market_dong.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader(); w.writerows(out)

    placed = sum(v for v in hit.values())
    print(f"\n{OUT/'market_dong.csv'} — {len(out):,}줄 · 병의원 수를 넣은 동 {matched:,}")
    print(f"동에 붙인 병의원 {placed:,}곳 / 병의원 {len(clinics):,}곳")
    # [대조] 동을 시군구로 다시 더하면 시군구 표와 같아야 한다
    sp = OUT / "market_sggu.csv"
    if sp.exists():
        want = {(x["시도"], x["시군구"]): int(x["병의원_계"])
                for x in csv.DictReader(sp.open(encoding="utf-8-sig"))}
        got = collections.Counter()
        for r in out:
            if r["병의원_계"] != DASH:
                got[(r["시도"], rollup_sggu(r["시도"], r["시군구"], set(want)))] += r["병의원_계"]
        gap = {k: (want[k], got.get(k, 0)) for k in want
               if want[k] != got.get(k, 0)}
        short = sum(a - b for a, b in gap.values())
        print(f"[대조] 동을 다시 더해 시군구 표와 맞춰 보니 어긋난 자리 {len(gap)}곳 "
              f"(모자란 곳 {short:,}곳)")
        for k, (a, b) in sorted(gap.items(), key=lambda x: -(x[1][0] - x[1][1]))[:4]:
            print(f"   {k[0]} {k[1]}: 시군구 표 {a:,} ↔ 동 합계 {b:,}")

    top = sorted([r for r in out if r["병의원_계"] != DASH],
                 key=lambda r: -r["병의원_계"])[:5]
    print("병의원이 가장 많은 동: " + ", ".join(
        f"{r['시도']} {r['시군구']} {r['행정동']} {r['병의원_계']}곳" for r in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
