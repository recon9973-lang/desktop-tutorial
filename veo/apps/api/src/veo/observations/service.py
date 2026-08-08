"""관측 자료 접근 — 프롬프트 집합과 엔진 상태.

DB 의 `PromptSet`/`Prompt` 행과, 엔진이 읽는
:class:`veo.observations.prompts.PromptSet` 값 객체를 서로 옮긴다. 둘을 나눠 둔 이유는
엔진이 DB 를 모른 채로 시험 가능해야 하기 때문이고, 그 덕분에 관측 엔진 전체가 지금까지
DB 없이 검사되어 왔다.

**균형 검사는 저장 전에 한다.** 브랜드에 불리한 질문을 빼고 만든 집합으로 재면 노출률이
실제보다 높게 나오고, 그것은 고객에게 유리한 방향의 거짓이라 더 오래 살아남는다. 저장한
뒤에 경고만 띄우면 이미 그 집합으로 잰 결과가 남는다.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.core.settings import get_provider_credentials
from veo.db.models.observation import AIAnswer, AIEngine
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import Prompt as PromptRow
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.observations.estimate import TokenBaseline, median_baseline
from veo.observations.pricing import DatedPriceTable, load_price_table
from veo.observations.prompts import (
    Exclusion,
    Funnel,
    Intent,
    Prompt,
    PromptSet,
    PromptSetImbalanceError,
    Subject,
)
from veo.observations.providers.registry import ProviderRegistry, build_registry
from veo.organizations.errors import DuplicateResourceError

TARGET_TYPE = "prompt_set"

DUPLICATE_KO = "이 프로젝트에는 이미 같은 이름·판의 프롬프트 집합이 있습니다."

ENGINE_NOTE_KO = (
    "쓸 수 없는 엔진도 이유와 함께 그대로 보여 줍니다. 목록에서 빼면 '여기 있는 게 전부' 로 "
    "읽히고, 자격증명만 넣으면 잴 수 있었던 것을 모른 채 지나가게 됩니다."
)

#: 검색을 끌 수 없는 엔진 옆에 붙는 문장. 엔진 자체는 쓸 수 있으므로 목록에서 빼지 않는다.
SEARCH_OFF_UNAVAILABLE_KO = (
    "이 엔진은 검색을 끌 수 없습니다. 물을 때마다 검색해서 답하므로 '검색 끔' 으로는 "
    "잴 수 없고, 켬 모드로만 측정합니다."
)


class UnknownPromptFieldError(ValueError):
    """분류 값이 VEO 가 아는 값이 아니다. 조용히 기본값으로 떨어뜨리지 않는다."""


# --------------------------------------------------------------------------- #
# 엔진
# --------------------------------------------------------------------------- #


def engine_registry() -> ProviderRegistry:
    """설정에 들어 있는 자격증명과 **날짜가 붙은 가격표**로 조립한 등록소.

    가격표는 `packages/model-prices/` 에 있는데 등록소에 연결되어 있지 않아서, 모든
    호출이 `NO_PRICE_CONFIGURED` 로 기록되고 있었다. 그것은 "공짜" 가 아니라 "모른다"
    이지만, 예산 상한을 건 실행이 금액을 모른 채 돌 수는 없으므로 실질적으로 예산 기능이
    닫혀 있었다.

    **표를 못 읽는 것과 표가 오래된 것을 구분한다.**

    * 파일이 없으면 가격표 없이 조립한다. 비용은 `NO_PRICE_CONFIGURED` 로 남는다 —
      엔진 목록 조회 같은 일이 가격표 때문에 실패하면 안 된다.
    * 오래된 표는 **그대로 넘긴다.** `DatedPriceTable.cost` 가 스스로 `PRICE_TABLE_STALE`
      을 돌려주고, 그것이 정직한 답이다. 여기서 걸러 버리면 "가격표가 오래됐다" 가
      "가격표가 없다" 로 바뀌어, 무엇을 고쳐야 하는지 알 수 없게 된다.

    표 자체는 값이 비어 있을 수 있다. 각 제공자의 공식 가격 페이지에서 사람이 확인해
    채우도록 되어 있고, 비어 있으면 비용은 계산되지 않는다 — 지어낸 가격을 금액으로
    제시하지 않기 위해서다.
    """
    return build_registry(
        credentials=get_provider_credentials(), price_table=price_table_for_estimates()
    )


def price_table_for_estimates() -> DatedPriceTable | None:
    """날짜가 붙은 가격표, 또는 못 읽었다는 뜻의 ``None``.

    **오래된 표는 그대로 넘긴다.** `DatedPriceTable.cost` 가 스스로 `PRICE_TABLE_STALE`
    을 돌려주고 그것이 정직한 답이다. 여기서 걸러 버리면 "가격표가 오래됐다" 가
    "가격표가 없다" 로 바뀌어, 무엇을 고쳐야 하는지 알 수 없게 된다.
    """
    try:
        return load_price_table()
    except (FileNotFoundError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# 값 객체 ↔ 행
# --------------------------------------------------------------------------- #


def _classified(
    value: str, kind: type[Intent] | type[Funnel] | type[Subject], field: str
) -> object:
    try:
        return kind(value)
    except ValueError:
        allowed = ", ".join(sorted(member.value for member in kind))
        raise UnknownPromptFieldError(
            f"{field} 값 '{value}' 을(를) 알지 못합니다. 가능한 값: {allowed}"
        ) from None


def build_prompt_set(
    *,
    name: str,
    prompts: list[dict[str, object]],
    exclusions: list[dict[str, str]],
) -> PromptSet:
    """요청 본문을 엔진이 읽는 집합으로 옮기고, 균형을 검사한다.

    :class:`PromptSetImbalanceError` 는 그대로 올린다 — 라우터가 그 이유를 한국어 그대로
    응답에 옮긴다. "집합이 부적합합니다" 로 뭉개면 무엇을 고쳐야 하는지 알 수 없다.
    """
    built = [
        Prompt(
            text=str(item["text"]),
            intent=_classified(str(item["intent"]), Intent, "intent"),  # type: ignore[arg-type]
            funnel=_classified(str(item["funnel"]), Funnel, "funnel"),  # type: ignore[arg-type]
            subject=_classified(str(item["subject"]), Subject, "subject"),  # type: ignore[arg-type]
            business_importance=float(item.get("business_importance", 0.5)),  # type: ignore[arg-type]
            locale=str(item.get("locale", "ko-KR")),
            persona=item.get("persona"),  # type: ignore[arg-type]
        )
        for item in prompts
    ]
    # 뺀 질문에는 분류가 없다 — 분류까지 받아 두면 "빼는 데도 분류가 필요하다" 가 되어
    # 기록을 안 남기는 쪽이 편해진다. 식별자는 본문에서 뽑는다.
    dropped = [
        Exclusion(
            prompt_id=hashlib.sha256(item["text"].strip().encode("utf-8")).hexdigest()[:32],
            text=item["text"],
            reason_ko=item["reason_ko"],
        )
        for item in exclusions
    ]
    return PromptSet.build(name=name, prompts=built, exclusions=dropped)


def prompt_set_of(row: PromptSetRow, prompts: list[PromptRow]) -> PromptSet:
    """저장된 행을 엔진이 읽는 집합으로 되살린다.

    균형 검사를 다시 돌리지 않는다. 저장될 때 통과한 집합이고, 규칙이 나중에 엄격해졌다고
    이미 발행된 집합이 소급해서 거부되면 그 집합으로 잰 과거 결과를 열 수 없게 된다.
    """
    built = tuple(
        sorted(
            (
                Prompt(
                    text=prompt.text,
                    intent=Intent(prompt.intent),
                    funnel=Funnel(prompt.funnel),
                    subject=Subject(prompt.subject_type),
                    business_importance=prompt.business_importance,
                    locale=prompt.locale,
                    persona=prompt.persona,
                )
                for prompt in prompts
            ),
            key=lambda prompt: prompt.prompt_id,
        )
    )
    return PromptSet.rebuild(name=f"{row.name}@{row.version}", prompts=built)


# --------------------------------------------------------------------------- #
# 저장·조회
# --------------------------------------------------------------------------- #


def create_prompt_set(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID,
    name: str,
    version: str,
    locale: str,
    generation_rule_ko: str | None,
    prompt_set: PromptSet,
    prompts: list[dict[str, object]],
) -> PromptSetRow:
    """검사를 통과한 집합만 저장한다. 프로젝트는 먼저 조회해 권한을 확인한다."""
    # 여기서 늦게 가져온다. `veo.projects.service` 는 `veo.api` 를 거쳐 라우터 전체를
    # 끌어오므로, 모듈 맨 위에서 가져오면 이 모듈을 먼저 import 하는 쪽에서 순환이 된다.
    # `seo/router.py` 의 `site_exists` 도 같은 이유로 함수 안에 있다.
    from veo.projects.service import require_project

    require_project(session, principal, project_id)

    row = PromptSetRow(
        organization_id=principal.organization_id,
        project_id=project_id,
        name=name,
        version=version,
        locale=locale,
        generation_rule_ko=generation_rule_ko,
        is_locked=False,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateResourceError(DUPLICATE_KO) from exc

    by_text = {str(item["text"]): item for item in prompts}
    for prompt in prompt_set.prompts:
        source = by_text.get(prompt.text, {})
        session.add(
            PromptRow(
                organization_id=principal.organization_id,
                prompt_set_id=row.id,
                text=prompt.text,
                intent=str(prompt.intent),
                funnel=str(prompt.funnel),
                persona=prompt.persona,
                locale=prompt.locale,
                subject_type=str(prompt.subject),
                business_importance=prompt.business_importance,
                expected_demand=source.get("expected_demand"),
                expected_demand_is_estimate=True,
            )
        )
    session.flush()
    return row


#: 수동 측정용 즉석 집합에 붙는 이름. 목록에서 정기 집합과 눈으로 갈리게 한다.
MANUAL_SET_NAME = "수동 측정"


def create_manual_prompt_set(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID,
    questions: Sequence[str],
    locale: str = "ko-KR",
) -> tuple[PromptSetRow, PromptSet]:
    """관리자가 그 자리에서 고른 검색어로 즉석 집합을 만든다.

    **균형 검사를 하지 않는다.** 이 집합으로 만든 실행은 `kind=MANUAL` 이 되고,
    `runs.aggregate_rate` 가 정기 측정과 섞이는 것을 거부한다 — 관문은 저기 있다
    (`prompts.PromptSet.ad_hoc` 의 설명).

    분류(의도·단계·대상)는 `UNCLASSIFIED` 로 둔다. 관리자에게 고르게 하는 것은 군더더기이고,
    서버가 대신 고르면 **분석가가 판단한 것처럼 저장된다.** 모르는 것은 모른다고 적는다.
    그 값이 들어간 집합은 `PromptSet.build` 가 거부하므로 비교용으로 새어 나가지 않는다.
    """
    from veo.projects.service import require_project

    require_project(session, principal, project_id)

    cleaned = [text.strip() for text in questions if text.strip()]
    if not cleaned:
        raise PromptSetImbalanceError("검색어가 하나도 없습니다. 잴 것이 없습니다")

    built = PromptSet.ad_hoc(
        name=MANUAL_SET_NAME,
        prompts=[
            Prompt(
                text=text,
                intent=Intent.UNCLASSIFIED,
                funnel=Funnel.UNCLASSIFIED,
                subject=Subject.UNCLASSIFIED,
                locale=locale,
            )
            for text in cleaned
        ],
    )

    # 판 번호는 만든 시각이다. 같은 검색어를 다른 날 다시 재는 것은 다른 측정이고,
    # 그 둘이 같은 행을 덮어쓰면 앞의 결과가 사라진다.
    version = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]

    row = PromptSetRow(
        organization_id=principal.organization_id,
        project_id=project_id,
        name=MANUAL_SET_NAME,
        version=version,
        locale=locale,
        generation_rule_ko=(
            "관리자가 화면에서 직접 입력한 검색어입니다. 균형 검사(ADR 0015)를 거치지 "
            "않았으므로 비교와 추이에 쓸 수 없습니다."
        ),
        is_locked=True,
        kind="MANUAL",
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:  # pragma: no cover - 판 번호에 난수가 붙어 사실상 안 걸린다
        session.rollback()
        raise DuplicateResourceError(DUPLICATE_KO) from exc

    for prompt in built.prompts:
        session.add(
            PromptRow(
                organization_id=principal.organization_id,
                prompt_set_id=row.id,
                text=prompt.text,
                intent=str(prompt.intent),
                funnel=str(prompt.funnel),
                persona=prompt.persona,
                locale=prompt.locale,
                subject_type=str(prompt.subject),
                business_importance=prompt.business_importance,
                expected_demand=None,
                expected_demand_is_estimate=True,
            )
        )
    session.flush()
    return row, built


def token_baselines(
    session: Session,
    principal: Principal,
    *,
    max_samples_per_slot: int = 200,
) -> dict[str, TokenBaseline]:
    """칸(엔진·모델·검색모드)마다 이미 잰 토큰의 중앙값.

    예상 비용은 이것 없이는 나오지 않는다. **없으면 없는 대로 비워 둔다** — 없는 칸을
    다른 칸의 값으로 메우면 그 순간 예상치가 추측이 되고, 추측은 화면에서 실측과 구별
    되지 않는다.

    조회는 조직 안으로 갇힌다(`tenant_select`). 다른 조직이 무엇을 얼마나 재는지가
    이 값으로 새어 나가면 안 된다.
    """
    statement = (
        tenant_select(AIAnswer, principal)
        .join(AIEngine, AIEngine.id == AIAnswer.ai_engine_id)
        .where(
            AIAnswer.is_valid_execution.is_(True),
            AIAnswer.input_tokens.is_not(None),
            AIAnswer.output_tokens.is_not(None),
        )
        .with_only_columns(
            AIEngine.provider,
            AIAnswer.model_version,
            AIAnswer.search_mode,
            AIAnswer.input_tokens,
            AIAnswer.output_tokens,
        )
        .order_by(AIAnswer.executed_at.desc())
    )
    assert_tenant_scoped(statement, principal.organization_id)

    collected: dict[str, list[tuple[int | None, int | None]]] = {}
    for provider, model, search_mode, input_tokens, output_tokens in session.execute(statement):
        slot = f"{str(provider).upper()}:{model}:{search_mode}"
        samples = collected.setdefault(slot, [])
        # 오래된 것부터 버린다 — 모델이 바뀌면 답변 길이도 바뀐다.
        if len(samples) < max_samples_per_slot:
            samples.append((input_tokens, output_tokens))

    baselines: dict[str, TokenBaseline] = {}
    for slot, samples in collected.items():
        baseline = median_baseline(samples)
        if baseline is not None:
            baselines[slot] = baseline
    return baselines


def get_prompt_set(
    session: Session, principal: Principal, prompt_set_id: uuid.UUID
) -> PromptSetRow | None:
    statement = tenant_select(PromptSetRow, principal).where(PromptSetRow.id == prompt_set_id)
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).one_or_none()


def prompts_of(
    session: Session, principal: Principal, prompt_set_id: uuid.UUID
) -> list[PromptRow]:
    statement = (
        tenant_select(PromptRow, principal)
        .where(PromptRow.prompt_set_id == prompt_set_id)
        .order_by(PromptRow.created_at, PromptRow.id)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return list(session.scalars(statement))


def list_prompt_sets(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID | None = None,
) -> tuple[list[PromptSetRow], int]:
    from veo.projects.service import require_project

    statement = tenant_select(PromptSetRow, principal)
    if project_id is not None:
        require_project(session, principal, project_id)
        statement = statement.where(PromptSetRow.project_id == project_id)
    assert_tenant_scoped(statement, principal.organization_id)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(session.scalars(statement.order_by(PromptSetRow.created_at, PromptSetRow.id)))
    return rows, total


__all__ = [
    "DUPLICATE_KO",
    "ENGINE_NOTE_KO",
    "SEARCH_OFF_UNAVAILABLE_KO",
    "TARGET_TYPE",
    "PromptSetImbalanceError",
    "UnknownPromptFieldError",
    "build_prompt_set",
    "create_prompt_set",
    "engine_registry",
    "get_observation_run",
    "get_prompt_set",
    "list_observation_runs",
    "list_prompt_sets",
    "prompt_set_of",
    "prompts_of",
]


def get_observation_run(
    session: Session, principal: Principal, run_id: uuid.UUID
) -> ObservationRunRow | None:
    statement = tenant_select(ObservationRunRow, principal).where(ObservationRunRow.id == run_id)
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).one_or_none()


def list_observation_runs(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID | None = None,
    kind: str | None = None,
    limit: int = 50,
) -> tuple[list[ObservationRunRow], int]:
    """최신순. 부분 실행도 그대로 들어 있다 — 목록에서 빼면 그 실행이 없던 일이 된다.

    `kind` 도 같은 이유로 **기본이 '거르지 않음'** 이다. 수동 측정을 기본으로 감추면
    사장님이 방금 돌린 것이 목록에 없다.
    """
    statement = tenant_select(ObservationRunRow, principal)
    if project_id is not None:
        statement = statement.where(ObservationRunRow.project_id == project_id)
    if kind is not None:
        statement = statement.where(ObservationRunRow.kind == kind)
    assert_tenant_scoped(statement, principal.organization_id)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(
        session.scalars(
            statement.order_by(ObservationRunRow.created_at.desc(), ObservationRunRow.id).limit(
                limit
            )
        )
    )
    return rows, total
