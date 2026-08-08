#!/usr/bin/env python3
"""서버에는 있는데 화면에서 못 부르는 API 를 찾는다.

`apps/api/openapi.json` 의 엔드포인트 전부와, `apps/web/src` 안에 실제로 적힌
경로 문자열을 맞춰 본다. 남는 것이 "만들었지만 화면에서 닿을 수 없는 것" 이다.

이 대조는 **문자열 대조**다. 두 가지를 못 잡는다는 것을 알고 쓴다.

* 경로를 변수로 조립하면(`${base}/api/x/${id}`) 여기서는 `[^/]*` 로 넓게 맞춘다.
  넓게 맞추므로 **놓치는 쪽이 아니라 덮어버리는 쪽**으로 틀린다 — 즉 이 스크립트가
  "없다" 고 한 것은 대체로 진짜 없고, "있다" 고 한 것 중에 가짜가 섞인다.
* 경로가 상수 표로 흩어져 있으면(`SCAN_PATHS = {...}`) 그 표의 값도 문자열이므로
  잡힌다. 하지만 조각을 이어 붙여 만드는 경우('/api/' + name)는 못 잡는다.

그래서 이 목록은 **판정이 아니라 후보**다. 한 건씩 코드로 확인한 뒤에 말한다.

    python3 scripts/ui_gap.py            후보만 출력
    python3 scripts/ui_gap.py --all      전체 엔드포인트와 판정
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENAPI = ROOT / "apps" / "api" / "openapi.json"
WEB_SRC = ROOT / "apps" / "web" / "src"

METHODS = ("get", "post", "put", "patch", "delete")

#: 화면이 부를 이유가 없는 것. 여기에 넣을 때는 왜 그런지 한 줄로 적는다.
EXPECTED_UNCALLED: dict[str, str] = {
    "GET /api/health": "감시용. 화면이 부르지 않는다",
    "GET /api/metrics": "Prometheus 수집용. 화면이 부르지 않는다",
    "DELETE /api/projects/{project_id}": "지원하지 않는다고 스스로 답하는 엔드포인트",
    "GET /api/organizations/current": "`/api/auth/me` 가 organization 을 함께 준다",
    "GET /api/organizations/{organization_id}": "위와 같음",
}


def endpoints() -> list[tuple[str, str, str]]:
    spec = json.loads(OPENAPI.read_text(encoding="utf-8"))
    rows = []
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if method in METHODS:
                rows.append((method.upper(), path, op.get("summary") or ""))
    return sorted(rows, key=lambda r: (r[1], r[0]))


def web_path_literals() -> list[str]:
    """`apps/web/src` 안에 적힌 API 경로 조각을 전부 긁는다.

    문자열 시작이 아니라 **중간**에 있는 것도 잡아야 한다 —
    `` `${baseUrl}/api/reports/...` `` 가 그런 모양이다.
    """
    found = subprocess.run(
        ["grep", "-rhoE", r"(/api/|/public/v1/)[A-Za-z0-9_./$%{}()-]*", str(WEB_SRC)],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return sorted({line.strip() for line in found.splitlines() if line.strip()})


def _matcher(literal: str) -> re.Pattern[str]:
    body = literal.split("?")[0]
    body = re.sub(r"\$\{[^}]*\}", "\x00", body).rstrip("/")
    parts = "".join("[^/]*" if ch == "\x00" else re.escape(ch) for ch in body)
    return re.compile(f"^{parts}/?$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="전체 엔드포인트와 판정")
    args = parser.parse_args()

    patterns = [_matcher(lit) for lit in web_path_literals()]
    rows = endpoints()

    candidates = []
    for method, path, summary in rows:
        probe = re.sub(r"\{[^}]*\}", "ZZZ", path).rstrip("/")
        called = any(rx.match(probe) for rx in patterns)
        if args.all:
            print(f"{'호출' if called else '  — '} {method:<6} {path:<52} {summary}")
        if not called and f"{method} {path}" not in EXPECTED_UNCALLED:
            candidates.append((method, path, summary))

    if args.all:
        print()
    print(f"엔드포인트 {len(rows)}개 · 화면에서 안 부르는 후보 {len(candidates)}개")
    print("(후보는 판정이 아니다 — 한 건씩 코드로 확인한 뒤에 말한다)")
    print()
    for method, path, summary in candidates:
        print(f"  {method:<6} {path:<52} {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
