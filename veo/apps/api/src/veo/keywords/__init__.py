"""Naver keyword intelligence: lookup, related keywords, trends, lists and export.

The package's organising rule is that **every number carries where it came from**:

* ``NAVER_SEARCH_AD`` — official absolute counts, clicks, CTR, advertising competition.
* ``NAVER_DATALAB`` — a relative interest index, kept in its own table and its own type.
* ``CALCULATED`` — VEO's arithmetic: device totals and the opportunity score.
* ``VEO_INTERNAL`` — VEO's own usage, such as recently looked-up keywords.

None of them is ever blended into a single figure, and a value that does not exist is
reported as absent with a reason rather than as ``0``.

The router in this package is deliberately **not mounted**. ``veo.api.app`` belongs to the
integrator; requests to change anything outside this package are filed in
``INTEGRATION_REQUEST.md``.
"""

from __future__ import annotations
