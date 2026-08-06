"""Test-tree wide setup.

Collection uses ``--import-mode=importlib`` (see ``pyproject.toml``). Without it, two
test modules sharing a basename in different directories — ``tests/seo/test_router.py``
and ``tests/geo/test_router.py``, for instance — collide during collection, because the
default *prepend* mode keys modules by basename alone. Each engine gets to name its
files after what they test rather than after what is already taken.

The trade-off is that importlib mode does not put a test module's own directory on
``sys.path``, so ``from support import ...`` inside ``tests/seo/`` stops resolving. Rather
than make every suite spell out a package path — and rather than grow a hand-maintained
list here that the next engine forgets to update — every immediate subdirectory of
``tests/`` is added once, at collection time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent

# 시험에서는 호스트 간격을 두지 않는다.
#
# 운영 기본값은 1초다(작업의뢰서 §5.2). 그 값이 시험에도 그대로 걸리면 **시험이 실제로
# 잠든다** — 2026-08-06 실측에서 전체 스위트가 86초에서 600초가 됐다. 느린 시험은 결국
# 안 돌리게 되고, 안 돌리는 시험은 없는 시험이다.
#
# 여기서 끄는 것은 **간격뿐**이다. 간격 규칙 자체는 `tests/common/test_pacing.py` 가
# 가짜 시계로 지키고, 같은 호스트에 요청이 겹치지 않는다는 성질은
# `tests/seo/test_console_crawl.py` 가 간격을 켠 채 확인한다. 끄고 넘어가는 것이 아니라,
# 잠들지 않고 확인하는 자리를 따로 둔 것이다.
#
# `setdefault` 인 이유: 특정 시험이 스스로 값을 정하고 싶을 때 그 값을 존중한다.
os.environ.setdefault("VEO_CRAWL_MIN_INTERVAL_SECONDS", "0")

# 한국 경유는 **시험에서 꺼 둔다.** setdefault 가 아니라 덮어쓴다.
#
# 왜 이것만 강하게 끄는가. 설정은 `apps/api/.env` 를 자동으로 읽고(core/settings.py),
# 개발 장비의 그 파일에는 경유 주소와 열쇠가 들어 있다. 그래서 시험이 받은 응답이
# `looks_like_interstitial` 이면 `RetryViaKorea` 가 발동하고, 그 경로는 `SafeFetcher` 에
# **주입한 transport 를 쓰지 않으므로 진짜 바깥으로 나간다.**
#
# 실측(2026-08-06): 모의 전송에 428바이트를 넣어 두었는데 수집 결과가 실제 남의 사이트
# 본문 559바이트였다. 시험이 조용히 인터넷을 다녀온 것이다. `.env` 가 없는 CI 에서는
# 안 나가므로 **로컬과 CI 의 동작이 달랐다** — 그 상태에서는 "시험 통과" 가 아무것도
# 보증하지 않는다(0-F).
#
# 경유가 켜진 상태를 확인해야 하는 시험은 가짜 경유를 직접 끼워 넣는다
# (`tests/common/test_retry_via_kr.py`). 진짜 바깥으로 나가는 시험은 없다.
os.environ["VEO_EGRESS_KR_URL"] = ""
os.environ["VEO_EGRESS_KR_TOKEN"] = ""


def _expose_suite_helper_modules() -> None:
    """Let each suite import its own sibling helpers by plain module name."""
    for directory in sorted(TESTS_ROOT.iterdir()):
        if not directory.is_dir() or directory.name.startswith((".", "__")):
            continue
        # Only suites that actually ship a helper need to be on the path; adding every
        # directory unconditionally would let a typo in one suite resolve against
        # another's module and pass for the wrong reason.
        has_helper = any(
            path.suffix == ".py" and not path.name.startswith("test_")
            and path.name != "conftest.py"
            for path in directory.iterdir()
        )
        if not has_helper:
            continue
        entry = str(directory)
        if entry not in sys.path:
            sys.path.insert(0, entry)


_expose_suite_helper_modules()
