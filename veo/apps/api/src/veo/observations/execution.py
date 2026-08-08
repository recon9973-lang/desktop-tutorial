"""관측 실행 — 엔진을 돌리고, 그 결과를 되돌릴 수 없는 기록으로 남긴다.

`ObservationRunner` 는 이미 완성되어 있었고 `src/` 안에서 아무도 부르지 않았다. 이
모듈이 그것을 부르는 곳이다.

저장에서 지키는 것
------------------
**못 한 일을 함께 저장한다.** `RunReport.skipped` 와 `stopped_reason` 을 빼고 `runs` 만
남기면, 예산에 걸려 절반만 실행된 관측이 **완전한 측정처럼 읽힌다.** 그 위에서 계산한
노출률은 분모가 틀린 값이고, 틀렸다는 사실이 어디에도 남지 않는다. DB 스키마가
`executions_planned`·`executions_skipped`·`stopped_reason`·`skipped_detail`·`is_complete`
를 미리 갖추고 있는 것도 같은 이유다.

**답변 원문은 DB 에 넣지 않는다.** 포인터와 해시만 넣고 원문은 답변 저장소로 간다. 읽을
때마다 해시를 검증하므로, 바뀐 증거는 돌려주지 않고 거부된다 — 조용히 편집된 답변은
없는 답변보다 나쁘다. 여전히 증거처럼 보이기 때문이다.

**비용은 잰 단위 그대로.** `cost_usd` 에 넣고 `cost_krw` 는 비워 둔다. 환율을 지어내면
고객에게 제시하는 금액이 틀리고, 나중에 환율이 바뀌면 과거 기록까지 달라진다.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import final
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.contracts.enums import ReviewState
from veo.core.settings import Settings, get_settings
from veo.db.models.observation import (
    AIAnswer,
    AIEngine,
    BrandIdentity,
    Citation,
    EntityMention,
)
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import Prompt as PromptRow
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.observations.answer_store import FilesystemAnswerStore
from veo.observations.attribution import DisambiguatingMentionDetector
from veo.observations.brand_identity import BrandIdentityRecord, to_brand_profile
from veo.observations.db_answer_store import DatabaseAnswerStore
from veo.observations.detection.disambiguation import BrandProfile
from veo.observations.findings import assessment_from_held_mention, new_assessment_row
from veo.observations.metrics import AnswerFact
from veo.observations.prompts import Funnel, Intent, Prompt, PromptSet, Subject
from veo.observations.providers.registry import ProviderRegistry
from veo.observations.providers.storage import RecordedAnswerStore
from veo.observations.review.decisions import open_review
from veo.observations.runner import BrandTarget, ObservationRunner, RunReport
from veo.observations.runs import AccountState, RunConditions, SearchMode
from veo.observations.service import engine_registry, prompt_set_of, prompts_of


class BrandIdentityMissingError(ValueError):
    """이 프로젝트에 브랜드 식별자가 없다.

    이름 없이 언급을 셀 수는 없다. 빈 이름으로 돌리면 모든 답변이 "언급 없음" 이 되고,
    그것은 측정이 아니라 **우리가 무엇을 찾아야 할지 몰랐다는 사실**이다.
    """


@final
@dataclass(frozen=True, slots=True)
class EngineChoice:
    """어느 엔진을, 어떤 모델과 조건으로 돌릴지."""

    engine: str
    model: str
    search_mode: SearchMode = SearchMode.BROWSING
    account_state: AccountState = AccountState.ANONYMOUS


def brand_target_for(
    session: Session, principal: Principal, project_id: uuid.UUID
) -> tuple[BrandTarget, BrandIdentity]:
    """이 프로젝트가 자기 브랜드라고 선언한 이름과 도메인.

    경쟁사 식별자(`competitor_id` 가 있는 행)는 제외한다. 자기 브랜드는 하나다.
    """
    statement = (
        tenant_select(BrandIdentity, principal)
        .where(BrandIdentity.project_id == project_id)
        .where(BrandIdentity.competitor_id.is_(None))
        .where(BrandIdentity.is_active.is_(True))
    )
    assert_tenant_scoped(statement, principal.organization_id)
    row = session.scalars(statement).first()
    if row is None:
        raise BrandIdentityMissingError(
            "이 프로젝트에 브랜드 식별자가 등록되어 있지 않습니다. 무엇을 찾아야 하는지 "
            "모르는 채로 관측을 돌리면 모든 답변이 '언급 없음' 으로 기록되며, 그것은 "
            "측정이 아닙니다. 상호와 자사 도메인을 먼저 등록해 주십시오."
        )

    names = (row.display_name, *(str(alias) for alias in row.aliases or ()))
    domains = tuple(str(domain) for domain in row.own_domains or ())
    return BrandTarget(names=tuple(dict.fromkeys(names)), domains=domains), row


def competitor_profiles_for(
    session: Session, principal: Principal, project_id: uuid.UUID
) -> tuple[BrandProfile, ...]:
    """이 프로젝트가 선언한 경쟁사들 — **우리와 같은 표, 같은 모양**으로 읽는다.

    점유율은 비율이고, 비율은 그것을 이루는 두 숫자만큼만 정직하다. 우리 브랜드에는
    주소·전화번호를 다 채워 두고 경쟁사는 이름만 적어 두면, 경쟁사 쪽이 더 자주 검수
    보류로 떨어져 **분자에서 빠진다.** 산술을 한 글자도 안 고치고 우리 점유율이 오른다.
    `describe_identity_asymmetry_ko` 가 그 비대칭을 말하라고 있는 이유다.
    """
    statement = (
        tenant_select(BrandIdentity, principal)
        .where(BrandIdentity.project_id == project_id)
        .where(BrandIdentity.competitor_id.is_not(None))
        .where(BrandIdentity.is_active.is_(True))
        .order_by(BrandIdentity.entity_key)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return tuple(brand_profile_for(row) for row in session.scalars(statement))


def brand_profile_for(row: BrandIdentity) -> BrandProfile:
    """저장된 선언을 판별기가 읽는 형태로 — **전부** 옮긴다.

    이 함수가 생기기 전까지 관측은 이름과 도메인만 읽었다. 고객이 등록 화면에서 넣은
    소재지·대표번호·구별 표현은 저장은 되고 **측정에는 한 번도 쓰이지 않았다.** 흔한
    상호를 확정선 위로 올리는 것이 바로 그 전화번호다(`veo.observations.brand_identity`
    의 실측표). 즉 고객이 시간을 들여 넣은 값이 아무것도 바꾸지 못하고 있었다.
    """
    return to_brand_profile(
        BrandIdentityRecord(
            entity_key=row.entity_key,
            display_name=row.display_name,
            is_own_brand=row.competitor_id is None,
            competitor_id=str(row.competitor_id) if row.competitor_id else None,
            aliases=tuple(str(alias) for alias in row.aliases or ()),
            own_domains=tuple(str(domain) for domain in row.own_domains or ()),
            address_terms=tuple(str(term) for term in row.address_terms or ()),
            phone_numbers=tuple(str(number) for number in row.phone_numbers or ()),
            distinguishing_terms=tuple(str(term) for term in row.distinguishing_terms or ()),
            name_is_ambiguous=row.name_is_ambiguous,
        )
    )


def answer_store(
    organization_id: uuid.UUID, *, settings: Settings, session: Session | None = None
) -> RecordedAnswerStore:
    """조직 하나에 묶인 답변 저장소. 다른 조직의 포인터는 이 범위 밖으로 나가지 못한다.

    **기본은 DB 다.** 로컬 파일은 배포 환경에서 재배포마다 사라지고, 그때 `ai_answers`
    행은 남는데 가리키는 원문이 없어진다 — "이 판정의 근거를 보여 달라" 에 답할 수
    없게 된다(0-A).

    `observation_answer_store` 를 `filesystem` 으로 두면 예전 방식으로 돌아간다.
    개발 장비에서 DB 없이 돌려 볼 때를 위한 것이지, 배포에서 고를 값이 아니다.
    """
    if settings.observation_answer_store == "filesystem" or session is None:
        return FilesystemAnswerStore(
            root=Path(settings.observation_answer_store_root),
            organization_id=str(organization_id),
        )
    return DatabaseAnswerStore(session=session, organization_id=organization_id)


def _attempt_index(prompt_id: str, fingerprint: str, attempt: int) -> str:
    """`_Unit.run_id` 와 같은 식. 회차를 되찾기 위해 같은 방식으로 다시 만든다.

    `ObservationRun` 은 회차를 들고 다니지 않는다 — 실행의 신원은 `run_id` 하나이고
    그것이 `(질문, 조건, 회차)` 로 결정되므로, 되계산해 맞추면 추측 없이 회차를 얻는다.
    """
    payload = f"{prompt_id}|{fingerprint}|{attempt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _domain_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _engine_row(
    session: Session, *, provider: str, model: str, search_mode: str, state: str
) -> AIEngine:
    """엔진 행을 찾거나 만든다.

    `ai_answers.ai_engine_id` 가 이 표를 가리키므로 행이 없으면 답변을 저장할 수 없다.
    엔진·모델·검색모드 셋이 다르면 다른 조건이고, 다른 조건에서 나온 답변을 한 줄로
    묶으면 비교가 성립하지 않는다(ADR 0010).
    """
    existing = session.scalars(
        select(AIEngine)
        .where(AIEngine.provider == provider)
        .where(AIEngine.model == model)
        .where(AIEngine.search_mode == search_mode)
    ).one_or_none()
    if existing is not None:
        existing.provider_state = state
        return existing

    row = AIEngine(
        provider=provider,
        model=model,
        search_mode=search_mode,
        display_name=f"{provider} {model}",
        is_enabled=state == "ENABLED",
        provider_state=state,
    )
    session.add(row)
    session.flush()
    return row


class DuplicateEngineSlotError(ValueError):
    """같은 엔진·같은 모델·같은 검색 모드를 두 번 요청했다.

    조용히 하나로 합치면 **요청한 만큼 안 돌고도 다 돈 것처럼 보인다.** 반복 횟수는
    `repetitions` 로 정하는 것이지 같은 칸을 두 번 적어서 늘리는 것이 아니다.
    """


def _conditions_of(
    engines: Sequence[EngineChoice], *, locale: str
) -> dict[str, RunConditions]:
    """엔진 선택들을 실행 계획의 칸으로 만든다 — 칸 하나가 (엔진, 모델, 검색 모드) 하나다.

    엔진 이름만으로 칸을 잡으면 검색 켬과 끔 중 뒤엣것이 앞엣것을 덮는다. 그러면 실행은
    한 모드만 되는데 화면에는 두 모드를 고른 것으로 남아, **끔 모드의 노출률이 켬 모드의
    숫자로 채워진다.** 두 모드를 나란히 재는 것이 이 관측의 목적이므로 여기서 갈라야 한다.
    """
    built: dict[str, RunConditions] = {}
    for choice in engines:
        condition = RunConditions(
            engine=choice.engine,
            model=choice.model,
            # 요청 시점에는 모른다. 응답에서 읽은 값이 실행 기록에 들어간다.
            model_version="요청 시점 미상",
            search_mode=choice.search_mode,
            account_state=choice.account_state,
            locale=locale,
        )
        if condition.slot in built:
            raise DuplicateEngineSlotError(
                f"같은 조건을 두 번 요청했습니다: {choice.engine} / {choice.model} / "
                f"{choice.search_mode}. 여러 번 돌리려면 반복 횟수를 올리십시오."
            )
        built[condition.slot] = condition
    return built


def execute_observation(
    session: Session,
    principal: Principal,
    *,
    prompt_set_row: PromptSetRow,
    engines: Sequence[EngineChoice],
    repetitions: int,
    allow_below_floor: bool = False,
    settings: Settings | None = None,
    registry: ProviderRegistry | None = None,
    store: RecordedAnswerStore | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> ObservationRunRow:
    """프롬프트 집합을 엔진들에 돌리고 결과를 통째로 남긴다.

    한 트랜잭션에 담는다 — 실행은 되돌릴 수 없는 기록이고, **반쯤 저장된 실행이 가장
    나쁘다.** 절반만 남으면 그 위에서 계산한 비율의 분모가 틀리는데, 틀렸다는 사실이
    어디에도 없다.

    `registry` 와 `store` 를 밖에서 넣을 수 있는 것은 시험을 위해서만이 아니다. 이 함수가
    스스로 등록소를 만들면 **네트워크 없이는 저장 경로를 한 번도 확인할 수 없고**, 그러면
    실제 고객 실행이 첫 시험이 된다. 관측 실행은 되돌릴 수 없는 기록이므로 그것이 첫
    시험이 되어서는 안 된다.
    """
    resolved = settings or get_settings()
    prompt_rows = prompts_of(session, principal, prompt_set_row.id)
    prompt_set = prompt_set_of(prompt_set_row, prompt_rows)
    brand, identity = brand_target_for(session, principal, prompt_set_row.project_id)
    profile = brand_profile_for(identity)
    rivals = competitor_profiles_for(session, principal, prompt_set_row.project_id)

    resolved_registry = registry if registry is not None else engine_registry()
    runner = ObservationRunner(
        registry=resolved_registry,
        store=store
        if store is not None
        else answer_store(principal.organization_id, settings=resolved, session=session),
        detector=DisambiguatingMentionDetector(profile, rivals),
        max_concurrency=resolved.observation_max_concurrency,
        budget_usd=resolved.observation_budget_usd,
        repetition_interval=timedelta(
            seconds=resolved.observation_repetition_interval_seconds
        ),
        on_progress=on_progress,
    )

    conditions = _conditions_of(engines, locale=prompt_set_row.locale)

    started_at = datetime.now(UTC)
    report = runner.execute(
        prompt_set,
        conditions=list(conditions.values()),
        repetitions=repetitions,
        allow_below_floor=allow_below_floor,
    )
    finished_at = datetime.now(UTC)

    return _persist(
        session,
        principal,
        prompt_set_row=prompt_set_row,
        prompt_rows=prompt_rows,
        prompt_set=prompt_set,
        report=report,
        conditions=conditions,
        engines=engines,
        brand=brand,
        profile=profile,
        started_at=started_at,
        finished_at=finished_at,
        registry_states=resolved_registry.states(),
    )


def _persist(
    session: Session,
    principal: Principal,
    *,
    prompt_set_row: PromptSetRow,
    prompt_rows: Sequence[PromptRow],
    prompt_set: PromptSet,
    report: RunReport,
    conditions: Mapping[str, RunConditions],
    engines: Sequence[EngineChoice],
    brand: BrandTarget,
    profile: BrandProfile,
    started_at: datetime,
    finished_at: datetime,
    registry_states: Mapping[str, object],
) -> ObservationRunRow:
    # 엔진이 쓰는 질문 식별자는 내용 해시, DB 는 UUID 다. 저장된 행에서 같은 해시를
    # 다시 계산해 표를 만든다 — 순서에 기대면 프롬프트가 하나만 바뀌어도 어긋난다.
    by_hash = {_prompt_hash_of(row): row for row in prompt_rows}

    # 칸(엔진·모델·검색모드)마다 한 행이다. 엔진 이름으로 묶으면 검색 끔으로 나온 답변이
    # 검색 켬 행에 붙어, 나중에 "검색을 켰는데 인용이 0건" 이라는 없는 사실이 만들어진다.
    engine_rows = {
        condition.slot: _engine_row(
            session,
            provider=condition.engine,
            model=condition.model,
            search_mode=str(condition.search_mode),
            state=str(registry_states.get(condition.engine, "UNKNOWN")),
        )
        for condition in conditions.values()
    }

    run_row = ObservationRunRow(
        organization_id=principal.organization_id,
        project_id=prompt_set_row.project_id,
        prompt_set_id=prompt_set_row.id,
        repetitions_per_prompt=report.repetitions,
        # 엔진 **이름**의 목록이다(칸 이름이 아니다). `competitors/from_observation.py`
        # 가 이 값으로 `ai_engines.provider` 를 조회하므로 모드를 붙이면 조회가 빈다.
        # 한 엔진을 두 모드로 돌리면 이름이 두 번 들어오므로 여기서 한 번으로 줄인다.
        engines=list(dict.fromkeys(choice.engine for choice in engines)),
        competitor_ids=[],
        started_at=started_at,
        finished_at=finished_at,
        status="SUCCEEDED" if report.is_complete else "PARTIAL_SUCCESS",
        executions_attempted=len(report.runs),
        executions_valid=sum(1 for run in report.runs if run.is_valid_execution),
        executions_planned=len(report.runs) + len(report.skipped),
        executions_skipped=len(report.skipped),
        is_complete=report.is_complete,
        stopped_reason=str(report.stopped_reason) if report.stopped_reason else None,
        prompts_below_repetition_floor=(
            [prompt.prompt_id for prompt in prompt_set.prompts]
            if report.below_repetition_floor
            else []
        ),
        skipped_detail={
            "items": [
                {
                    "prompt_id": item.prompt_id,
                    "engine": item.engine,
                    "search_mode": item.search_mode,
                    "attempt": item.attempt,
                    "reason": str(item.reason),
                    "reason_ko": item.reason_ko,
                }
                for item in report.skipped
            ],
            "summary_ko": report.summary_ko,
            "unpriced_calls": report.unpriced_calls,
            "total_cost_usd": report.total_cost_usd,
        },
        confidence_breakdown={
            "engine_states": {name: str(state) for name, state in report.engine_states.items()},
            "below_repetition_floor": report.below_repetition_floor,
        },
    )
    session.add(run_row)
    session.flush()

    # 회차를 되찾기 위한 표. `run_id` 가 (질문, 조건, 회차) 로 결정되므로 되계산해 맞춘다.
    attempts: dict[str, int] = {}
    for prompt in prompt_set.prompts:
        for condition in conditions.values():
            for attempt in range(1, report.repetitions + 1):
                attempts[_attempt_index(prompt.prompt_id, condition.fingerprint, attempt)] = (
                    attempt
                )

    for run in report.runs:
        prompt_row = by_hash.get(run.prompt_id)
        engine_row = engine_rows.get(run.conditions.slot)
        if prompt_row is None or engine_row is None:
            # 저장할 자리가 없는 실행을 조용히 버리면 실행 수가 맞지 않는다. 여기까지
            # 오면 표를 잘못 만든 것이므로 감춘다기보다 드러나는 편이 낫다.
            raise ValueError(
                f"실행 결과를 저장할 대상을 찾지 못했습니다: prompt={run.prompt_id} "
                f"engine={run.conditions.engine}"
            )

        answer = AIAnswer(
            organization_id=principal.organization_id,
            observation_run_id=run_row.id,
            prompt_id=prompt_row.id,
            ai_engine_id=engine_row.id,
            repetition_index=attempts.get(run.run_id, 0),
            model_version=run.conditions.model_version,
            search_mode=str(run.conditions.search_mode),
            account_state=str(run.conditions.account_state),
            locale=run.conditions.locale,
            executed_at=run.executed_at,
            is_valid_execution=run.is_valid_execution,
            raw_answer_storage_key=run.raw_answer_ref,
            # 답변이 없는 실행에도 해시 칸은 비울 수 없다. 빈 문자열은 "원문 없음" 이고,
            # 그 옆의 `error_code` 가 왜 없는지를 말한다.
            raw_answer_hash=run.raw_answer_hash or "",
            error_code=run.error_code,
            citation_support=run.citation_support,
            latency_ms=run.latency_ms,
            cost_usd=run.cost_usd,
            cost_krw=None,
            # 값을 못 낸 이유와 실제 토큰 수. 가격표가 비어 있어도 사용량은 남는다.
            cost_basis=run.cost_basis,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
        )
        session.add(answer)
        session.flush()

        for position, url in enumerate(run.citations, start=1):
            domain = _domain_of(url)
            session.add(
                Citation(
                    organization_id=principal.organization_id,
                    ai_answer_id=answer.id,
                    url=url,
                    domain=domain,
                    position=position,
                    is_own_domain=any(
                        domain == own or domain.endswith(f".{own}") for own in brand.domains
                    ),
                )
            )

        # 확정된 언급과 **보류된 언급을 모두** 남긴다. 보류를 안 남기면 사람이 볼 자리가
        # 사라지고, 그 실행은 화면에서 "언급 없음" 과 구별되지 않는다.
        #
        # `match_confidence` 는 판별기가 낸 값을 그대로 적는다. 예전에는 여기에 1.0 이
        # 박혀 있었다 — 그 칸은 "얼마나 확신하는가" 를 묻는 칸인데, 무엇이 들어오든
        # 만점을 적고 있었다(0-A).
        # **경쟁사도 같은 표에 같은 모양으로** 남긴다. 우리 것만 남기면 나중에 점유율을
        # 낼 때 경쟁사 숫자를 사람이 손으로 넣게 되고(#23), 손으로 넣은 값은 잰 값처럼
        # 보이지만 아니다. 탐지는 이미 한 번의 호출로 양쪽을 함께 봤다.
        for sighting in run.sightings:
            if not (sighting.mentioned or sighting.needs_review):
                continue  # 이름이 아예 안 나온 브랜드는 남길 것이 없다.
            session.add(
                EntityMention(
                    organization_id=principal.organization_id,
                    ai_answer_id=answer.id,
                    entity_key=sighting.entity_key,
                    is_own_brand=sighting.is_own_brand,
                    competitor_id=(
                        uuid.UUID(sighting.competitor_id) if sighting.competitor_id else None
                    ),
                    raw_occurrence_count=max(sighting.raw_occurrence_count, 1),
                    first_position=sighting.first_position,
                    match_confidence=(
                        sighting.confidence if sighting.confidence is not None else 0.0
                    ),
                    needs_human_disambiguation=sighting.needs_review,
                    review_state=(
                        ReviewState.PENDING_REVIEW.value
                        if sighting.needs_review
                        else ReviewState.NOT_REVIEWED.value
                    ),
                )
            )

        # 보류된 언급은 **위험 판정으로도** 남긴다. 답변과 같은 트랜잭션에 담는 것이
        # 중요하다 — 나중에 따로 훑는 방식이면 그 훑기를 돌리지 않은 실행이 조용히
        # 검수 큐를 비껴간다. `claim_assessments` 에 쓰는 첫 코드다(#24).
        if run.mention_pending_review and run.mention_first_position is not None:
            session.add(
                new_assessment_row(
                    open_review(
                        assessment_from_held_mention(
                            answer_id=answer.id,
                            answer_ref=run.raw_answer_ref or "",
                            answer_hash=run.raw_answer_hash or "",
                            span_start=run.mention_first_position,
                            quoted_text=run.mention_quote,
                            reasons_ko=run.mention_evidence_ko,
                            decided_at=run.executed_at,
                        )
                    ),
                    organization_id=principal.organization_id,
                    answer_id=answer.id,
                )
            )

    session.flush()
    return run_row


def _prompt_hash_of(row: PromptRow) -> str:
    """저장된 행에서 엔진이 쓰는 질문 식별자를 다시 계산한다."""
    return Prompt(
        text=row.text,
        intent=Intent(row.intent),
        funnel=Funnel(row.funnel),
        subject=Subject(row.subject_type),
        business_importance=row.business_importance,
        locale=row.locale,
        persona=row.persona,
    ).prompt_id


__all__ = [
    "BrandIdentityMissingError",
    "EngineChoice",
    "answer_facts",
    "answer_store",
    "brand_profile_for",
    "brand_target_for",
    "competitor_profiles_for",
    "execute_observation",
]


def answer_facts(
    session: Session, principal: Principal, run_id: uuid.UUID
) -> tuple[AnswerFact, ...]:
    """저장된 답변들을 지표 계산이 읽는 형태로.

    `citation_support` 를 그대로 넘긴다. 이 값이 인용률의 분모를 정한다 — 출처를 밝히지
    않은 응답을 분모에 넣으면 인용률이 낮게 나오고, 그 낮은 값은 사이트 탓처럼 읽힌다.
    """
    statement = (
        tenant_select(AIAnswer, principal)
        .where(AIAnswer.observation_run_id == run_id)
        .order_by(AIAnswer.executed_at, AIAnswer.id)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    answers = list(session.scalars(statement))

    answer_ids = [answer.id for answer in answers]
    if not answer_ids:
        return ()

    # **우리 도메인 인용만** 센다. 경쟁사를 인용한 응답은 우리가 인용된 것이 아니다.
    # 여기서 모든 인용을 세면 인용률이 부풀고, 부푼 값은 아무도 의심하지 않는다.
    cited_ids = set(
        session.scalars(
            select(Citation.ai_answer_id)
            .where(Citation.ai_answer_id.in_(answer_ids))
            .where(Citation.is_own_domain.is_(True))
        )
    )
    # 같은 이유로 자사 언급만 센다. 그리고 **확정된 것만** 센다 — 이름이 같은 다른
    # 업체인지 갈리지 않은 건은 언급이 아니라 질문이다.
    mentioned_ids = set(
        session.scalars(
            select(EntityMention.ai_answer_id)
            .where(EntityMention.ai_answer_id.in_(answer_ids))
            .where(EntityMention.is_own_brand.is_(True))
            .where(EntityMention.needs_human_disambiguation.is_(False))
        )
    )
    # 보류된 건은 따로 센다. 이것을 안 넘기면 노출률이 조용히 내려가고, 왜 내려갔는지
    # 화면에서 알 방법이 없다 — "안 나왔다" 와 "누구인지 모르겠다" 가 같은 모양이 된다.
    pending_ids = set(
        session.scalars(
            select(EntityMention.ai_answer_id)
            .where(EntityMention.ai_answer_id.in_(answer_ids))
            .where(EntityMention.is_own_brand.is_(True))
            .where(EntityMention.needs_human_disambiguation.is_(True))
        )
    )

    # 출처 다양성은 **우리 것이 아닌 인용도** 세야 한다. 엔진이 몇 곳을 인용하는지가
    # 인용률을 읽는 방법을 바꾸기 때문이다 — 두 곳만 인용하는 엔진에서의 20% 와 마흔
    # 곳을 인용하는 엔진에서의 20% 는 같은 뜻이 아니다.
    domains_by_answer: dict[uuid.UUID, list[str]] = {}
    for answer_id, domain in session.execute(
        select(Citation.ai_answer_id, Citation.domain).where(
            Citation.ai_answer_id.in_(answer_ids)
        )
    ):
        if domain:
            domains_by_answer.setdefault(answer_id, []).append(domain)

    # 안정성은 엔진마다, 질문 의도는 프롬프트에서. 둘 다 조인 한 번으로 가져온다 —
    # 답변마다 따로 부르면 답변 수만큼 왕복이 늘어난다.
    #
    # `dict(...)` 로 줄이지 않는다. SQLAlchemy 는 2-튜플이 아니라 `Row` 를 돌려주고,
    # `dict()` 는 그것을 받아 주지 않는다 — 시험에서 실제로 터졌다.
    engines: dict[uuid.UUID, str] = {  # noqa: C416
        answer_id: provider
        for answer_id, provider in session.execute(
            select(AIAnswer.id, AIEngine.provider)
            .join(AIEngine, AIEngine.id == AIAnswer.ai_engine_id)
            .where(AIAnswer.id.in_(answer_ids))
        )
    }
    intents: dict[uuid.UUID, str] = {  # noqa: C416
        prompt_id: intent
        for prompt_id, intent in session.execute(
            select(PromptRow.id, PromptRow.intent).where(
                PromptRow.id.in_({answer.prompt_id for answer in answers})
            )
        )
    }

    return tuple(
        AnswerFact(
            prompt_id=str(answer.prompt_id),
            is_valid=answer.is_valid_execution,
            mentioned=answer.id in mentioned_ids,
            mention_pending_review=answer.id in pending_ids,
            cited=answer.id in cited_ids,
            citation_support=answer.citation_support,
            engine=engines.get(answer.id, ""),
            # 답변 행에 이미 저장돼 있는데 지표로 넘기지 않고 있었다. 없으면 안정성이
            # 검색 켬·끔을 한 묶음으로 세고, 두 조건의 차이가 엔진의 불안정으로 읽힌다.
            search_mode=answer.search_mode or "",
            intent=intents.get(answer.prompt_id, ""),
            cited_domains=tuple(domains_by_answer.get(answer.id, ())),
            # 반복이 **언제** 일어났는지가 신뢰구간의 전제다. 이 값을 흘리면 같은 순간에
            # 몰아 던진 반복이 독립 표본처럼 계산된다.
            executed_at=answer.executed_at,
        )
        for answer in answers
    )
