"""What an answer engine got wrong about a customer, and how sure anyone is.

Three modules, and the separation between them is the design:

* :mod:`veo.observations.risk.taxonomy` — the kinds of risk the methodology recognises
  and the severity band each one lands in. Severity is read from a versioned table; no
  caller anywhere chooses a number.
* :mod:`veo.observations.risk.assessment` — one finding: the exact span assessed, the
  stored answer it came from, what decided it, and — kept strictly apart — nothing at all
  about human review.
* :mod:`veo.observations.risk.entailment` — whether a cited source actually supports the
  sentence. With no usable language model this answers ``UNKNOWN`` and stops.

Human review lives next door in :mod:`veo.observations.review`, and the direction of the
import is load-bearing: ``review`` reads ``risk``, never the other way round. That is what
makes it structurally impossible for an automated verdict to acquire a review state.
"""

from __future__ import annotations
