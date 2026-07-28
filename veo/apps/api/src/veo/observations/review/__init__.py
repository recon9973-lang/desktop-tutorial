"""Human review of machine findings, and the gate between the two.

* :mod:`veo.observations.review.decisions` — the reviewer's state machine. A table of
  declared edges; nothing else is legal, and no automated trigger appears on any of them.
* :mod:`veo.observations.review.queue` — what needs a person, why, in what order, who
  holds it, and an append-only trail of every one of those facts.
* :mod:`veo.observations.review.gating` — what may appear in a customer-facing report.

This package imports :mod:`veo.observations.risk`; the reverse never happens. A
:class:`~veo.observations.risk.assessment.ClaimAssessment` has no field in which a review
state could be written, so the only way an assessment acquires one is by passing through
this package, where a human decision is required to produce it.
"""

from __future__ import annotations
