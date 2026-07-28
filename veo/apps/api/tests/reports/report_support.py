"""Hand-checkable material for the report tests.

Every number here is written out by hand so that an assertion elsewhere in the suite can
be verified by reading rather than by re-running the evaluator. The scores are *not*
computed: a report freezes what it is given, so a test that recomputed them would be
testing the evaluator instead of the snapshot.

Three states appear on purpose:

* ``SEO_READINESS`` — scored, with one ``해당 없음`` category and one ``측정 불가`` category.
* ``GEO_READINESS`` — scored under the same conditions, so a comparison is legal.
* the competitor — measured under a *different* methodology version, so the gap must
  come out as ``측정 불가`` rather than as a subtraction nobody may trust.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from veo.collect.contract import EvidenceRecord, IssueDraft
from veo.compare.conditions import MeasurementConditions
from veo.scoring.models import (
    AppliedCap,
    CategoryScore,
    CheckOutcome,
    CheckStatus,
    RaisedGate,
    ScoreResult,
    ScoringDomain,
)

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")


def _api_prefix() -> str:
    from veo.core.settings import get_settings

    return str(get_settings().api_prefix)


API_PREFIX = _api_prefix()
REPORTS = f"{API_PREFIX}/reports"


@dataclass(frozen=True)
class Tenant:
    """One organization with a project and three callers holding different roles."""

    organization_id: uuid.UUID
    project_id: uuid.UUID
    analyst: Any
    viewer: Any
    developer: Any


@dataclass
class PrincipalBox:
    """The caller of the next request. Swapped by the ``act_as`` fixture."""

    current: Any = None


# --------------------------------------------------------------------------- #
# The numbers, written out once.
# --------------------------------------------------------------------------- #

SEO_OVERALL = 72.5
SEO_OVERALL_BEFORE_CAPS = 84.0
SEO_COVERAGE = 0.8125
SEO_CONFIDENCE = 0.91
SEO_CRAWL_SCORE = 61.25
SEO_CONTENT_SCORE = 88.0

GEO_OVERALL = 55.0
GEO_COVERAGE = 0.75
GEO_CONFIDENCE = 0.6

COMPETITOR_SCORE = 91.0

SPEC_ID = "veo.test.readiness"
SPEC_VERSION = "1.4.0"
SPEC_CHECKSUM = "sha256:6f1c9d2b4a7e08135f2c9a0d4b6e8f1027384756a9b0c1d2e3f405162738495a"
COLLECTOR_VERSION = "veo-collector/2.3.1"

MEASURED_AT = datetime(2026, 7, 20, 3, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 7, 21, 9, 30, tzinfo=UTC)
WINDOW_START = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 20, 23, 59, tzinfo=UTC)

#: A string that exists nowhere else, so a leak of a raw excerpt is unmistakable.
EVIDENCE_SENTINEL = "RAWEVIDENCESENTINEL-8f31c2"

UNKNOWN_REASON = "Search Console 자격증명이 없어 색인 상태를 확인하지 못했습니다."
NOT_APPLICABLE_REASON = "이 사이트에는 다국어 페이지가 없어 해당 항목이 적용되지 않습니다."


def make_conditions(**overrides: Any) -> MeasurementConditions:
    base = MeasurementConditions(
        spec_id=SPEC_ID,
        spec_version=SPEC_VERSION,
        spec_checksum=SPEC_CHECKSUM,
        collector_version=COLLECTOR_VERSION,
        pages_examined=120,
        locale="ko-KR",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
        enabled_providers=("VEO_CRAWLER",),
        measured_at=MEASURED_AT,
    )
    return replace(base, **overrides) if overrides else base


def _outcome(check_id: str, status: CheckStatus, note: str | None = None) -> CheckOutcome:
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=0.9,
        evidence_ids=("http_response:aaaabbbbccccdddd",),
        note=note,
    )


def make_seo_score() -> ScoreResult:
    """Scored overall; one category ``해당 없음``, one ``측정 불가``."""
    return ScoreResult(
        spec_id=SPEC_ID,
        spec_version=SPEC_VERSION,
        spec_checksum=SPEC_CHECKSUM,
        domain=ScoringDomain.SEO_READINESS,
        status="SCORED",
        overall_score=SEO_OVERALL,
        overall_score_before_caps=SEO_OVERALL_BEFORE_CAPS,
        band_id="needs_work",
        coverage=SEO_COVERAGE,
        confidence=SEO_CONFIDENCE,
        effective_weight_total=70.0,
        categories=[
            CategoryScore(
                category_id="crawlability",
                name_ko="크롤 가능성",
                name_en="Crawlability",
                weight=40.0,
                status="SCORED",
                score=SEO_CRAWL_SCORE,
                budget=1.3,
                penalty_total=0.5,
                coverage=0.9,
                confidence=0.95,
                applicable_check_ids=["seo.crawl.robots", "seo.crawl.sitemap"],
                scored_check_ids=["seo.crawl.robots", "seo.crawl.sitemap"],
                not_applicable_check_ids=[],
                unknown_check_ids=[],
                failing_check_ids=["seo.crawl.robots"],
            ),
            CategoryScore(
                category_id="content",
                name_ko="콘텐츠 구조",
                name_en="Content structure",
                weight=30.0,
                status="SCORED",
                score=SEO_CONTENT_SCORE,
                budget=0.7,
                penalty_total=0.08,
                coverage=0.8,
                confidence=0.88,
                applicable_check_ids=["seo.content.title"],
                scored_check_ids=["seo.content.title"],
                not_applicable_check_ids=[],
                unknown_check_ids=[],
                failing_check_ids=[],
            ),
            CategoryScore(
                category_id="indexing",
                name_ko="색인 상태",
                name_en="Indexing",
                weight=20.0,
                status="UNKNOWN",
                score=None,
                budget=0.0,
                penalty_total=0.0,
                coverage=0.0,
                confidence=0.0,
                applicable_check_ids=["seo.index.coverage"],
                scored_check_ids=[],
                not_applicable_check_ids=[],
                unknown_check_ids=["seo.index.coverage"],
                failing_check_ids=[],
            ),
            CategoryScore(
                category_id="i18n",
                name_ko="다국어",
                name_en="Internationalisation",
                weight=10.0,
                status="NOT_APPLICABLE",
                score=None,
                budget=0.0,
                penalty_total=0.0,
                coverage=1.0,
                confidence=1.0,
                applicable_check_ids=[],
                scored_check_ids=[],
                not_applicable_check_ids=["seo.i18n.hreflang"],
                unknown_check_ids=[],
                failing_check_ids=[],
            ),
        ],
        applied_caps=[
            AppliedCap(
                cap_id="sitewide_noindex",
                max_overall_score=72.5,
                reason_ko="사이트 전체에 noindex가 걸려 있어 상한을 적용했습니다.",
                release_condition_ko="noindex 해제 후 재검증하면 상한이 풀립니다.",
                triggered_by=["seo.crawl.robots"],
            )
        ],
        gates=[
            RaisedGate(
                gate_id="exposure_blocked",
                status_code="EXPOSURE_BLOCKED",
                label_ko="노출 차단",
                label_en="Exposure blocked",
                description_ko="robots.txt가 전체 경로를 막고 있습니다.",
                triggered_by=["seo.crawl.robots"],
            )
        ],
        outcomes=[
            _outcome("seo.crawl.robots", CheckStatus.FAIL),
            _outcome("seo.crawl.sitemap", CheckStatus.PASS),
            _outcome("seo.content.title", CheckStatus.WARNING),
            _outcome("seo.index.coverage", CheckStatus.UNKNOWN, UNKNOWN_REASON),
            _outcome("seo.i18n.hreflang", CheckStatus.NOT_APPLICABLE, NOT_APPLICABLE_REASON),
        ],
        trace={"formula": "budget - penalty", "effective_weight_total": 70.0},
    )


def make_geo_score() -> ScoreResult:
    return ScoreResult(
        spec_id=SPEC_ID,
        spec_version=SPEC_VERSION,
        spec_checksum=SPEC_CHECKSUM,
        domain=ScoringDomain.GEO_READINESS,
        status="SCORED",
        overall_score=GEO_OVERALL,
        overall_score_before_caps=GEO_OVERALL,
        band_id="poor",
        coverage=GEO_COVERAGE,
        confidence=GEO_CONFIDENCE,
        effective_weight_total=100.0,
        categories=[
            CategoryScore(
                category_id="extractability",
                name_ko="답변 추출 가능성",
                name_en="Answer extractability",
                weight=100.0,
                status="SCORED",
                score=GEO_OVERALL,
                budget=1.0,
                penalty_total=0.45,
                coverage=GEO_COVERAGE,
                confidence=GEO_CONFIDENCE,
                applicable_check_ids=["geo.extract.answer"],
                scored_check_ids=["geo.extract.answer"],
                not_applicable_check_ids=[],
                unknown_check_ids=[],
                failing_check_ids=["geo.extract.answer"],
            )
        ],
        applied_caps=[],
        gates=[],
        outcomes=[_outcome("geo.extract.answer", CheckStatus.FAIL)],
        trace={"formula": "budget - penalty"},
    )


def make_issues() -> tuple[IssueDraft, ...]:
    return (
        IssueDraft(
            check_id="seo.crawl.robots",
            title_ko="robots.txt가 전체 경로를 차단합니다",
            summary_ko="robots.txt의 Disallow: / 때문에 어떤 페이지도 수집되지 않습니다.",
            affected_urls=("https://example.test/robots.txt", "https://example.test/"),
            evidence_ids=("robots_txt:1111222233334444",),
            remediation_ko="Disallow: / 를 제거하고 필요한 경로만 개별로 막으십시오.",
            remediation_owner="DEVELOPER",
            business_impact_ko="검색 유입이 발생할 수 없습니다.",
            fix_example="User-agent: *\nAllow: /\nDisallow: /admin/",
            reverification_note_ko="배포 후 robots.txt를 다시 수집해 검사를 재실행하십시오.",
        ),
        IssueDraft(
            check_id="seo.content.title",
            title_ko="title이 중복됩니다",
            summary_ko="서로 다른 12개 페이지가 같은 title을 사용합니다.",
            affected_urls=("https://example.test/a", "https://example.test/b"),
            evidence_ids=("dom_snippet:5555666677778888",),
            remediation_ko="페이지마다 고유한 title을 부여하십시오.",
            remediation_owner="MARKETER",
            business_impact_ko="검색 결과에서 페이지가 서로 구분되지 않습니다.",
            fix_example="<title>강남 임플란트 비용 안내 | 예시치과</title>",
            reverification_note_ko="수정한 페이지를 다시 수집해 title 중복 검사를 재실행하십시오.",
        ),
    )


def make_evidence() -> tuple[EvidenceRecord, ...]:
    return (
        EvidenceRecord(
            evidence_id="robots_txt:1111222233334444",
            kind="robots_txt",
            url="https://example.test/robots.txt",
            collected_at=MEASURED_AT,
            content_hash="1111222233334444" * 4,
            excerpt=f"User-agent: *\nDisallow: /  {EVIDENCE_SENTINEL}",
            storage_key="s3://veo-evidence/robots/1111",
            detail={"bytes": 42},
        ),
        EvidenceRecord(
            evidence_id="dom_snippet:5555666677778888",
            kind="dom_snippet",
            url="https://example.test/a",
            collected_at=MEASURED_AT,
            content_hash="5555666677778888" * 4,
            excerpt=f"<title>예시</title> {EVIDENCE_SENTINEL}",
            storage_key=None,
            detail={},
        ),
    )


def make_diagnosis(**overrides: Any) -> Any:
    """A two-domain diagnosis with keyword demand and one competitor."""
    from veo.reports.snapshot import (
        CompetitorObservation,
        DiagnosisInput,
        DomainDiagnosis,
        KeywordDemand,
        MeasuredValue,
    )

    seo = DomainDiagnosis(
        key="SEO_READINESS",
        name_ko="SEO 준비도",
        score=make_seo_score(),
        conditions=make_conditions(),
        summary_ko="기술 준비도 72.5점, 측정 범위 81%입니다.",
        issues=make_issues(),
        evidence=make_evidence(),
        band_label_ko="개선 필요",
        run_ids=("11111111-1111-4111-8111-111111111111",),
        data_sources=("VEO_CRAWLER",),
    )
    geo = DomainDiagnosis(
        key="GEO_READINESS",
        name_ko="GEO 준비도",
        score=make_geo_score(),
        conditions=make_conditions(),
        summary_ko="GEO 준비도 55.0점입니다.",
        issues=(),
        evidence=(),
        band_label_ko="취약",
        run_ids=("22222222-2222-4222-8222-222222222222",),
        data_sources=("VEO_CRAWLER",),
    )

    keywords = (
        KeywordDemand(
            keyword="강남 임플란트",
            monthly_searches=MeasuredValue.measured(
                14800.0, source="NAVER_SEARCH_AD", unit="회", decimals=0
            ),
            opportunity=MeasuredValue.measured(
                62.0, source="CALCULATED", unit="점", decimals=1
            ),
            note_ko="네이버 검색광고 절대 검색량입니다.",
        ),
        KeywordDemand(
            keyword="임플란트 부작용",
            monthly_searches=MeasuredValue.unmeasured(
                "제공자가 보고 하한 미만으로 억제한 값입니다.", source="NAVER_SEARCH_AD", unit="회"
            ),
            opportunity=MeasuredValue.unmeasured(
                "검색량이 없어 기회 점수를 계산할 수 없습니다.", source="CALCULATED"
            ),
            note_ko="",
        ),
    )

    competitors = (
        CompetitorObservation(
            label="경쟁 치과 A",
            slug="competitor-a",
            domain_key="SEO_READINESS",
            theirs=MeasuredValue.measured(COMPETITOR_SCORE, source=SPEC_ID, unit="점"),
            their_conditions=make_conditions(spec_version="1.3.0", pages_examined=118),
            note_ko="",
        ),
    )

    base = DiagnosisInput(
        title_ko="예시치과 검색 준비도 진단",
        audience="BUSINESS",
        generated_at=GENERATED_AT,
        measurement_window_start=WINDOW_START,
        measurement_window_end=WINDOW_END,
        domains=(seo, geo),
        keywords=keywords,
        competitors=competitors,
    )
    return replace(base, **overrides) if overrides else base


def request_body(project_id: uuid.UUID, diagnosis: Any | None = None) -> dict[str, Any]:
    """The same fixture, expressed as the JSON a client would post.

    Built through the router's own request model rather than by hand, so a test that
    asserts a number over HTTP is asserting the number the fixture declares — not a
    second copy of it that could drift.
    """
    from veo.reports.schemas import CreateReportRequest

    request = CreateReportRequest.from_diagnosis(project_id, diagnosis or make_diagnosis())
    return request.model_dump(mode="json")


def version_body(diagnosis: Any | None = None) -> dict[str, Any]:
    """The body for a *new version of an existing report* — no project on it."""
    from veo.reports.schemas import CreateVersionRequest

    request = CreateVersionRequest.from_diagnosis(diagnosis or make_diagnosis())
    return request.model_dump(mode="json")


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
