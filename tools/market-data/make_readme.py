#!/usr/bin/env python3
"""만들어 둔 표를 읽어 «무엇이 들어 있나» 대문(README)을 쓴다. 숫자는 표에서 센다."""
import csv, collections, pathlib

OUT = pathlib.Path("data/market")
num = lambda v: None if v in ("—", "", None) else float(v)


def main() -> int:
    sg = list(csv.DictReader((OUT / "market_sggu.csv").open(encoding="utf-8")))
    sj = list(csv.DictReader((OUT / "market_subject.csv").open(encoding="utf-8")))
    dg = list(csv.DictReader((OUT / "market_dong.csv").open(encoding="utf-8")))
    kk_p, sa_p = OUT / "market_kakao.csv", OUT / "market_sangga.csv"
    kk = list(csv.DictReader(kk_p.open(encoding="utf-8-sig"))) if kk_p.exists() else []
    sa = list(csv.DictReader(sa_p.open(encoding="utf-8-sig"))) if sa_p.exists() else []
    stores = sum(int(r["점포_계"]) for r in sa if r["점포_계"] != "—")
    blanks = {c: sum(1 for r in sg if r[c] == "—") for c in sg[0]}
    still = [c for c, v in blanks.items() if v]
    pop = sum(num(r["인구"]) or 0 for r in sg)
    n = sum(int(r["병의원_계"]) for r in sg)
    ok = sorted([r for r in sg if num(r["인구1만명당_병의원"])],
                key=lambda r: -num(r["인구1만명당_병의원"]))
    subj_tot = collections.Counter()
    for r in sj:
        subj_tot[r["진료과목"]] += int(r["표시기관수"])
    kinds = [c for c in sg[0] if c.startswith("종별_")]
    kind_tot = {k[3:]: sum(int(r[k]) for r in sg) for k in kinds}

    def tbl(rows, cols):
        head = "| " + " | ".join(cols) + " |\n|" + "|".join([" --- "] * len(cols)) + "|\n"
        return head + "".join("| " + " | ".join(str(c) for c in r) + " |\n" for r in rows)

    md = f"""# 지역별 병의원 상권 자료

전국 **병의원 {n:,}곳**(보건소·보건지소·보건진료소 제외) 을 **시군구 {len(sg)}곳** 으로 나누고,
같은 자리의 **주민등록 인구 {pop:,.0f}명** 과 붙여 만든 표다. 진료과목은 **{len(subj_tot)}종**.

## 어디서 온 자료인가

| 무엇 | 기준 시점 | 출처 |
| --- | --- | --- |
| 병의원 {n:,}곳 · 진료과목 {len(sj):,}쌍 | 2026년 6월 | 건강보험심사평가원 「전국 병의원 및 약국 현황」(공공누리 제1유형 · 출처표시) |
| 인구 · 남녀 | 2026-06-30 | 행정안전부 「주민등록 인구통계 · 행정동」 |
| 나이대 인구 | 2026-08-31 | 같은 곳(5세 단위 21칸) |
| 행정동 면적 | 2026-07-01 | 통계청 SGIS 행정동 경계 |
| 과목별 검색 수요 | 2025-09~2026-08 | 네이버 데이터랩 검색어 트렌드 |
| 지도 분류 | 2026-09-19 | 카카오 로컬(전국 훑기) |
| 업종별 점포 {stores:,}곳 | 2026년 6월 | 소상공인시장진흥공단 상가(상권)정보 |

원자료는 ANSEO(`veo-platform`) 저장소의 `apps/api/data/` 에 있다. 이 표는 그것을 합쳐 만든 것이라,
다시 만들려면 그 저장소를 먼저 내려받아야 한다.

```bash
git clone --depth 1 https://github.com/recon9973-lang/veo-platform /home/user/veo-platform
python3 tools/market-data/build_anseo.py            # 표 세 개를 다시 만든다
python3 tools/market-data/make_readme.py            # 이 대문을 다시 쓴다
```

## 무엇이 들어 있나

| 파일 | 한 줄이 뜻하는 것 | 줄 수 |
| --- | --- | ---: |
| `market_sggu.csv` | 시군구 하나 — 인구·면적·병의원 수·종별·밀집도·나이대·미용 겸업 | {len(sg):,} |
| `market_subject.csv` | 시군구 × 진료과목 — 내건 곳 / 전문의 있는 곳 / 전문의 없이 | {len(sj):,} |
| `market_kakao.csv` | 시군구 하나 — 카카오 지도가 그 병원을 무엇으로 분류했나 | {len(kk):,} |
| `market_sangga.csv` | 시군구 하나 — 업종별 가게 수와 «이 동네는 어떤 동네인가» | {len(sa):,} |
| `market_dong.csv` | 행정동 하나 — 인구·남녀·나이대·면적 | {len(dg):,} |
| `naver_datalab_subjects.csv` | 과목·시술 하나 — 검색 수요(피부과=100 기준) | 20 |
| `population_sggu.csv` | 사장님이 주신 시트를 옮긴 것(인구 만명) | 109 |
| `sggu_codes.csv` | 시군구 하나 — 공공 API 에 물을 때 쓰는 코드 | {len(sa):,}+ |
| `병의원_상권자료.xlsx` | 위를 한 권으로 묶은 것(표지 「읽는 법」 포함) | — |
| `screen/index.html` | 눌러 보며 찾는 화면(자료를 안에 넣어 둬 네트워크 없이 열린다) | — |

## 표를 읽을 때 꼭 알아야 할 것 두 가지

**하나 — 「표시기관수」는 전문 병원 수가 아니다.**
심평원은 한 병원이 표시한 진료과목을 모두 적는다. 그래서 피부과를 표시한 곳이 {subj_tot['피부과']:,}곳이지만
피부과 전문의가 있는 곳은 훨씬 적다. 마케팅에서는 **그 검색어로 부딪칠 수 있는 병원 수**라서 이 숫자가
오히려 쓸모 있고, 「진짜 그 과 병원」을 보려면 같은 표의 **과목전문의수** 칸을 본다.

**둘 — 「업종별상권」은 병원 자료가 아니라 «동네» 자료다.**
같은 인구라도 학원가·먹자골목·오피스는 오는 사람이 다르다. 「전국대비」가 100보다 크면
전국 평균보다 그 업종이 많다는 뜻이다. 상가자료는 «간판 달고 장사하는 자리» 만 잡으므로
심평원 병의원 수와는 원래 다르게 나온다.

**셋 — 자료마다 행정구역 시점이 다르다.**
인구는 2026-06-30(옛 이름), 나이대와 경계는 2026-07 개편 뒤 이름(「전남광주통합특별시」·
인천 제물포구/영종구/검단구)이다. 코드로 맞추면 전남 전체·광주 5구·인천 3구가 통째로 비어서,
코드로 못 찾은 자리는 **이름으로** 한 번 더 찾아 메웠다.

## 전국 그림

전국 평균 **인구 1만 명당 병의원 {n / pop * 10000:.1f}곳** (1개소당 {pop / n:,.0f}명).

### 병원 종류별

{tbl([(k, f'{v:,}') for k, v in sorted(kind_tot.items(), key=lambda x: -x[1])], ['종류', '전국'])}
### 가장 빽빽한 곳 10

{tbl([(f"{r['시도']} {r['시군구']}", f"{int(num(r['인구'])):,}", r['병의원_계'],
       r['인구1만명당_병의원'], r['1개소당_인구']) for r in ok[:10]],
     ['지역', '인구', '병의원', '인구 1만명당', '1개소당 인구'])}
### 가장 헐거운 곳 10

{tbl([(f"{r['시도']} {r['시군구']}", f"{int(num(r['인구'])):,}", r['병의원_계'],
       r['인구1만명당_병의원'], r['1개소당_인구']) for r in ok[-10:]],
     ['지역', '인구', '병의원', '인구 1만명당', '1개소당 인구'])}
## 아직 «—» 인 것

| 못 잰 것 | 왜 | 어떻게 하면 잴 수 있나 |
| --- | --- | --- |
| 세종 나이대 | 행안부 나이대 자료에 세종이 통째로 없다 | 행안부 화면에서 세종 나이대만 따로 읽는다(인구·남녀·면적은 채웠다) |
| 한 달에 몇 번 검색되는지(절대 검색량) | 공개 API 에 없다 | 네이버 검색광고 「키워드도구」 열쇠(3종)를 저장소에 넣으면 잰다 |
| 지도에서 검색하면 몇 곳이 잡히는지 | 네이버 지도 API 는 5곳까지만 준다(실측) | 카카오 로컬 열쇠를 저장소에 넣으면 잰다 |
| 읍면동 단위 병의원 수 | 심평원 읍면동 표기와 행정동 이름이 늘 같지는 않다 | 병원 좌표와 행정동 경계를 겹쳐 센다 |

지금 «—» 가 남은 칸: {", ".join(f"{c} {v}곳" for c, v in blanks.items() if v) or "없다"}.

숫자를 지어내지 않는다. 못 잰 것은 «—» 로 둔다.
"""
    (OUT / "README.md").write_text(md, encoding="utf-8")
    print(f"대문 {len(md):,}자 · 시군구 {len(sg)} · 과목쌍 {len(sj)} · 행정동 {len(dg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
