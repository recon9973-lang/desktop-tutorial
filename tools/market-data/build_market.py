#!/usr/bin/env python3
"""모아 둔 원자료를 «지역별 병의원 상권표» 하나로 합친다(네트워크 안 씀).

들어오는 것
  data/market/population_sggu.csv          인구(사장님 시트)
  data/market/raw/hira_master.csv[.gz]     심평원 기관 마스터   (없으면 «—»)
  data/market/raw/hira_sggu_subject.jsonl  시군구×진료과목 기관수(없으면 «—»)
  data/market/raw/kakao_local.jsonl        카카오 검색 노출 수  (없으면 «—»)
  data/market/naver_datalab_subjects.json  과별 검색 수요(전국)

나가는 것
  data/market/market_sggu.csv     지역 한 줄 = 인구·기관수·밀집도·종별
  data/market/market_subject.csv  지역×진료과목
  data/market/README.md           무엇이 실측이고 무엇이 아직 «—» 인지

원칙: 없는 값은 «—» 로 남긴다. 추정으로 채우지 않는다.
"""
import csv, gzip, io, json, pathlib

ROOT = pathlib.Path("data/market")
RAW = ROOT / "raw"
DASH = "—"


def read_master() -> list[dict]:
    for p, op in ((RAW / "hira_master.csv", open), (RAW / "hira_master.csv.gz", gzip.open)):
        if p.exists():
            with op(p, "rt", encoding="utf-8") as f:  # type: ignore[arg-type]
                return list(csv.DictReader(f))
    return []


def read_jsonl(p: pathlib.Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.open(encoding="utf-8"):
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
    return out


def norm(s: str) -> str:
    """«서울특별시»·«경기도» 같은 이름을 사장님 시트의 «서울»·«경기» 에 맞춘다."""
    s = (s or "").strip()
    for a, b in (("특별자치시", ""), ("특별자치도", ""), ("광역시", ""), ("특별시", ""),
                 ("남도", "남"), ("북도", "북"), ("청도", "청"), ("기도", "기"), ("원도", "원")):
        if s.endswith(a):
            return s[: -len(a)] + b
    return s


def main() -> int:
    pop = {}
    with (ROOT / "population_sggu.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pop[(r["시도"], r["시군구"])] = int(r["인구_만명"])

    master = read_master()
    subj = read_jsonl(RAW / "hira_sggu_subject.jsonl")
    kakao = read_jsonl(RAW / "kakao_local.jsonl")

    # ── 지역별 집계 ──
    agg: dict[tuple, dict] = {}
    for r in master:
        k = (norm(r["sidoCdNm"]), r["sgguCdNm"].strip())
        a = agg.setdefault(k, {"전체": 0, "종별": {}, "의사수": 0})
        a["전체"] += 1
        a["종별"][r["clCdNm"] or "미상"] = a["종별"].get(r["clCdNm"] or "미상", 0) + 1
        try:
            a["의사수"] += int(r["drTotCnt"] or 0)
        except ValueError:
            pass

    kinds = sorted({k for a in agg.values() for k in a["종별"]})
    rows = []
    for (sido, sggu), p in sorted(pop.items()):
        if not sggu:
            continue  # 시도 합계 행은 따로
        a = agg.get((sido, sggu), {})
        n = a.get("전체")
        row = {"시도": sido, "시군구": sggu, "인구_만명": p,
               "병의원_전체": n if n is not None else DASH,
               "인구1만명당_병의원": round(n / p, 1) if n else DASH,
               "1개소당_인구_명": round(p * 10000 / n) if n else DASH,
               "의사수_합": a.get("의사수", DASH) or DASH}
        for k in kinds:
            row[f"종별_{k}"] = a.get("종별", {}).get(k, 0)
        rows.append(row)

    fields = ["시도", "시군구", "인구_만명", "병의원_전체", "인구1만명당_병의원",
              "1개소당_인구_명", "의사수_합"] + [f"종별_{k}" for k in kinds]
    with (ROOT / "market_sggu.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    # ── 지역 × 진료과목 ──
    kmap = {(r["region"], r["term"]): r.get("total") for r in kakao}
    srows = []
    for d in subj:
        sido, sggu = norm(d["sidoCdNm"]), d["sgguCdNm"].strip()
        p = pop.get((sido, sggu))
        nm = d.get("dgsbjtCdNm") or d["dgsbjtCd"]
        srows.append({
            "시도": sido, "시군구": sggu, "진료과목코드": d["dgsbjtCd"], "진료과목": nm,
            "기관수": d["count"], "인구_만명": p if p else DASH,
            "인구1만명당": round(d["count"] / p, 2) if p and d["count"] else DASH,
            "카카오_검색노출수": kmap.get((f"{sido} {sggu}", nm), DASH) or DASH,
        })
    if srows:
        with (ROOT / "market_subject.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(srows[0].keys()))
            w.writeheader(); w.writerows(srows)

    have = lambda n: "실측" if n else DASH
    (ROOT / "README.md").write_text(f"""# 지역별 병의원 상권 자료 — 무엇이 들어 있나

| 자료 | 상태 | 줄 수 | 출처 |
| --- | --- | ---: | --- |
| `population_sggu.csv` 인구 | 실측(사장님 시트) | {len(pop)} | 사장님 제공 시트(인구 만명) |
| `raw/hira_master.csv[.gz]` 기관 마스터 | {have(master)} | {len(master)} | 심평원 병원정보서비스 |
| `raw/hira_sggu_subject.jsonl` 시군구×과목 | {have(subj)} | {len(subj)} | 심평원 병원정보서비스 |
| `raw/kakao_local.jsonl` 검색 노출 수 | {have(kakao)} | {len(kakao)} | 카카오 로컬 |
| `naver_datalab_subjects.csv` 과별 검색 수요 | 실측 | — | 네이버 데이터랩 |
| `market_sggu.csv` 지역표 | {have(master)} | {len(rows)} | 위를 합친 것 |
| `market_subject.csv` 지역×과목표 | {have(srows)} | {len(srows)} | 위를 합친 것 |

«{DASH}» 는 **아직 못 잰 값**이다. 지어내지 않는다.
""", encoding="utf-8")
    print(f"지역표 {len(rows)}행 · 지역×과목 {len(srows)}행 · 마스터 {len(master)}행")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
