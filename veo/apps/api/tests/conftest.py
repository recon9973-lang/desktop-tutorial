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

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent


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
