"""Request and response shapes for ``/seo``.

The scan endpoint takes a crawl that has already happened. This package deliberately
does not fetch: the SSRF guard, the redirect policy and the size budgets live in
``veo.common.security`` and belong to one crawler, not to eight collectors. So the
worker crawls once through :class:`~veo.common.security.fetcher.SafeFetcher` and posts
the material here, which also means the endpoint can be exercised end to end from a
fixture with no network at all.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")

ImportanceLiteral = Literal[
    "CONVERSION_OR_HOME",
    "CATEGORY_OR_HUB",
    "CONTENT_OR_PRODUCT",
    "TAG_OR_FILTER",
    "INTENTIONAL_NOINDEX",
]


class SiteScanRequest(BaseModel):
    """콘솔 진단 요청 — 주소만 주면 VEO 가 직접 가져와 채점한다.

    수집과 채점은 분리하지 않는다. 수집물을 본문으로 받는 계약(`/seo/scan`)이 한때
    있었지만, 요청자가 만든 provider 자료를 명세의 이름으로 채점하게 되므로 닫았다 —
    채점의 입력은 VEO 의 수집기가 SSRF 방어와 함께 직접 가져온 것뿐이다.
    """

    model_config = _FROZEN

    target_url: str = Field(min_length=1, description="진단할 사이트의 대표 주소입니다.")
    site_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "등록된 사이트에 결과를 남기려면 지정합니다. 비워 두면 채점은 동일하게 "
            "수행하지만 **아무것도 저장하지 않습니다** — 영업 단계의 간편 진단이 그 경우입니다."
        ),
    )
    urls: list[str] = Field(
        default_factory=list,
        description=(
            "반드시 함께 볼 페이지 주소입니다. 사이트가 링크로 잇지 않은 페이지를 "
            "일부러 진단할 때 씁니다. `discover` 가 켜져 있으면 여기 넣은 주소가 "
            "가장 먼저 수집되고, 발견한 주소는 그 뒤에 붙습니다."
        ),
    )
    discover: bool = Field(
        default=True,
        description=(
            "사이트맵과 내부 링크를 따라 VEO 가 스스로 페이지를 찾을지 여부입니다. "
            "끄면 대표 주소와 `urls` 에 넣은 주소만 봅니다. 한 장만 보면 내부 링크·"
            "중복 메타데이터·클릭 깊이처럼 사이트 전체를 봐야 판정되는 항목이 "
            "측정 불가로 남고, 그 배점은 분모에 그대로 남습니다."
        ),
    )
    max_urls: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description=(
            "이번 진단에서 가져올 최대 페이지 수입니다. 비워 두면 서버 기본값을 씁니다. "
            "대상 사이트에 보내는 요청 수를 그대로 정하는 값이므로 함부로 올리지 않습니다."
        ),
    )
    locale: str = "ko-KR"


class ImprovementSummary(BaseModel):
    """고치면 얼마나 오르는가 — 위에서부터 처리하면 점수가 가장 빨리 오른다.

    `gain_points` 는 채점기가 실제 산식으로 계산한 값이다. 화면이 따로 어림하지 않는다 —
    어림하면 고친 뒤의 실제 점수와 어긋나고, 그러면 우선순위 자체를 믿을 수 없게 된다.
    """

    model_config = _FROZEN

    check_id: str
    category_id: str
    title_ko: str
    #: 이 항목을 통과로 바꿨을 때 전체 점수가 오르는 폭.
    gain_points: float
    #: 상한에 걸려 지금은 고쳐도 점수가 오르지 않는 상태. 이때 `gain_points` 는 0이다.
    blocked_by_cap: bool
    severity: str
    remediation_owner: str


class ScanHistoryEntry(BaseModel):
    """이력 한 줄. 추이 그래프의 점 하나가 된다."""

    model_config = _FROZEN

    scan_run_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    urls_collected: int
    score: float | None
    band_id: str | None
    coverage: float
    confidence: float
    #: 그때 적용된 명세. 버전이 다른 두 점수를 나란히 비교하면 안 된다는 표시이기도 하다.
    spec_version: str
    spec_checksum: str
    #: 실행한 사람. 계정이 지워졌거나 예약 실행이면 비어 있다 — 기록 자체는 남는다.
    requested_by_name: str | None
    #: 이 점을 목록의 가장 최근 실행과 나란히 놓아도 되는가. 조건이 기록되지 않은 옛
    #: 실행은 `false` 다 — 어떻게 쟀는지 모르는 것과 같게 쟀다는 것은 다른 말이다.
    comparable_with_latest: bool = True
    #: 왜 나란히 놓을 수 없는지. 놓을 수 있으면 비어 있다.
    incomparable_reason_ko: str | None = None


class ScanHistoryPayload(BaseModel):
    model_config = _FROZEN

    site_id: uuid.UUID
    entries: list[ScanHistoryEntry]


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #


class CheckCatalogueEntry(BaseModel):
    model_config = _FROZEN

    id: str
    title_ko: str
    title_en: str
    category_id: str
    category_name_ko: str
    severity: str
    scope: str
    remediation_owner: str
    applicability_ko: str | None
    evidence_required: list[str]
    engine_scope: list[str]
    collector: str
    requires_provider: bool


class CheckCataloguePayload(BaseModel):
    model_config = _FROZEN

    spec_id: str
    spec_version: str
    spec_checksum: str
    checks: list[CheckCatalogueEntry]


class CategorySummary(BaseModel):
    model_config = _FROZEN

    category_id: str
    name_ko: str
    weight: float
    status: str
    score: float | None
    coverage: float
    confidence: float
    not_applicable_check_ids: list[str]
    unknown_check_ids: list[str]
    failing_check_ids: list[str]


class CapSummary(BaseModel):
    model_config = _FROZEN

    cap_id: str
    max_overall_score: float
    reason_ko: str
    release_condition_ko: str
    triggered_by: list[str]


class ScoreSummary(BaseModel):
    model_config = _FROZEN

    spec_id: str
    spec_version: str
    spec_checksum: str
    status: str
    score: float | None
    score_before_caps: float | None
    band_id: str | None
    coverage: float
    confidence: float
    #: 검색에 들어갈 수 있는 비율. 관문이 없는 명세에서는 1.0 이다.
    #:
    #: 화면이 이 값을 받아야 **0점의 이유를 읽을 수 있다.** 도달률 0.4 곱하기 품질 85 와
    #: 도달률 1.0 곱하기 품질 34 는 같은 34점이지만, 앞의 사이트가 고칠 것은 차단이고
    #: 뒤의 사이트가 고칠 것은 품질이다. 점수 하나로는 둘을 구분할 수 없다.
    reach: float = 1.0
    #: 확인하지 못한 관문 검사. 조용히 넘어가면 "확인했고 문제없음" 과 구분되지 않는다.
    gate_unverified: list[str] = []
    is_rank_prediction: Literal[False]
    categories: list[CategorySummary]
    applied_caps: list[CapSummary]
    calculation_trace: dict[str, Any]


class OutcomeSummary(BaseModel):
    """한 항목의 판정과, **왜 그렇게 판정했는지**.

    식별자와 상태만 내보내면 화면은 `seo.onpage.heading_hierarchy` 라고 쓸 수밖에 없고,
    그 줄을 본 직원이 할 수 있는 일이 없다. 제목·영역·심각도는 발행 명세에서 가져오고,
    관측값은 수집기가 이미 담아 둔 것을 그대로 흘려보낸다.
    """

    model_config = _FROZEN

    check_id: str
    #: 명세가 정한 이름. 수집기가 정하게 두면 같은 항목의 이름이 수집기마다 달라진다.
    title_ko: str
    category_id: str
    category_name_ko: str
    severity: str
    remediation_owner: str
    #: 이 항목을 재려면 누가 움직여야 하는가 — SELF_SERVICE / CUSTOMER_GRANTED /
    #: PAID_PROVIDER. 뒤의 둘은 배점에서 빠지므로, 화면이 그 사실을 함께 알려야 한다.
    availability: str
    #: 왜 이 항목을 보는지. 명세의 근거 문장을 그대로 옮긴다.
    reference_ko: str | None
    status: str
    confidence: float | None
    confidence_level: str | None
    affected_weight: float
    evaluated_weight: float
    evidence_ids: list[str]
    note: str | None
    #: 수집기가 실제로 본 값. 페이지별 제목 길이, 어긋난 제목 단계, 막힌 크롤러 이름 —
    #: 화면의 "원인 상세" 가 여기서 나온다. 판정을 내리지 못했으면 ``None``.
    observed: Any = None


class UnknownCheckSummary(BaseModel):
    model_config = _FROZEN

    check_id: str
    category_id: str
    title_ko: str
    reason_ko: str


class IssueSummary(BaseModel):
    model_config = _FROZEN

    check_id: str
    title_ko: str
    summary_ko: str
    affected_urls: list[str]
    evidence_ids: list[str]
    remediation_ko: str
    remediation_owner: str
    business_impact_ko: str
    fix_example: str | None
    reverification_note_ko: str


class EvidenceSummary(BaseModel):
    model_config = _FROZEN

    evidence_id: str
    kind: str
    url: str | None
    collected_at: str
    content_hash: str
    excerpt: str


class ScanPayload(BaseModel):
    model_config = _FROZEN

    summary_ko: str
    score: ScoreSummary
    outcomes: list[OutcomeSummary]
    unknown_checks: list[UnknownCheckSummary]
    issues: list[IssueSummary]
    #: 조치 우선순위. 이득이 큰 것부터.
    improvements: list[ImprovementSummary] = Field(default_factory=list)
    evidence: list[EvidenceSummary]
    notes_ko: list[str]
    #: 같은 크롤로 함께 채점된 GEO 요약(사이트 저장 진단에서만). 합산 금지.
    geo: GeoCompanionSummary | None = None


class GeoCompanionSummary(BaseModel):
    """같은 크롤로 함께 채점된 GEO 의 요약 — 전환기가 읽는 최소한.

    ``scan_run_id`` 가 None 이면 동반 채점이 실패한 것이고 ``failure_note_ko`` 가
    그 사실을 말한다. 점수는 SEO 와 합치지 않는다 — 눈금이 다른 두 답이다.
    """

    model_config = _FROZEN

    scan_run_id: uuid.UUID | None = None
    score: float | None = None
    band_id: str | None = None
    spec_version: str | None = None
    failure_note_ko: str | None = None


class PageStageSummary(BaseModel):
    """검색 여정 한 단계의, 이 페이지에서의 점수."""

    model_config = _FROZEN

    category_id: str
    name_ko: str
    weight: float
    is_gate: bool
    score: float | None


class PageLossSummary(BaseModel):
    """이 페이지가 잃은 점수 한 건 — 고치면 그만큼 돌아온다."""

    model_config = _FROZEN

    check_id: str
    category_id: str
    status: str
    lost: float


class PageScoreSummary(BaseModel):
    """페이지 점수 전체 — 명세 1.9.0 부터, 산식 출처와 함께.

    항등식 ``quality == 100 - Σ(losses.lost)`` · ``score == reach x quality`` 가
    응답 안에서 성립한다 — 화면이 숫자를 검산할 수 있다.
    """

    model_config = _FROZEN

    spec_id: str
    spec_version: str
    status: str  # SCORED | UNKNOWN | NOT_APPLICABLE
    score: float | None
    reach: float
    quality: float | None
    stages: list[PageStageSummary] = Field(default_factory=list)
    losses: list[PageLossSummary] = Field(default_factory=list)
    gate_unverified: list[str] = Field(default_factory=list)
    unmeasured: list[str] = Field(default_factory=list)
    #: 표본 정책이 이 페이지를 재지 않은 검사 — 감점이 아니다. 화면은
    #: ``not_sampled_note_ko`` 를 그대로 단다.
    not_sampled: list[str] = Field(default_factory=list)
    not_applicable: list[str] = Field(default_factory=list)
    not_sampled_note_ko: str


class PageChecksSummary(BaseModel):
    """한 페이지에서 실제로 판정된 검사들, 그리고 (1.9.0+ 실행이면) 점수.

    ``score`` 가 ``None`` 인 것은 두 경우다: 1.9.0 이전 명세로 저장된 실행(그 판의
    규칙에 없던 산수를 하지 않는다, ADR 0012), 또는 이 페이지에 판정이 하나도 없는
    경우. 어느 쪽인지는 실행 단위 ``notes_ko`` 가 말한다.
    """

    model_config = _FROZEN

    url: str
    failed: list[str] = Field(default_factory=list)
    warned: list[str] = Field(default_factory=list)
    #: 목록이 아니라 수인 이유: 목록 화면에서 통과 항목명까지 실으면 페이지 200장에
    #: 검사 30개씩이 매 응답에 실린다. 전체 목록은 페이지 상세에서 준다.
    passed_count: int
    problem_count: int
    score: float | None = None
    score_status: str | None = None


class PageDetailPayload(BaseModel):
    """페이지 하나의 전체 판정 — 통과 목록과 점수 전체까지."""

    model_config = _FROZEN

    url: str
    failed: list[str] = Field(default_factory=list)
    warned: list[str] = Field(default_factory=list)
    passed: list[str] = Field(default_factory=list)
    #: 이 페이지에서 잰 적 없는 검사는 여기 나오지 않는다. "통과" 와 "안 쟀다" 를
    #: 섞으면 페이지가 실제보다 건강해 보인다.
    score: PageScoreSummary | None = None


class SiteCheckSummary(BaseModel):
    """사이트 전체 단위의 판정. 페이지에 귀속되지 않는다."""

    model_config = _FROZEN

    check_id: str
    status: str
    reason_ko: str | None = None


class ScanPagesPayload(BaseModel):
    """한 실행의 판정을 페이지 축으로 — 재크롤 없이 저장된 것에서.

    `site_checks` 는 반드시 `measured_at` 과 함께 그려야 한다. 날짜 없이 페이지
    화면에 섞으면 사이트 전체의 사실이 "이 페이지의 문제" 로 잘못 읽힌다.
    """

    model_config = _FROZEN

    scan_run_id: uuid.UUID
    measured_at: datetime | None
    pages: list[PageChecksSummary] = Field(default_factory=list)
    site_checks: list[SiteCheckSummary] = Field(default_factory=list)
    recorded_before_page_lists: bool = False
    notes_ko: list[str] = Field(default_factory=list)


__all__ = [
    "CapSummary",
    "CategorySummary",
    "CheckCatalogueEntry",
    "CheckCataloguePayload",
    "EvidenceSummary",
    "GeoCompanionSummary",
    "IssueSummary",
    "OutcomeSummary",
    "PageChecksSummary",
    "PageDetailPayload",
    "PageLossSummary",
    "PageScoreSummary",
    "PageStageSummary",
    "ScanPagesPayload",
    "ScanPayload",
    "ScoreSummary",
    "SiteCheckSummary",
    "UnknownCheckSummary",
]
