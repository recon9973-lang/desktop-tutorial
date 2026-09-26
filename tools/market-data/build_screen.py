#!/usr/bin/env python3
"""화면 틀(템플릿)에 자료를 넣어 한 파일짜리 화면을 만든다.

나가는 곳: data/market/screen/index.html — 이것을 그대로 올린다.
자료를 바깥에서 받아오지 않고 안에 넣는 이유는, 올라간 화면이 네트워크 없이도
그대로 열리게 하기 위해서다.
"""
import csv, json, pathlib

ROOT = pathlib.Path("data/market")
SCREEN = ROOT / "screen"
TPL = pathlib.Path("tools/market-data/screen/index.template.html")

# 데이터랩 이름 ↔ 심평원 진료과목 이름. **같은 과목일 때만** 잇는다.
ALIAS = {"재활의학과·도수치료": "재활의학과"}


def main() -> int:
    demand = {}
    with (ROOT / "naver_datalab_subjects.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nm = ALIAS.get(r["과목·키워드"], r["과목·키워드"])
            demand[nm] = round(float(r["피부과=100 기준 평균"]))
    subj_names = set(json.loads((SCREEN / "subjects.json").read_text(encoding="utf-8"))["이름"])
    demand = {k: v for k, v in demand.items() if k in subj_names}

    html = TPL.read_text(encoding="utf-8")
    for mark, payload in (
        ("__REGIONS__", (SCREEN / "regions.json").read_text(encoding="utf-8")),
        ("__SUBJECTS__", (SCREEN / "subjects.json").read_text(encoding="utf-8")),
        ("__DEMAND__", json.dumps(demand, ensure_ascii=False, separators=(",", ":"))),
    ):
        html = html.replace(mark, payload)
    out = SCREEN / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"{out} {out.stat().st_size / 1024:.0f}KB · 검색 수요 이어붙인 과목 {len(demand)}개: "
          f"{', '.join(sorted(demand))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
