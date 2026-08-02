"""What a stranger may send, and what a stranger may see.

The response models here are the privacy boundary of the whole product. A public result
carries the score, the band, the coverage, the confidence, the methodology version and
the names of the top findings — enough for a clinic owner to recognise their own site's
problems and want the full report.

It carries **no evidence**. Not an excerpt, not a content hash, not a storage key, not a
page URL beyond the one the caller typed. The reasons are separate and both binding:

* Evidence excerpts are quotations of the fetched page, and a shared result token is a
  URL that travels. Anything in the payload is a permanent copy for whoever holds it.
* Collector-authored strings — ``IssueDraft.summary_ko`` and friends — interpolate URLs
  and observed values. They are the right thing to show a paying customer inside their
  own console, so the public finding is built from the **specification's** static
  wording: check id, Korean title, severity, category, who fixes it.

2026-08-02 제품 결정으로 경계가 한 뼘 옮겨졌다: 검사 행(PublicCheckRow)에는 수집기의
**진단 문장(detail_ko)·조치 문장(fix_ko)·조치 코드**를 싣는다. 공개 진단은 호출자가
직접 입력한 한 페이지만 재므로, 이 문장들이 언급하는 URL 은 호출자 자신의 것이다.
여전히 싣지 않는 것: 페이지 본문 발췌(evidence excerpt), 콘텐츠 해시, 저장 키.
공유 토큰은 여행하는 URL 이고, 본문 인용은 실리는 순간 영구 사본이 된다.

Every model forbids unknown fields. On the request side that is what makes personal-data
minimisation enforceable rather than aspirational: a field nobody designed cannot be
accepted by accident.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_STRICT = ConfigDict(extra="forbid")

#: How many findings a free result shows. The rest are counted, not listed — hiding the
#: count would be a sales trick, and listing everything would be the paid report.
MAX_PUBLIC_FINDINGS = 5

RANK_PREDICTION_NOTICE_KO = (
    "이 점수는 검색 순위 예측이 아니라, 검색엔진과 AI 답변 엔진이 사이트를 발견하고 해석할 수 "
    "있는 상태인지에 대한 값입니다."
)

PUBLIC_SCOPE_NOTICE_KO = (
    "무료 진단은 페이지 수와 외부 연동을 제한한 축소 범위로 실행됩니다. 채점 방식과 명세는 "
    "유료 진단과 동일하며, 측정하지 못한 항목은 감점 대신 측정 범위(coverage)에 반영됩니다."
)

TargetUrl = Annotated[str, Field(min_length=8, max_length=2048)]
Keyword = Annotated[str, Field(min_length=1, max_length=100)]


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #


class PublicScanRequest(BaseModel):
    """One or more URLs to diagnose. The ceiling is enforced by the service, not here,
    so the refusal can name the configured maximum in Korean rather than emit a
    validation error that says ``too_long``."""

    model_config = _STRICT

    urls: list[TargetUrl] = Field(
        default_factory=list,
        description="진단할 주소입니다. 무료 진단은 설정된 최대 개수까지만 허용합니다.",
    )


class PublicKeywordLookupRequest(BaseModel):
    model_config = _STRICT

    keywords: list[Keyword] = Field(
        default_factory=list, description="조회할 키워드입니다."
    )


class PublicLeadRequest(BaseModel):
    """A callback request, and nothing beyond what a callback needs.

    Name plus one contact channel is the whole record. There is no birth date, no
    resident registration number, no marketing-consent checkbox — see
    ``leads.py`` for why consent is a contract request rather than a guess.
    """

    model_config = _STRICT

    name: Annotated[str, Field(min_length=1, max_length=40)] = Field(
        description="연락 시 부를 이름입니다."
    )
    phone: Annotated[str, Field(min_length=8, max_length=20)] | None = Field(
        default=None, description="회신받을 전화번호입니다. 이메일과 둘 중 하나는 필요합니다."
    )
    email: Annotated[str, Field(min_length=5, max_length=120)] | None = Field(
        default=None, description="회신받을 이메일입니다. 전화번호와 둘 중 하나는 필요합니다."
    )
    site_url: TargetUrl | None = Field(
        default=None, description="진단 대상 홈페이지 주소입니다. 선택 항목입니다."
    )

    @model_validator(mode="after")
    def _needs_one_channel(self) -> PublicLeadRequest:
        if not self.phone and not self.email:
            raise ValueError("전화번호 또는 이메일 중 하나는 입력해 주세요.")
        return self


# --------------------------------------------------------------------------- #
# Shared response pieces
# --------------------------------------------------------------------------- #


class PublicScoreBlock(BaseModel):
    """A score, and everything needed to know what it does and does not mean."""

    model_config = _STRICT

    spec_id: str
    spec_version: str
    spec_checksum: str
    status: Literal["SCORED", "NOT_APPLICABLE", "UNKNOWN"]
    score: float | None
    band_id: str | None
    band_label_ko: str | None
    coverage: float
    confidence: float
    is_rank_prediction: Literal[False] = False
    meaning_ko: str = RANK_PREDICTION_NOTICE_KO


class PublicFinding(BaseModel):
    """One problem worth naming, in the specification's own words.

    Deliberately carries no URL, no observed value and no evidence id. What it gives a
    reader is the name of the check, how serious it is, and who fixes it.
    """

    model_config = _STRICT

    check_id: str
    title_ko: str
    category_id: str
    category_name_ko: str
    severity: str
    remediation_owner: str
    status: Literal["FAIL", "WARNING"]


class PublicStage(BaseModel):
    """검색 여정 한 단계의 점수. 관문(is_gate)은 가중 평균이 아니라 곱셈이다."""

    model_config = _STRICT

    category_id: str
    name_ko: str
    score: float | None
    weight: float
    is_gate: bool = False


class PublicCheckRow(BaseModel):
    """검사 하나의 판정 전체 — 무료 화면의 체크리스트 한 줄.

    ``gain_points`` 는 채점기가 실제 산식으로 계산한 "고치면 오르는 폭"이다. 화면이
    따로 어림하지 않는다. ``code_example`` 은 붙여넣을 수 있는 조치 코드 — 정답
    코드가 하나로 정해지는 검사에만 있고, 없으면 문장 설명(note_ko)만 나간다.
    """

    model_config = _STRICT

    check_id: str
    title_ko: str
    category_id: str
    category_name_ko: str
    severity: str
    remediation_owner: str
    status: Literal["PASS", "WARNING", "FAIL", "NOT_APPLICABLE", "UNKNOWN"]
    note_ko: str | None = None
    #: 수집기의 진단 문장 그대로 — 무엇이, 어디서, 어떻게 어긋났는가. 실패·주의에만.
    detail_ko: str | None = None
    #: 수집기의 조치 문장 그대로 — 무엇을 하면 되는가.
    fix_ko: str | None = None
    gain_points: float | None = None
    blocked_by_cap: bool = False
    #: 점수를 이루지 않는 영역(연동 필요·보안 헤더류)의 검사. 화면은 "점수 밖" 으로
    #: 갈라 그린다 — 섞으면 순위와 무관한 일을 하고 점수가 오르는 착시가 생긴다.
    outside_score: bool = False
    code_example: str | None = None


class PublicStatusCounts(BaseModel):
    """상태별 검사 수 — 필터 칩의 숫자. 화면이 세지 않고 서버가 센다."""

    model_config = _STRICT

    failed: int = 0
    warned: int = 0
    passed: int = 0
    unknown: int = 0
    not_applicable: int = 0


class PublicPreviews(BaseModel):
    """이 페이지가 검색결과·공유 카드에서 실제로 어떻게 보이는가.

    값이 ``None`` 이면 **그 태그가 없다**는 뜻이다. 화면은 그 부재 자체를 그린다 —
    "설명 없음" 이라고 쓰는 것이 아니라 없는 채로 깨져 보이는 미리보기가 설득한다.
    """

    model_config = _STRICT

    serp_title: str | None = None
    serp_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    has_og_image: bool = False


class PublicExposureBlock(BaseModel):
    """Whether anything blocks the page from being reached at all.

    Kept beside the readiness score and never merged into it: a page can be structurally
    excellent and completely invisible, and those are different jobs to fix.
    """

    model_config = _STRICT

    is_blocked: bool
    status_codes: list[str] = Field(default_factory=list)
    labels_ko: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Scan responses
# --------------------------------------------------------------------------- #


class PublicSeoScanPayload(BaseModel):
    model_config = _STRICT

    kind: Literal["SEO"] = "SEO"
    target_url: str
    scanned_url_count: int
    summary_ko: str
    scope_notice_ko: str = PUBLIC_SCOPE_NOTICE_KO
    score: PublicScoreBlock
    #: 검색에 들어갈 수 있는 비율. 화면의 "도달률x품질" 줄이 이 값으로 그려진다.
    reach: float = 1.0
    stages: list[PublicStage] = Field(default_factory=list)
    checks: list[PublicCheckRow] = Field(default_factory=list)
    counts: PublicStatusCounts = Field(default_factory=PublicStatusCounts)
    previews: PublicPreviews | None = None
    top_findings: list[PublicFinding] = Field(default_factory=list)
    total_finding_count: int = 0
    unmeasured_check_count: int = 0
    result_token: str
    result_expires_at: datetime


class PublicGeoScanPayload(BaseModel):
    model_config = _STRICT

    kind: Literal["GEO"] = "GEO"
    target_url: str
    scanned_url_count: int
    summary_ko: str
    scope_notice_ko: str = PUBLIC_SCOPE_NOTICE_KO
    readiness: PublicScoreBlock
    reach: float = 1.0
    stages: list[PublicStage] = Field(default_factory=list)
    checks: list[PublicCheckRow] = Field(default_factory=list)
    counts: PublicStatusCounts = Field(default_factory=PublicStatusCounts)
    exposure: PublicExposureBlock
    top_findings: list[PublicFinding] = Field(default_factory=list)
    total_finding_count: int = 0
    unmeasured_check_count: int = 0
    result_token: str
    result_expires_at: datetime


PublicResultPayload = PublicSeoScanPayload | PublicGeoScanPayload


# --------------------------------------------------------------------------- #
# Keyword responses
# --------------------------------------------------------------------------- #


class PublicKeywordEntry(BaseModel):
    """One keyword's figures, with each kind of absence kept apart.

    ``quality`` is what stops a suppressed value reading as zero. "Nobody searches for
    this" and "the provider would not say" are different answers and a free tool has no
    more licence to blur them than a paid one.
    """

    model_config = _STRICT

    keyword: str
    normalized_keyword: str
    monthly_total_searches: int | None = None
    monthly_total_quality: str
    monthly_pc_searches: int | None = None
    monthly_pc_quality: str
    monthly_mobile_searches: int | None = None
    monthly_mobile_quality: str
    competition_label: str | None = None


class PublicKeywordLookupPayload(BaseModel):
    model_config = _STRICT

    locale: str = "ko-KR"
    searchad_state: str
    keywords: list[PublicKeywordEntry] = Field(default_factory=list)
    notices_ko: list[str] = Field(default_factory=list)
    scope_notice_ko: str = (
        "무료 조회는 네이버 검색광고가 공개하는 월간 검색수만 보여 줍니다. 기회 점수와 추이 "
        "분석은 콘솔에서 제공합니다."
    )


# --------------------------------------------------------------------------- #
# Lead response
# --------------------------------------------------------------------------- #


class PublicLeadPayload(BaseModel):
    """Confirmation that says, in Korean, exactly what was written down."""

    model_config = _STRICT

    lead_id: str
    received_at: datetime
    stored_fields_ko: list[str]
    retention_note_ko: str
    consent_note_ko: str


__all__ = [
    "MAX_PUBLIC_FINDINGS",
    "PUBLIC_SCOPE_NOTICE_KO",
    "RANK_PREDICTION_NOTICE_KO",
    "PublicExposureBlock",
    "PublicFinding",
    "PublicGeoScanPayload",
    "PublicKeywordEntry",
    "PublicKeywordLookupPayload",
    "PublicKeywordLookupRequest",
    "PublicLeadPayload",
    "PublicLeadRequest",
    "PublicResultPayload",
    "PublicScanRequest",
    "PublicScoreBlock",
    "PublicSeoScanPayload",
]
