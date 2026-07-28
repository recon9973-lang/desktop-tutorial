"""Competitor comparison and observed share of voice.

Two engines live here and they are kept apart on purpose.

``comparison`` answers *"are we behind, and on what"* using readiness measurements — and
it only answers when both sides were measured the same way. Every pairing goes through
:func:`veo.compare.assert_comparable`; a refusal that explains itself is the product, not
an error path.

``sov`` answers *"who did the answer engines actually cite"*. It is observation, not
readiness, and the two never merge into one figure. A zero denominator there is
``데이터 없음`` — nobody citing anybody is not a 0% share.
"""
