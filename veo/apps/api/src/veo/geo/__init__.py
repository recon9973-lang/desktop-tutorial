"""GEO **readiness**: can an AI answer engine reach, extract and verify this page.

This package answers one question and refuses the neighbouring one. Readiness is a
deterministic structural check on material VEO already fetched. Whether an engine
actually named or linked the brand is an observation, produced by a different engine,
stored in different tables, shown on a different screen, and never added to this number
(ADR 0003).

Nothing here decides points. Every module returns
:class:`~veo.scoring.CheckOutcome` values — a status, the evidence behind it and a named
confidence level — and ``veo.scoring.evaluate`` turns those into a score using the
published ``veo.geo.readiness`` specification.
"""

from veo.geo.service import (
    GEO_SPEC_ID,
    GeoReadinessReport,
    declared_check_ids,
    geo_collectors,
    run_geo_readiness,
)

__all__ = [
    "GEO_SPEC_ID",
    "GeoReadinessReport",
    "declared_check_ids",
    "geo_collectors",
    "run_geo_readiness",
]
