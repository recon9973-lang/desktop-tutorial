"""Orchestration: resolve the competitors, build the measurements, run the engines.

Two seams are protocols rather than concrete classes, and both exist for a reason beyond
testability.

:class:`CompetitorDirectory` is where tenancy is enforced. Every lookup goes through
``tenant_select`` and ``assert_tenant_scoped``, and a competitor belonging to another
organization produces exactly the same "not found" as one that exists nowhere — a
distinct error would turn the endpoint into an existence oracle.

:class:`ComparisonStore` is where a comparison is kept. **The shipped implementation is
in-memory and therefore per-process and not durable** — there is no
``competitor_comparisons`` table in the schema and this worker may not add one.
``INTEGRATION_REQUEST.md`` §1 asks for it. Until it lands, comparisons do not survive a
restart and are not shared between workers, and that limitation is stated here rather
than discovered in production.

Two integrity rules live in this module, both of which refuse rather than repair:

* a score whose ``spec_checksum`` does not match the published specification on disk is
  not a VEO score, and is rejected. Otherwise a caller could hand over numbers produced
  by a document nobody can audit and have them compared as though they were ours;
* an unrecognised check status is rejected rather than coerced to ``UNKNOWN``, because
  silently downgrading a status removes a check from the comparison denominator.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.compare import MeasurementConditions
from veo.competitors.comparison import (
    CategoryMeasurement,
    ComparisonResult,
    Measurement,
    compare,
)
from veo.competitors.conditions import MissingConditionError, declared_conditions
from veo.competitors.schemas import (
    ComparisonCreateRequest,
    MeasurementInput,
    ObservedVisibilityInput,
    ScoreInput,
)
from veo.competitors.sov import (
    ObservedVisibility,
    ParticipantVisibility,
    ShareOfVoiceReport,
    share_of_voice,
)
from veo.db.models.identity import Competitor, Project
from veo.organizations.errors import ReferenceNotFoundError
from veo.scoring import CheckStatus, ScoringSpec, SpecNotFoundError, load_spec

BASELINE_KEY = "self"

PROJECT_NOT_FOUND_KO = "프로젝트를 찾을 수 없습니다."
COMPETITOR_NOT_FOUND_KO = "경쟁사를 찾을 수 없습니다."

SEPARATION_NOTE_KO = (
    "준비도 비교와 관측된 AI 가시성은 서로 다른 측정입니다. 한 숫자로 합치거나 한쪽을 "
    "다른 쪽의 근거로 쓰지 마십시오."
)


class MeasurementRejected(ValueError):
    """The submitted measurement cannot be trusted enough to compare."""

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


# --------------------------------------------------------------------------- #
# Competitor directory
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CompetitorRef:
    """The little a comparison needs to know about a competitor row."""

    id: uuid.UUID
    display_name: str
    origin: str
    selection_source: str
    """CUSTOMER_SPECIFIED | VEO_SUGGESTED — share of voice moves with who chose the set."""
    is_active: bool


class CompetitorDirectory(Protocol):
    def resolve(
        self,
        principal: Principal,
        project_id: uuid.UUID,
        competitor_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, CompetitorRef]: ...


@dataclass(frozen=True, slots=True)
class SqlCompetitorDirectory:
    """The real directory. Every statement carries its organization filter."""

    session: Session

    def resolve(
        self,
        principal: Principal,
        project_id: uuid.UUID,
        competitor_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, CompetitorRef]:
        self._require_project(principal, project_id)

        wanted = list(dict.fromkeys(competitor_ids))
        if not wanted:
            return {}

        statement = (
            tenant_select(Competitor, principal)
            .where(Competitor.project_id == project_id)
            .where(Competitor.id.in_(wanted))
        )
        assert_tenant_scoped(statement, principal.organization_id)

        found = {
            row.id: CompetitorRef(
                id=row.id,
                display_name=row.display_name,
                origin=row.origin,
                selection_source=row.selection_source,
                is_active=row.is_active,
            )
            for row in self.session.scalars(statement)
        }

        missing = [competitor_id for competitor_id in wanted if competitor_id not in found]
        if missing:
            raise ReferenceNotFoundError(COMPETITOR_NOT_FOUND_KO)
        return found

    def _require_project(self, principal: Principal, project_id: uuid.UUID) -> None:
        statement = tenant_select(Project, principal).where(Project.id == project_id)
        assert_tenant_scoped(statement, principal.organization_id)
        if self.session.scalars(statement).one_or_none() is None:
            raise ReferenceNotFoundError(PROJECT_NOT_FOUND_KO)


@dataclass
class InMemoryCompetitorDirectory:
    """A directory backed by a dictionary, for tests that are not about SQL."""

    rows: dict[tuple[uuid.UUID, uuid.UUID], dict[uuid.UUID, CompetitorRef]] = field(
        default_factory=dict
    )

    def add(
        self, organization_id: uuid.UUID, project_id: uuid.UUID, competitor: CompetitorRef
    ) -> None:
        self.rows.setdefault((organization_id, project_id), {})[competitor.id] = competitor

    def resolve(
        self,
        principal: Principal,
        project_id: uuid.UUID,
        competitor_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, CompetitorRef]:
        known = self.rows.get((principal.organization_id, project_id), {})
        resolved: dict[uuid.UUID, CompetitorRef] = {}
        for competitor_id in dict.fromkeys(competitor_ids):
            found = known.get(competitor_id)
            if found is None:
                raise ReferenceNotFoundError(COMPETITOR_NOT_FOUND_KO)
            resolved[competitor_id] = found
        return resolved


# --------------------------------------------------------------------------- #
# Comparison store
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ComparisonRecord:
    """A comparison as it was produced, with the tenant it belongs to."""

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    created_by: uuid.UUID
    payload: dict[str, Any]


class ComparisonStore(Protocol):
    def save(self, record: ComparisonRecord) -> ComparisonRecord: ...

    def get(
        self, organization_id: uuid.UUID, comparison_id: uuid.UUID
    ) -> ComparisonRecord | None: ...

    def list(
        self,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[ComparisonRecord], int]: ...


@dataclass
class InMemoryComparisonStore:
    """Newest first, scoped by organization.

    Not durable. See the module docstring and ``INTEGRATION_REQUEST.md`` §1 — the schema
    has nowhere to put a comparison and this worker may not add a table.
    """

    records: list[ComparisonRecord] = field(default_factory=list)

    def save(self, record: ComparisonRecord) -> ComparisonRecord:
        self.records.append(record)
        return record

    def get(
        self, organization_id: uuid.UUID, comparison_id: uuid.UUID
    ) -> ComparisonRecord | None:
        for record in self.records:
            if record.id == comparison_id and record.organization_id == organization_id:
                return record
        return None

    def list(
        self,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[ComparisonRecord], int]:
        matching = [
            record
            for record in reversed(self.records)
            if record.organization_id == organization_id and record.project_id == project_id
        ]
        return matching[offset : offset + limit], len(matching)


# --------------------------------------------------------------------------- #
# Building measurements
# --------------------------------------------------------------------------- #


def load_verified_spec(score: ScoreInput) -> ScoringSpec:
    """The published specification this score claims to have been produced by.

    The checksum is verified, not trusted. A number whose methodology document cannot be
    produced on demand is not defensible, and comparing two of them is worse.
    """
    try:
        spec = load_spec(score.spec_id, score.spec_version)
    except SpecNotFoundError as exc:
        raise MeasurementRejected(
            f"발행된 점수 명세를 찾을 수 없습니다: {score.spec_id}@{score.spec_version}. "
            "발행되지 않은 방법론으로 계산된 점수는 비교할 수 없습니다."
        ) from exc

    if spec.checksum != score.spec_checksum:
        raise MeasurementRejected(
            "점수에 적힌 명세 체크섬이 발행본과 다릅니다. 감사할 수 없는 문서로 계산된 "
            "점수는 비교 대상이 될 수 없습니다."
        )
    return spec


def build_measurement(
    *, key: str, label_ko: str, payload: MeasurementInput, spec: ScoringSpec
) -> Measurement:
    """Turn one submitted measurement into engine input, refusing anything ambiguous."""
    conditions = _conditions_of(payload)
    category_names = {category.id: category.name_ko for category in spec.categories}
    category_weights = {category.id: category.weight for category in spec.categories}

    return Measurement(
        key=key,
        label_ko=label_ko,
        conditions=conditions,
        overall_score=payload.score.overall_score,
        coverage=payload.score.coverage,
        confidence=payload.score.confidence,
        categories=tuple(
            CategoryMeasurement(
                category_id=category.category_id,
                name_ko=category_names.get(category.category_id, category.category_id),
                weight=category_weights.get(category.category_id, 0.0),
                score=category.score,
                coverage=category.coverage,
                scored_check_ids=tuple(category.scored_check_ids),
            )
            for category in payload.score.categories
        ),
        check_statuses={
            check_id: _status(check_id, raw)
            for check_id, raw in payload.score.check_statuses.items()
        },
    )


def build_observation(payload: ObservedVisibilityInput) -> ObservedVisibility:
    try:
        return ObservedVisibility(
            prompt_set_label=payload.prompt_set_label,
            engine_labels=tuple(payload.engine_labels),
            observed_answer_count=payload.observed_answer_count,
            decided_prompt_count=payload.decided_prompt_count,
            participants=tuple(
                ParticipantVisibility(
                    key=entry.key,
                    label_ko=entry.label_ko,
                    is_own_brand=entry.is_own_brand,
                    cited_answer_count=entry.cited_answer_count,
                    mentioned_answer_count=entry.mentioned_answer_count,
                    won_prompt_count=entry.won_prompt_count,
                )
                for entry in payload.participants
            ),
        )
    except ValueError as exc:
        raise MeasurementRejected(str(exc)) from exc


# --------------------------------------------------------------------------- #
# The three operations
# --------------------------------------------------------------------------- #


def create_comparison(
    principal: Principal,
    request: ComparisonCreateRequest,
    *,
    directory: CompetitorDirectory,
    store: ComparisonStore,
    observed_visibility: Callable[[Principal, uuid.UUID], ObservedVisibility] | None = None,
) -> ComparisonRecord:
    """Resolve, compare, and keep the result.

    The competitors are resolved *before* anything is computed, so a caller who names
    another organization's competitor gets a 404 rather than a comparison that quietly
    dropped one participant.
    """
    resolved = directory.resolve(
        principal,
        request.project_id,
        [entry.competitor_id for entry in request.competitors],
    )

    spec = load_verified_spec(request.baseline.measurement.score)
    baseline = build_measurement(
        key=BASELINE_KEY,
        label_ko=request.baseline.label_ko,
        payload=request.baseline.measurement,
        spec=spec,
    )

    competitors = []
    for entry in request.competitors:
        reference = resolved[entry.competitor_id]
        # Each side is checked against its own published specification. A competitor
        # measured under a different one still fails the comparability guard below —
        # this only refuses a document that cannot be produced at all.
        load_verified_spec(entry.measurement.score)
        competitors.append(
            build_measurement(
                key=str(entry.competitor_id),
                label_ko=reference.display_name,
                payload=entry.measurement,
                spec=spec,
            )
        )

    try:
        result = compare(
            baseline,
            competitors,
            spec=spec,
            allow_scope_variance=request.allow_scope_variance,
        )
    except ValueError as exc:
        raise MeasurementRejected(str(exc)) from exc

    # 점유율의 출처를 결과에 못 박는다. 이 표시가 없으면 손으로 적은 숫자가 잰 값과
    # 같은 모양으로 화면에 서고, 읽는 사람은 물을 자리조차 없다(0-A).
    visibility = None
    visibility_source = None
    if request.observation_run_id is not None:
        if observed_visibility is None:
            raise MeasurementRejected(
                "관측 실행에서 점유율을 계산할 수 없습니다. 이 배포에는 관측 조회 경로가 "
                "연결되어 있지 않습니다."
            )
        visibility = share_of_voice(observed_visibility(principal, request.observation_run_id))
        visibility_source = "OBSERVED"
    elif request.observed_visibility is not None:
        visibility = share_of_voice(build_observation(request.observed_visibility))
        visibility_source = "HAND_ENTERED"

    return store.save(
        ComparisonRecord(
            id=uuid.uuid4(),
            organization_id=principal.organization_id,
            project_id=request.project_id,
            created_at=datetime.now(UTC),
            created_by=principal.user_id,
            payload=comparison_payload(result, visibility, visibility_source),
        )
    )


def list_comparisons(
    principal: Principal,
    project_id: uuid.UUID,
    *,
    store: ComparisonStore,
    offset: int,
    limit: int,
) -> tuple[list[ComparisonRecord], int]:
    return store.list(
        principal.organization_id, project_id, offset=offset, limit=limit
    )


def get_comparison(
    principal: Principal, comparison_id: uuid.UUID, *, store: ComparisonStore
) -> ComparisonRecord | None:
    return store.get(principal.organization_id, comparison_id)


def comparison_payload(
    result: ComparisonResult,
    visibility: ShareOfVoiceReport | None,
    source: str | None = None,
) -> dict[str, Any]:
    """The stored, returned document. Readiness and observation stay in separate blocks.

    ``source`` 는 점유율 숫자가 **어디서 왔는지** 다 — `OBSERVED`(관측 실행에서 계산)
    인지 `HAND_ENTERED`(사람이 적어 넣음)인지. 이 표시가 없으면 손으로 적은 숫자가 잰
    값과 같은 모양으로 화면에 서고, 읽는 사람은 물을 자리조차 없다(0-A).
    """
    document = result.as_dict()
    document["share_of_voice"] = visibility.as_dict() if visibility is not None else None
    document["share_of_voice_source"] = source
    document["separation_note_ko"] = SEPARATION_NOTE_KO
    return document


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _conditions_of(payload: MeasurementInput) -> MeasurementConditions:
    try:
        stated = declared_conditions(
            collector_version=payload.conditions.collector_version,
            device=payload.conditions.device,
            renderer=payload.conditions.renderer,
        )
    except MissingConditionError as exc:
        raise MeasurementRejected(str(exc)) from exc

    return MeasurementConditions(
        spec_id=payload.score.spec_id,
        spec_version=payload.score.spec_version,
        spec_checksum=payload.score.spec_checksum,
        collector_version=stated["collector_version"],
        pages_examined=payload.conditions.pages_examined,
        locale=payload.conditions.locale,
        device=stated["device"],
        renderer=stated["renderer"],
        enabled_providers=tuple(sorted(set(payload.conditions.enabled_providers))),
        measured_at=payload.conditions.measured_at,
    )


def _status(check_id: str, raw: str) -> CheckStatus:
    try:
        return CheckStatus(raw)
    except ValueError as exc:
        raise MeasurementRejected(
            f"{check_id}: 알 수 없는 검사 상태 '{raw}'입니다. 모르는 상태를 UNKNOWN 으로 "
            "바꿔 받으면 그 항목이 조용히 비교 분모에서 빠집니다."
        ) from exc


def summaries(records: Sequence[ComparisonRecord]) -> list[Mapping[str, Any]]:
    """List rows, built from the stored document so a summary can never disagree with it."""
    return [
        {
            "id": record.id,
            "project_id": record.project_id,
            "created_at": record.created_at,
            "summary_ko": record.payload["summary_ko"],
            "comparable_count": record.payload["comparable_count"],
            "refused_count": record.payload["refused_count"],
            "confidence": record.payload["confidence"],
            "allow_scope_variance": record.payload["allow_scope_variance"],
        }
        for record in records
    ]


__all__ = [
    "BASELINE_KEY",
    "COMPETITOR_NOT_FOUND_KO",
    "PROJECT_NOT_FOUND_KO",
    "SEPARATION_NOTE_KO",
    "ComparisonRecord",
    "ComparisonStore",
    "CompetitorDirectory",
    "CompetitorRef",
    "InMemoryComparisonStore",
    "InMemoryCompetitorDirectory",
    "MeasurementRejected",
    "SqlCompetitorDirectory",
    "build_measurement",
    "build_observation",
    "comparison_payload",
    "create_comparison",
    "get_comparison",
    "list_comparisons",
    "load_verified_spec",
    "summaries",
]
