#!/usr/bin/env python3
"""발행된 채점 명세의 가중치와 검사 수를 세어 화면에 찍는다.

`docs/scoring/methodology.md` 의 표는 **손으로 옮겨 적은 것**이다. 명세가 바뀌면
문서만 남고, 남은 문서는 틀린 채로 읽힌다. 그래서 세는 일을 명령 하나로 남긴다.

    python3 scripts/spec_weights.py              최신 발행본
    python3 scripts/spec_weights.py 1.8.0        판을 지정
    python3 scripts/spec_weights.py --domain geo 도메인을 지정 (seo | geo)

관문(`is_gate`)은 가중 평균에 들어가지 않는다 — 곱해지기 때문이다. 그래서 합계는
관문과 점수 밖 영역(`contributes_to_score: false`)을 빼고 낸다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "packages" / "scoring-specs" / "specs"

DOMAINS = {
    "seo": "veo.seo.readiness",
    "geo": "veo.geo.readiness",
}


def _versions(spec_dir: Path) -> list[tuple[tuple[int, ...], Path]]:
    found = []
    for path in spec_dir.glob("*.yaml"):
        try:
            parts = tuple(int(piece) for piece in path.stem.split("."))
        except ValueError:
            continue
        found.append((parts, path))
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="예: 1.9.0. 비우면 가장 높은 판")
    parser.add_argument("--domain", choices=sorted(DOMAINS), default="seo")
    args = parser.parse_args()

    spec_dir = SPECS / DOMAINS[args.domain]
    available = _versions(spec_dir)
    if not available:
        print(f"명세 파일이 없습니다: {spec_dir}", file=sys.stderr)
        return 1

    if args.version is None:
        path = available[-1][1]
    else:
        path = spec_dir / f"{args.version}.yaml"
        if not path.exists():
            names = ", ".join(item[1].stem for item in available)
            print(f"그런 판이 없습니다: {args.version} (있는 것: {names})", file=sys.stderr)
            return 1

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    categories = document.get("categories", [])

    print(f"{document['spec_id']} {document['version']}  (발효 {document['effective_at']})")
    print()
    print(f"{'영역':<28} {'가중치':>8} {'검사':>6}  성격")
    for category in categories:
        checks = len(category.get("checks") or [])
        if category.get("is_gate"):
            nature = "관문 — 곱한다"
        elif category.get("contributes_to_score", True) is False:
            nature = "점수 밖 — 분모에 안 들어간다"
        else:
            nature = ""
        print(
            f"{category['id']:<28} {category.get('weight', 0):>8} {checks:>6}  {nature}"
        )

    scored = [
        category
        for category in categories
        if category.get("contributes_to_score", True) and not category.get("is_gate")
    ]
    total = round(sum(float(category.get("weight", 0)) for category in scored), 4)
    print()
    print(f"가중치 합 (관문·점수 밖 제외): {total}")
    if total != 100.0:
        # 100 이 아니면 재정규화가 필요하다는 뜻이고, 문서의 "정확히 100.0" 은 거짓이 된다.
        print("  ※ 100.0 이 아닙니다. 문서의 설명과 어긋납니다 — 어느 쪽이 맞는지 확인하십시오.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
