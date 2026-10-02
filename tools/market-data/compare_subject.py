#!/usr/bin/env python3
"""시군구 × 진료과목을 **API 와 지금 표**로 나란히 놓고 대조한다.

왜: 자료 출처를 파일에서 API 로 바꾸기 전에 «숫자가 어긋나지 않는가» 를 먼저 본다.
받다 만 상태에서도 **받은 만큼만** 대조한다(없는 자리를 0으로 치지 않는다).

읽는 것:  raw/hira_sggu_subject.jsonl  (API · 시군구 × 과목 기관 수)
         market_subject.csv            (지금 표 · 파일 자료로 만든 것)
"""
import collections, csv, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_anseo import hira_region_api

OUT = pathlib.Path("data/market")
RAW = OUT / "raw"


def main() -> int:
    src = RAW / "hira_sggu_subject.jsonl"
    if not src.exists():
        print(f"{src} 가 없다 — 러너로 `sggu-subject` 를 먼저 돌린다"); return 2

    tab = {(r["시도"], r["시군구"]) for r in
           csv.DictReader((OUT / "market_sggu.csv").open(encoding="utf-8-sig"))}

    def fit(k):
        """표에 그 자리가 없고 시 한 줄만 있으면 시로 묶는다(화성 4개 구 → 화성시)."""
        if k in tab:
            return k
        for s2, g2 in tab:
            if s2 == k[0] and g2.endswith("시") and k[1].startswith(g2[:-1]):
                return (s2, g2)
        return k

    # 과목 코드 ↔ 이름.
    # [내가 틀린 자리 2026-10-02] API 가 이름을 안 줘서 코드표만 보고 맞추려다
    # 이름이 통째로 비어 «표가 전부 0» 으로 보였다. 자료가 아니라 내 대조가 틀린 것이었다.
    # 코드↔이름은 심평원 파일에 그대로 있다(코드는 안 바뀐다) — 거기서 가져온다.
    names = {}
    cp = RAW / "hira_subject_codes.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")):
            if c.get("dgsbjtCdNm"):
                names[c["dgsbjtCd"]] = c["dgsbjtCdNm"]
    if not names:
        import gzip
        fp = pathlib.Path("/home/user/veo-platform/apps/api/data/hira/2026-06/subjects.csv.gz")
        if fp.exists():
            lines = [l for l in gzip.open(fp, "rt", encoding="utf-8-sig")
                     if not l.startswith("#")]
            for r in csv.DictReader(lines):
                names.setdefault(r["진료과목코드"].strip(), r["진료과목코드명"].strip())
            print(f"[이름] 심평원 파일에서 과목 이름 {len(names)}개를 가져왔다")

    # 한 자리가 **코드 둘**로 갈려 있을 수 있다.
    # [실측 2026-10-02] 광주는 심평원 안에 「광주」와 「전남광주」 두 시도코드가 함께
    # 있다. 훑기가 앞의 것(2곳짜리)만 지나간 참이라 API 가 0 을 돌려줬는데,
    # 그걸 «API 가 틀렸다» 로 읽으면 안 된다. **그 자리의 코드를 다 받은 자리만** 견준다.
    want_pairs = collections.defaultdict(set)
    import gzip
    mp = RAW / "hira_master.csv.gz"
    if mp.exists():
        for r in csv.DictReader(gzip.open(mp, "rt", encoding="utf-8")):
            if r["sidoCd"] and r["sgguCd"]:
                k = fit(hira_region_api(r))
                want_pairs[k].add((r["sidoCd"], r["sgguCd"]))

    B, got_pairs = collections.Counter(), collections.defaultdict(set)
    for line in src.open(encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        k = fit(hira_region_api({"sidoCdNm": d["sidoCdNm"], "sgguCdNm": d["sgguCdNm"],
                                 "XPos": "", "YPos": ""}))
        if d.get("dgsbjtCdNm"):
            names.setdefault(d["dgsbjtCd"], d["dgsbjtCdNm"])
        B[(k[0], k[1], d["dgsbjtCd"])] += d["count"]
        got_pairs[k].add((d["sidoCd"], d["sgguCd"]))

    seen_reg = {k for k in got_pairs
                if not want_pairs or want_pairs.get(k, set()) <= got_pairs[k]}
    half = len(got_pairs) - len(seen_reg)
    if half:
        print(f"[견주지 않음] 그 자리의 코드를 아직 다 못 받은 곳 {half}곳")

    A = {}
    name2cd = {v: k for k, v in names.items()}
    for r in csv.DictReader((OUT / "market_subject.csv").open(encoding="utf-8-sig")):
        cd = name2cd.get(r["진료과목"])
        if cd:
            A[(r["시도"], r["시군구"], cd)] = int(r["표시기관수"])

    if not names:
        print("과목 코드↔이름을 못 만들었다 — 이름 없이 코드로만 견준다")
    # **받은 자리만** 견준다
    keys = [k for k in set(A) | set(B) if (k[0], k[1]) in seen_reg]
    if not keys:
        print("견줄 자리가 없다"); return 2
    ta = sum(A.get(k, 0) for k in keys)
    tb = sum(B.get(k, 0) for k in keys)
    print(f"받은 자리 {len(seen_reg)}곳 / 표 {len(tab)}곳 · 견준 칸 {len(keys):,}")
    print(f"기관×과목 — 표 {ta:,} · API {tb:,} ({tb-ta:+,} · "
          f"{(tb/ta-1)*100:+.2f}%)" if ta else "")
    same = sum(1 for k in keys if A.get(k, 0) == B.get(k, 0))
    w2 = sum(1 for k in keys if abs(B.get(k,0)-A.get(k,0)) <= max(2, A.get(k,0)*0.02))
    w5 = sum(1 for k in keys if abs(B.get(k,0)-A.get(k,0)) <= max(3, A.get(k,0)*0.05))
    print(f"똑같은 칸 {same:,} ({same/len(keys)*100:.1f}%) · "
          f"2% 안 {w2:,} ({w2/len(keys)*100:.1f}%) · 5% 안 {w5:,} ({w5/len(keys)*100:.1f}%)")

    # 자리별로도 본다
    ra = collections.Counter(); rb = collections.Counter()
    for k in keys:
        ra[(k[0], k[1])] += A.get(k, 0); rb[(k[0], k[1])] += B.get(k, 0)
    rok = sum(1 for r in ra if abs(rb[r]-ra[r]) <= max(3, ra[r]*0.02))
    print(f"\n자리별(시군구) — 2% 안에 드는 곳 {rok} / {len(ra)}")
    bad = sorted(((rb[r]-ra[r], r) for r in ra), key=lambda x: -abs(x[0]))[:6]
    print("가장 많이 달라진 자리:")
    for d, r in bad:
        pct = f"{d/ra[r]*100:+.1f}%" if ra[r] else "—"
        print(f"   {r[0]} {r[1]:<12} 표 {ra[r]:>6,} → API {rb[r]:>6,} ({d:+}, {pct})")

    cell = sorted(((B.get(k,0)-A.get(k,0), k) for k in keys), key=lambda x: -abs(x[0]))[:6]
    print("\n가장 많이 달라진 칸:")
    for d, k in cell:
        nm = names.get(k[2], k[2])
        print(f"   {k[0]} {k[1]} · {nm:<12} 표 {A.get(k,0):>5,} → API {B.get(k,0):>5,} ({d:+})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
