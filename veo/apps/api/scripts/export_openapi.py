"""Write the OpenAPI document to ``apps/api/openapi.json``.

The committed document is the API contract. The TypeScript client is generated from it,
and ``tests/contract`` fails if the running application and the committed file disagree —
so an API change cannot merge without regenerating both.

Usage:
    python scripts/export_openapi.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from veo.api.app import create_app

OUTPUT = Path(__file__).resolve().parents[1] / "openapi.json"


def render() -> str:
    document = create_app().openapi()
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the committed document is stale",
    )
    args = parser.parse_args()

    rendered = render()

    if args.check:
        if not OUTPUT.exists():
            print(f"{OUTPUT} does not exist; run without --check", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT} is out of date with the application. "
                "Run: python scripts/export_openapi.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT} is up to date")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
