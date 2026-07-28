"""VEO's public, unauthenticated surface.

This is the front door: someone types their clinic's URL, gets a real diagnosis, and
becomes a lead. It is also the only part of VEO exposed to the open internet, so it is
where abuse arrives — SSRF through a caller-supplied URL, quota drain, and VEO being
used to hammer a third party's server.

Four rules hold the package together, and each has a module:

``limits``
    Per IP, per session and per **target host**, counted separately. The host bucket is
    charged one unit per outbound request, keyed on the host VEO is about to contact, at
    the moment the guard approves the hop — so a redirect or a multi-URL scan cannot
    launder traffic onto a host that was never charged. That module's docstring states
    what the bucket does *not* cover; read it before relying on it.
``tokens``
    Result tokens of 256 bits, stored hashed, compared in constant time, expiring.
``schemas``
    Score, band, coverage, confidence, methodology version, top findings — and never an
    evidence excerpt, an internal address, or anything belonging to a customer.
``service``
    The same engines the console runs, at a smaller scope. Never a cheaper scorer.
``leads``
    A name and one contact channel, with the response saying what was stored.
``router``
    An ``APIRouter`` under ``/public/v1``. **Not mounted** — see
    ``INTEGRATION_REQUEST.md``.
"""

from __future__ import annotations

__all__: list[str] = []
