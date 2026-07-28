"""검색엔진 연동 — four checks VEO cannot answer by crawling.

Ownership of a Search Console property, registration in Naver Search Advisor and the
state of a submitted sitemap are facts held by the search engine, not by the site. With
no credential every one of them is UNKNOWN with a Korean reason, which lowers coverage
and leaves the score untouched. A guess here would be a claim about someone's account.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
PROVIDER_NAVER_SEARCH_ADVISOR = "NAVER_SEARCH_ADVISOR"
PROVIDER_INDEXNOW = "INDEXNOW"


class SearchEngineIntegrationCollector(SeoCollector):
    category_id = "search_engine_integration"
    check_id_list = (
        "seo.integration.gsc_verified",
        "seo.integration.naver_swa_registered",
        "seo.integration.sitemap_submitted",
        "seo.integration.indexnow_configured",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        ledger = EvidenceLedger()
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        gsc, gsc_reason = provider_payload(context, PROVIDER_SEARCH_CONSOLE)
        naver, naver_reason = provider_payload(context, PROVIDER_NAVER_SEARCH_ADVISOR)
        indexnow, indexnow_reason = provider_payload(context, PROVIDER_INDEXNOW)

        for produced, produced_issues in (
            _gsc_verified(context, ledger, gsc, gsc_reason),
            _naver_registered(context, ledger, naver, naver_reason),
            _sitemap_submitted(context, ledger, gsc, gsc_reason),
            _indexnow(context, ledger, indexnow, indexnow_reason),
        ):
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


def _record(ledger: EvidenceLedger, provider: str, payload: Mapping[str, Any], excerpt: str) -> str:
    return ledger.of(
        "provider_response",
        url=None,
        payload=repr(sorted(payload.items())),
        excerpt=excerpt,
        detail={"provider": provider},
    )


def _gsc_verified(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.integration.gsc_verified"
    if payload is None:
        return unknown_outcome(check_id, reason_ko or "소유권 확인 상태를 조회하지 못했습니다."), []

    site = payload.get("site")
    if not isinstance(site, Mapping):
        return (
            unknown_outcome(check_id, "Search Console 응답에 소유권 정보가 없습니다."),
            [],
        )

    verified = bool(site.get("verified"))
    evidence = [
        _record(
            ledger,
            PROVIDER_SEARCH_CONSOLE,
            payload,
            f"소유권 확인: {'예' if verified else '아니오'} "
            f"(권한 {site.get('permission_level', '알 수 없음')})",
        )
    ]

    result = site_outcome(
        check_id,
        passed=verified,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"verified": verified, "permission_level": site.get("permission_level")},
        note=(
            "Search Console에서 사이트 소유권이 확인되어 있습니다."
            if verified
            else "Search Console에 사이트 소유권이 확인되어 있지 않습니다."
        ),
    )
    if verified:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="Google Search Console 소유권이 확인되지 않았습니다",
            summary_ko=(
                "소유권이 확인되지 않으면 색인 상태, 검색 실적, 수동 조치 통보를 전혀 받을 수 "
                "없습니다. 문제가 생겨도 알 방법이 없는 상태입니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "Search Console에서 도메인 속성을 추가하고 DNS TXT 레코드로 소유권을 확인하십시오. "
                "도메인 속성으로 등록하면 하위 도메인과 http·https를 한 번에 포괄합니다."
            ),
            reverification_ko="확인 절차 후 속성 상태를 다시 조회해 verified인지 확인합니다.",
            business_impact_ko="색인 문제와 수동 조치를 사후에야 알게 되어 대응이 늦어집니다.",
        )
    ]


def _naver_registered(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.integration.naver_swa_registered"
    if payload is None:
        reason = reason_ko or "서치어드바이저 등록 상태를 조회하지 못했습니다."
        return unknown_outcome(check_id, reason), []

    registered = bool(payload.get("site_registered"))
    verified = bool(payload.get("ownership_verified", registered))
    evidence = [
        _record(
            ledger,
            PROVIDER_NAVER_SEARCH_ADVISOR,
            payload,
            f"사이트 등록: {'예' if registered else '아니오'}, "
            f"소유 확인: {'예' if verified else '아니오'}",
        )
    ]

    passed = registered and verified
    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"site_registered": registered, "ownership_verified": verified},
        note=(
            "네이버 서치어드바이저에 사이트가 등록되어 있습니다."
            if passed
            else "네이버 서치어드바이저에 사이트가 등록·확인되어 있지 않습니다."
        ),
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="네이버 서치어드바이저에 사이트가 등록되어 있지 않습니다",
            summary_ko=(
                "국내 검색 유입의 상당 부분이 네이버에서 발생하는데, 서치어드바이저에 등록하지 "
                "않으면 수집 요청도 진단도 할 수 없습니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "네이버 서치어드바이저에서 사이트를 추가하고 HTML 파일 업로드 또는 메타 태그로 "
                "소유를 확인한 뒤, 사이트맵과 RSS를 함께 제출하십시오."
            ),
            reverification_ko="등록 후 서치어드바이저 상태를 다시 조회해 등록·확인 여부를 봅니다.",
            business_impact_ko="네이버 검색 노출이 늦어지고 수집 오류를 확인할 창구가 없습니다.",
        )
    ]


def _sitemap_submitted(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.integration.sitemap_submitted"
    if payload is None:
        reason = reason_ko or "사이트맵 제출 상태를 조회하지 못했습니다."
        return unknown_outcome(check_id, reason), []

    submitted = payload.get("sitemaps")
    if not isinstance(submitted, Sequence) or isinstance(submitted, str | bytes):
        return unknown_outcome(check_id, "응답에 사이트맵 제출 목록이 없습니다."), []

    entries = [item for item in submitted if isinstance(item, Mapping)]
    processed = [
        item
        for item in entries
        if not item.get("is_pending") and int(item.get("errors", 0) or 0) == 0
    ]
    passed = bool(processed)

    evidence = [
        _record(
            ledger,
            PROVIDER_SEARCH_CONSOLE,
            payload,
            f"제출된 사이트맵 {len(entries)}건, 정상 처리 {len(processed)}건",
        )
    ]

    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"submitted": len(entries), "processed": len(processed)},
        note=(
            f"사이트맵 {len(processed)}건이 제출되어 정상 처리되었습니다."
            if passed
            else "정상 처리된 사이트맵 제출 기록이 없습니다."
        ),
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="사이트맵이 제출되지 않았거나 처리되지 않았습니다",
            summary_ko=(
                f"검색엔진에 제출된 사이트맵 {len(entries)}건 가운데 정상 처리된 건이 없습니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "Search Console의 사이트맵 메뉴에서 사이트맵 주소를 제출하고, 오류가 표시되면 "
                "해당 URL 목록을 정리한 뒤 다시 제출하십시오."
            ),
            reverification_ko="제출 후 처리 상태가 '성공'으로 바뀌는지 다시 조회합니다.",
            business_impact_ko="새 페이지가 수집되기까지 걸리는 시간이 길어집니다.",
        )
    ]


def _indexnow(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.integration.indexnow_configured"
    if payload is None:
        return (
            unknown_outcome(
                check_id,
                reason_ko
                or "변경 통지 구성 여부를 확인할 수 있는 연동이 없습니다. "
                "미구성으로 단정하지 않습니다.",
            ),
            [],
        )

    configured = bool(payload.get("configured"))
    evidence = [
        _record(
            ledger,
            PROVIDER_INDEXNOW,
            payload,
            f"IndexNow 구성: {'예' if configured else '아니오'} "
            f"(키 위치 {payload.get('key_location', '없음')})",
        )
    ]

    result = site_outcome(
        check_id,
        passed=configured,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"configured": configured},
        note=(
            "IndexNow 변경 통지가 구성되어 있습니다."
            if configured
            else "IndexNow 변경 통지가 구성되어 있지 않습니다."
        ),
    )
    if configured:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="IndexNow 변경 통지가 구성되어 있지 않습니다",
            summary_ko=(
                "페이지를 새로 올리거나 고쳤을 때 검색엔진에 즉시 알리는 경로가 없습니다. "
                "필수 항목은 아니지만 갱신 반영 속도에 도움이 됩니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "IndexNow 키 파일을 도메인 루트에 올리고, 콘텐츠 발행·수정 시점에 해당 URL을 "
                "통지하도록 배포 절차에 연결하십시오."
            ),
            reverification_ko="구성 후 키 파일 응답과 통지 로그를 다시 확인합니다.",
            business_impact_ko="수정 사항이 검색 결과에 반영되기까지 시간이 더 걸립니다.",
        )
    ]


__all__ = [
    "PROVIDER_INDEXNOW",
    "PROVIDER_NAVER_SEARCH_ADVISOR",
    "PROVIDER_SEARCH_CONSOLE",
    "SearchEngineIntegrationCollector",
]
