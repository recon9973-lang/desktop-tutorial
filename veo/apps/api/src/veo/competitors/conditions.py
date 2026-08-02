"""Reading the conditions a measurement was taken under, off the measurement itself.

:class:`~veo.compare.MeasurementConditions` is what makes a comparison legitimate, so
building one is the place where a comparison is most easily corrupted — not by malice but
by a default. A hardcoded ``locale="ko-KR"`` makes a Korean scan and an English scan look
alike; a defaulted ``device`` makes a mobile crawl comparable to a desktop one; counting
the URLs a crawl *requested* rather than the ones it *collected* hides a failed crawl
behind a healthy-looking page count.

So every field here is read from something that actually observed it:

============================  =========================================================
field                         source
============================  =========================================================
``spec_id`` / ``_version``    the :class:`~veo.scoring.ScoreResult` — the score carries
``spec_checksum``             its own methodology, and it is the only thing that can
``pages_examined``            ``len(context.documents)`` — pages that came back
``locale``                    ``context.locale``
``enabled_providers``         ``context.provider_states``, ``ENABLED`` only
``measured_at``               ``context.collected_at``
``collector_version``         **stated by the caller** — see below
``device`` / ``renderer``     **stated by the caller** — see below
============================  =========================================================

Three fields have no home on :class:`~veo.collect.contract.CollectionContext` today. They
are therefore required keyword arguments with **no defaults**, and a blank value raises
:class:`MissingConditionError` rather than passing through. A silently defaulted device is
exactly how two unlike measurements end up side by side in a customer's report.
``INTEGRATION_REQUEST.md`` asks for them to move onto the context, at which point these
arguments become derivations like the rest.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from veo.collect.contract import CollectionContext
from veo.compare import MeasurementConditions
from veo.contracts.enums import ProviderState
from veo.geo.service import GeoReadinessReport
from veo.scoring import ScoreResult

#: Fields VEO cannot yet derive and therefore refuses to guess.
DECLARED_FIELDS = ("collector_version", "device", "renderer")


class MissingConditionError(ValueError):
    """A condition VEO cannot derive was not stated, or was stated as blank.

    Deliberately fatal. The alternative — substituting a plausible default — produces a
    comparison that looks fine and is not, which is the single worst outcome this package
    can produce.
    """

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(
            f"측정 조건 '{field}'은(는) 값을 지정해야 합니다. VEO가 추론할 수 없는 항목이며, "
            "임의로 채우면 서로 다른 조건의 측정이 같은 조건인 것처럼 비교됩니다."
        )


def enabled_providers(states: Mapping[str, ProviderState]) -> tuple[str, ...]:
    """The providers that actually answered, sorted.

    Only ``ENABLED`` counts. ``DEGRADED`` and ``CIRCUIT_OPEN`` mean some checks came back
    ``UNKNOWN``, and a measurement with a degraded provider is not the same measurement as
    one with a healthy provider — treating them alike would let a coverage hole on one
    side read as a quality difference between the two sites.
    """
    return tuple(sorted(name for name, state in states.items() if state is ProviderState.ENABLED))


def conditions_from_score(
    score: ScoreResult,
    context: CollectionContext,
    *,
    collector_version: str,
    device: str,
    renderer: str,
) -> MeasurementConditions:
    """Build the conditions block for one scored measurement."""
    return MeasurementConditions(
        spec_id=score.spec_id,
        spec_version=score.spec_version,
        spec_checksum=score.spec_checksum,
        collector_version=_stated("collector_version", collector_version),
        pages_examined=len(context.documents),
        locale=context.locale,
        device=_stated("device", device),
        renderer=_stated("renderer", renderer),
        enabled_providers=enabled_providers(context.provider_states),
        measured_at=context.collected_at,
    )


class HasScore(Protocol):
    """이 모듈이 결과에서 읽는 전부 — score 하나. SEO 와 GEO 가 같은 뼈대다."""

    @property
    def score(self) -> Any: ...


def conditions_from_seo_scan(
    result: HasScore,
    context: CollectionContext,
    *,
    collector_version: str,
    device: str,
    renderer: str,
) -> MeasurementConditions:
    """Conditions for a completed :func:`veo.seo.service.run_seo_scan`."""
    return conditions_from_score(
        result.score,
        context,
        collector_version=collector_version,
        device=device,
        renderer=renderer,
    )


def conditions_from_geo_report(
    report: GeoReadinessReport,
    context: CollectionContext,
    *,
    collector_version: str,
    device: str,
    renderer: str,
) -> MeasurementConditions:
    """Conditions for a completed :func:`veo.geo.service.run_geo_readiness`.

    Identical machinery to the SEO path, and that is the point: a GEO score and an SEO
    score carry different ``spec_id`` values, so the guard refuses to compare one against
    the other without anything here having to know about it.
    """
    return conditions_from_score(
        report.score,
        context,
        collector_version=collector_version,
        device=device,
        renderer=renderer,
    )


def declared_conditions(
    *, collector_version: str, device: str, renderer: str
) -> dict[str, str]:
    """Validate the three stated fields on their own, for callers that measured elsewhere.

    The HTTP surface accepts already-finished measurements and therefore has no
    ``CollectionContext`` to read from. It still may not default these.
    """
    return {
        "collector_version": _stated("collector_version", collector_version),
        "device": _stated("device", device),
        "renderer": _stated("renderer", renderer),
    }


def _stated(field: str, value: str) -> str:
    if not value or not value.strip():
        raise MissingConditionError(field)
    return value.strip()


__all__ = [
    "DECLARED_FIELDS",
    "MissingConditionError",
    "conditions_from_geo_report",
    "conditions_from_score",
    "conditions_from_seo_scan",
    "declared_conditions",
    "enabled_providers",
]
