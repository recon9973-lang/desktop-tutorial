"""Put this suite's helper module on the import path.

The tree-wide ``tests/conftest.py`` only exposes helpers that sit in an *immediate*
subdirectory of ``tests/``. This suite is one level deeper, so it does the same job for
itself rather than asking the shared file (which this worker does not own) to change.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
