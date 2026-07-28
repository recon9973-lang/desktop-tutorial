"""Naver adapters.

Three modules, and the separation between them is load-bearing:

* :mod:`veo.providers.naver.searchad` — the official Search Ad API. Absolute monthly
  search counts, clicks, CTR, an advertising competition label, ad depth.
* :mod:`veo.providers.naver.datalab` — DataLab. A *relative* interest index, 0-100,
  scaled inside the window that was requested. It is not a search volume.
* :mod:`veo.providers.naver.errors` — typed failures, backoff, a circuit breaker, and
  the single ``UNKNOWN`` value that every unanswerable call degrades to.

``searchad`` and ``datalab`` do not import each other. That is checked by a test, and it
is what makes it structurally impossible for an interest index to be routed into a field
that means "number of searches".
"""

from __future__ import annotations
