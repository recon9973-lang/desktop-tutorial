#!/usr/bin/env python
"""최초 조직과 관리자 계정을 만든다. 배포 후 딱 한 번 실행한다.

사용법:

    # 비밀번호를 물어본다 (권장 — 화면에 표시되지 않는다)
    python scripts/bootstrap.py --name "베놈" --slug venom \
        --email owner@example.com --display-name "이재훈"

    # 자동화 환경에서는 환경변수로 준다
    VEO_BOOTSTRAP_PASSWORD='...' python scripts/bootstrap.py ... --no-prompt

비밀번호는 **명령행 인자로 받지 않는다.** ``ps`` 로 같은 서버의 다른 사용자에게
그대로 보이고, 셸 기록에도 남기 때문이다. 성공해도 비밀번호는 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from veo.bootstrap import (
    MIN_BOOTSTRAP_PASSWORD_LENGTH,
    BootstrapRefused,
    bootstrap_first_organization,
)
from veo.db.session import session_scope

# The *name* of the variable to read the password from — not a password. S105 flags the
# string because it contains "PASSWORD"; the whole point of this module is that the value
# never appears in source or in argv.
_PASSWORD_ENV = "VEO_BOOTSTRAP_PASSWORD"  # noqa: S105


def _read_password(*, prompt: bool) -> str:
    """From the environment, or from a terminal that does not echo. Never from argv."""
    from_env = os.environ.get(_PASSWORD_ENV)
    if from_env:
        return from_env
    if not prompt:
        raise BootstrapRefused(
            f"{_PASSWORD_ENV} 환경변수가 비어 있습니다. "
            "--no-prompt 를 쓰려면 환경변수로 비밀번호를 주십시오."
        )
    if not sys.stdin.isatty():
        raise BootstrapRefused(
            "터미널이 아니므로 비밀번호를 물어볼 수 없습니다. "
            f"{_PASSWORD_ENV} 환경변수를 사용하십시오."
        )

    first = getpass.getpass("관리자 비밀번호: ")
    second = getpass.getpass("한 번 더 입력: ")
    if first != second:
        raise BootstrapRefused("두 번 입력한 비밀번호가 서로 다릅니다.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="최초 조직과 관리자 계정을 만든다 (최초 1회).",
        epilog=(
            f"비밀번호는 {_PASSWORD_ENV} 환경변수나 프롬프트로만 받는다. "
            "명령행 인자로는 받지 않는다 — ps 와 셸 기록에 남기 때문이다."
        ),
    )
    parser.add_argument("--name", required=True, help="조직 이름 (예: 베놈)")
    parser.add_argument("--slug", required=True, help="조직 식별자 (예: venom)")
    parser.add_argument("--email", required=True, help="관리자 이메일 (로그인 아이디)")
    parser.add_argument("--display-name", required=True, help="관리자 이름")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help=f"물어보지 않고 {_PASSWORD_ENV} 환경변수만 사용한다",
    )
    args = parser.parse_args(argv)

    try:
        password = _read_password(prompt=not args.no_prompt)
        with session_scope() as db:
            result = bootstrap_first_organization(
                db,
                organization_name=args.name,
                organization_slug=args.slug,
                email=args.email,
                display_name=args.display_name,
                password=password,
            )
    except BootstrapRefused as exc:
        print(f"중단했습니다. 아무것도 생성되지 않았습니다.\n  {exc}", file=sys.stderr)
        return 2

    print("최초 설정을 완료했습니다.")
    print(f"  조직      {args.name} ({result.organization_slug})")
    print(f"  관리자    {result.email}")
    print(f"  권한      {result.role}")
    print()
    print("이제 이 계정으로 로그인할 수 있습니다. 비밀번호는 화면에 표시하지 않습니다.")
    print(f"최소 길이는 {MIN_BOOTSTRAP_PASSWORD_LENGTH}자입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
