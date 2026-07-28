"""관측·성과 — whether anyone is watching, kept apart from the technical readiness.

Search performance is not readiness. The specification gives this category the smallest
weight in the domain and its description says the two are reported separately, because a
site can be technically perfect and have no traffic yet, and a site can rank well while
sitting on faults about to bite. This module reports only whether the data exists, is
fresh and is not collapsing — never how good it is.

Without a Search Console credential all three checks are UNKNOWN.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    IssueDraft,
    unknown_outcome,
)
from veo.scoring import CheckOutcome
from veo.seo.collectors.base import (
    OFFICIAL_API,
    EvidenceLedger,
    SeoCollector,
    issue,
    provider_payload,
    site_outcome,
)

PROVIDER_SEARCH_CONSOLE = "GOOGLE_SEARCH_CONSOLE"

#: Days after which performance data is stale enough to be worth reporting.
MAX_DATA_AGE_DAYS = 7

#: Proportion of indexed pages that may disappear before the drop is worth reporting.
MAX_INDEX_DROP_RATIO = 0.3


class ObservabilityOutcomesCollector(SeoCollector):
    category_id = "observability_outcomes"
    check_id_list = (
        "seo.outcome.impressions_available",
        "seo.outcome.index_coverage_healthy",
        "seo.outcome.data_freshness",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        ledger = EvidenceLedger()
        payload, reason_ko = provider_payload(context, PROVIDER_SEARCH_CONSOLE)

        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        for step in (_impressions, _index_coverage, _freshness):
            produced, produced_issues = step(context, ledger, payload, reason_ko)
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


def _record(ledger: EvidenceLedger, payload: Mapping[str, Any], excerpt: str) -> str:
    return ledger.of(
        "provider_response",
        url=None,
        payload=repr(sorted(payload.items())),
        excerpt=excerpt,
        detail={"provider": PROVIDER_SEARCH_CONSOLE},
    )


def _impressions(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.outcome.impressions_available"
    if payload is None:
        return unknown_outcome(check_id, reason_ko or "노출 데이터를 조회하지 못했습니다."), []

    performance = payload.get("performance")
    if not isinstance(performance, Mapping):
        return unknown_outcome(check_id, "응답에 검색 실적 항목이 없습니다."), []

    rows = int(performance.get("rows", 0) or 0)
    impressions = int(performance.get("impressions", 0) or 0)
    passed = rows > 0

    evidence = [_record(ledger, payload, f"검색 실적 {rows}행, 노출 {impressions}회")]
    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"rows": rows, "impressions": impressions},
        note=(
            f"검색 노출 데이터가 {rows}행 수집되고 있습니다."
            if passed
            else "검색 노출 데이터가 한 행도 수집되지 않았습니다."
        ),
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="검색 노출 데이터가 수집되지 않고 있습니다",
            summary_ko=(
                "연동은 되어 있으나 노출 데이터가 비어 있습니다. 색인이 아직 되지 않았거나, "
                "속성 범위가 실제 서비스 도메인과 어긋나 있을 수 있습니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "Search Console 속성이 실제 서비스 도메인과 같은지 확인하고, 색인 생성 요청으로 "
                "주요 페이지부터 수집을 요청하십시오."
            ),
            reverification_ko="이레 뒤 다시 조회해 노출 행이 쌓이는지 확인합니다.",
            business_impact_ko=(
                "성과를 확인할 수 없어 어떤 개선이 효과가 있었는지 판단할 수 없습니다."
            ),
        )
    ]


def _index_coverage(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.outcome.index_coverage_healthy"
    if payload is None:
        return unknown_outcome(check_id, reason_ko or "색인 커버리지를 조회하지 못했습니다."), []

    coverage = payload.get("index_coverage")
    if not isinstance(coverage, Mapping) or "indexed" not in coverage:
        return unknown_outcome(check_id, "응답에 색인 커버리지 항목이 없습니다."), []

    indexed = int(coverage.get("indexed", 0) or 0)
    previous = coverage.get("previous_indexed")
    if previous is None:
        return (
            unknown_outcome(
                check_id,
                "직전 색인 수치가 없어 악화 여부를 비교하지 못했습니다. 다음 수집부터 비교됩니다.",
            ),
            [],
        )

    previous_count = int(previous or 0)
    dropped = previous_count - indexed
    ratio = dropped / previous_count if previous_count > 0 else 0.0
    passed = ratio <= MAX_INDEX_DROP_RATIO

    evidence = [
        _record(
            ledger,
            payload,
            f"색인 {previous_count} → {indexed} (감소율 {round(ratio * 100, 1)}%)",
        )
    ]
    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"indexed": indexed, "previous_indexed": previous_count, "drop": dropped},
        note=(
            "색인 커버리지에 급격한 감소가 없습니다."
            if passed
            else f"색인된 페이지가 {previous_count}개에서 {indexed}개로 줄었습니다."
        ),
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="색인된 페이지 수가 급격히 줄었습니다",
            summary_ko=(
                f"색인 페이지가 {previous_count}개에서 {indexed}개로 "
                f"{round(ratio * 100, 1)}% 줄었습니다. 배포 사고나 차단 설정을 먼저 의심해야 "
                "하는 신호입니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "최근 배포에서 robots.txt, noindex 설정, 리다이렉트 규칙이 바뀌지 않았는지 "
                "확인하십시오. Search Console의 색인 제외 사유별 목록을 보면 원인을 좁힐 수 "
                "있습니다."
            ),
            reverification_ko="원인 조치 후 색인 수치가 회복되는지 다음 수집에서 비교합니다.",
            business_impact_ko="색인에서 빠진 페이지 수만큼 검색 유입이 즉시 사라집니다.",
        )
    ]


def _freshness(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.outcome.data_freshness"
    if payload is None:
        reason = reason_ko or "성과 데이터의 최신성을 확인하지 못했습니다."
        return unknown_outcome(check_id, reason), []

    performance = payload.get("performance")
    if not isinstance(performance, Mapping) or not performance.get("date_range_end"):
        return (
            unknown_outcome(check_id, "응답에 데이터 기준일이 없어 최신성을 확인하지 못했습니다."),
            [],
        )

    observed_at = _parse_date(str(performance["date_range_end"]))
    if observed_at is None:
        return unknown_outcome(check_id, "데이터 기준일 형식을 해석하지 못했습니다."), []

    age_days = (context.collected_at - observed_at).days
    passed = age_days <= MAX_DATA_AGE_DAYS

    evidence = [
        _record(ledger, payload, f"데이터 기준일 {observed_at.date()}, 경과 {age_days}일")
    ]
    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"date_range_end": observed_at.isoformat(), "age_days": age_days},
        note=(
            f"성과 데이터가 {age_days}일 전 기준으로 최신입니다."
            if passed
            else f"성과 데이터가 {age_days}일 전 기준에서 갱신되지 않았습니다."
        ),
        warning=True,
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="성과 데이터가 최신 상태가 아닙니다",
            summary_ko=(
                f"가장 최근 성과 데이터가 {observed_at.date()} 기준이며 {age_days}일이 "
                f"지났습니다. 기준은 {MAX_DATA_AGE_DAYS}일입니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "연동 계정의 권한이 유지되고 있는지, 수집 작업이 실패하고 있지 않은지 "
                "확인하십시오. "
                "권한이 회수되면 조회는 성공해도 값이 갱신되지 않습니다."
            ),
            reverification_ko="연동 점검 후 데이터 기준일이 최근으로 바뀌는지 확인합니다.",
            business_impact_ko="오래된 수치로 판단하면 이미 끝난 문제를 좇거나 새 문제를 놓칩니다.",
        )
    ]


def _parse_date(value: str) -> datetime | None:
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


__all__ = [
    "MAX_DATA_AGE_DAYS",
    "MAX_INDEX_DROP_RATIO",
    "PROVIDER_SEARCH_CONSOLE",
    "ObservabilityOutcomesCollector",
]
