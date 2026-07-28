"""성능·사용자 경험.

Three of these seven checks are read from the crawl. The other four are measurements
VEO cannot take itself, and this module's most important behaviour is what it does when
it cannot take them: it reports UNKNOWN with a Korean reason and stops. It never
estimates a Largest Contentful Paint from page size, and it never treats "we have no
PageSpeed credential" as "the site is slow".

Where a provider *is* connected, the provider's own verdict is what gets read. Lighthouse
publishes a normalised 0-to-1 score per audit with its own pass/average bands; CrUX
publishes a FAST/AVERAGE/SLOW category. VEO reports those categories rather than
re-deriving them from a raw millisecond value against a threshold of its own invention.

Lab and field are never merged. ``seo.perf.*_lab`` reads PageSpeed only and
``seo.perf.inp_field`` reads CrUX only, so a single credential can never make the other
half of the picture appear measured.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.scoring import CheckOutcome, CheckStatus
from veo.seo.collectors.base import (
    DIRECT,
    NO_DOCUMENTS_KO,
    OFFICIAL_API,
    EvidenceLedger,
    SeoCollector,
    all_unknown,
    issue,
    provider_payload,
    site_outcome,
    url_ratio_outcome,
)
from veo.seo.observation import SiteObservation
from veo.seo.parsing import is_https, resolve

PROVIDER_PAGESPEED = "GOOGLE_PAGESPEED"
PROVIDER_CRUX = "GOOGLE_CRUX"

#: Lighthouse's own published band boundaries for an audit score. These are the
#: provider's classification, reproduced so VEO reports what Lighthouse reports; they
#: are not VEO thresholds and they decide no points.
_LIGHTHOUSE_PASS = 0.9
_LIGHTHOUSE_AVERAGE = 0.5

_LAB_AUDITS = {
    "seo.perf.lcp_lab": ("largest-contentful-paint", "LCP(최대 콘텐츠 표시 시간)"),
    "seo.perf.cls_lab": ("cumulative-layout-shift", "CLS(누적 레이아웃 이동)"),
    "seo.perf.tbt_lab": ("total-blocking-time", "TBT(총 차단 시간)"),
}

_CRUX_METRIC = "INTERACTION_TO_NEXT_PAINT"

_CRUX_STATUS = {
    "FAST": CheckStatus.PASS,
    "AVERAGE": CheckStatus.WARNING,
    "SLOW": CheckStatus.FAIL,
}


class PerformanceUxCollector(SeoCollector):
    category_id = "performance_ux"
    check_id_list = (
        "seo.perf.lcp_lab",
        "seo.perf.cls_lab",
        "seo.perf.tbt_lab",
        "seo.perf.inp_field",
        "seo.ux.mobile_viewport",
        "seo.security.https_valid",
        "seo.security.no_mixed_content",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        site = self.observe(context)
        if not site.has_pages:
            return all_unknown(self.check_id_list, NO_DOCUMENTS_KO)

        ledger = EvidenceLedger()
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        lab_payload, lab_reason = provider_payload(context, PROVIDER_PAGESPEED)
        for check_id in _LAB_AUDITS:
            produced, produced_issues = _lab_metric(
                context, site, ledger, check_id, lab_payload, lab_reason
            )
            outcomes.append(produced)
            issues.extend(produced_issues)

        produced, produced_issues = _field_metric(context, site, ledger)
        outcomes.append(produced)
        issues.extend(produced_issues)

        for step in (_viewport, _https, _mixed_content):
            produced, produced_issues = step(context, site, ledger)
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


# --------------------------------------------------------------------------- #
# Lab metrics — PageSpeed only
# --------------------------------------------------------------------------- #


def _lab_metric(
    context: CollectionContext,
    site: SiteObservation,
    ledger: EvidenceLedger,
    check_id: str,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    audit_id, label_ko = _LAB_AUDITS[check_id]

    if payload is None:
        return unknown_outcome(check_id, reason_ko or f"{label_ko}을(를) 측정하지 못했습니다."), []

    measured: dict[str, dict[str, Any]] = {}
    for page in site.pages:
        entry = payload.get(page.url)
        if not isinstance(entry, Mapping):
            continue
        audits = entry.get("lighthouse")
        if not isinstance(audits, Mapping):
            continue
        audit = audits.get(audit_id)
        if not isinstance(audit, Mapping) or not isinstance(audit.get("score"), int | float):
            continue
        measured[page.url] = dict(audit)

    if not measured:
        return (
            unknown_outcome(
                check_id,
                f"연동은 되어 있으나 수집한 URL에 대한 {label_ko} 측정값이 응답에 없습니다.",
            ),
            [],
        )

    evaluated = [page for page in site.pages if page.url in measured]
    failing = [
        page for page in evaluated if float(measured[page.url]["score"]) < _LIGHTHOUSE_AVERAGE
    ]
    middling = [
        page
        for page in evaluated
        if _LIGHTHOUSE_AVERAGE <= float(measured[page.url]["score"]) < _LIGHTHOUSE_PASS
    ]

    evidence = [
        ledger.of(
            "lighthouse_run",
            url=page.url,
            payload=str(measured[page.url]),
            excerpt=(
                f"{label_ko}: {measured[page.url].get('display_value', '')} "
                f"(Lighthouse 점수 {measured[page.url]['score']})"
            ),
            detail={"audit": audit_id, **measured[page.url]},
        )
        for page in (failing or middling or evaluated[:1])
    ]

    affected = failing or middling
    result = url_ratio_outcome(
        check_id,
        affected=affected,
        evaluated=evaluated,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={
            url: {"score": value["score"], "display_value": value.get("display_value")}
            for url, value in measured.items()
        },
        clean_note_ko=f"{label_ko}이(가) 제공자 기준으로 양호합니다.",
        affected_note_ko=f"{len(affected)}개 URL의 {label_ko}이(가) 제공자 기준에 미치지 못합니다.",
        warning=not failing,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    displayed = ", ".join(
        f"{page.url} {measured[page.url].get('display_value', '')}" for page in affected[:5]
    )
    return result, [
        issue(
            context,
            check_id,
            title_ko=f"{label_ko}이(가) 기준을 넘습니다",
            summary_ko=(
                f"PageSpeed Insights가 보고한 {label_ko}이(가) {len(affected)}개 URL에서 "
                f"기준에 미치지 못합니다: {displayed}"
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=_LAB_REMEDIATION_KO[check_id],
            reverification_ko="개선 후 같은 URL로 PageSpeed 측정을 다시 실행해 값을 비교합니다.",
            business_impact_ko="첫 화면이 늦게 뜰수록 방문자가 기다리지 않고 이탈합니다.",
        )
    ]


_LAB_REMEDIATION_KO = {
    "seo.perf.lcp_lab": (
        "첫 화면에 보이는 가장 큰 이미지의 용량을 줄이고 WebP 같은 형식으로 바꾸십시오. "
        "해당 이미지에 우선 로딩을 지정하고, 첫 화면을 가리는 외부 스크립트는 뒤로 미룹니다."
    ),
    "seo.perf.cls_lab": (
        "이미지와 광고 영역에 width·height 또는 aspect-ratio를 지정해 자리를 먼저 잡아 두십시오. "
        "뒤늦게 삽입되는 배너는 본문 위가 아니라 정해진 자리에 넣습니다."
    ),
    "seo.perf.tbt_lab": (
        "첫 화면에 필요 없는 자바스크립트를 나중에 불러오도록 분리하고, 사용하지 않는 라이브러리를 "
        "제거하십시오. 채팅·통계 스크립트는 defer로 미루는 것만으로도 크게 줄어듭니다."
    ),
}


# --------------------------------------------------------------------------- #
# Field metric — CrUX only
# --------------------------------------------------------------------------- #


def _field_metric(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.perf.inp_field"
    payload, reason_ko = provider_payload(context, PROVIDER_CRUX)
    if payload is None:
        return unknown_outcome(check_id, reason_ko or "INP(field) 값을 측정하지 못했습니다."), []

    categories: dict[str, str] = {}
    for page in site.pages:
        entry = payload.get(page.url)
        if not isinstance(entry, Mapping):
            continue
        metrics = entry.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        metric = metrics.get(_CRUX_METRIC)
        if not isinstance(metric, Mapping):
            continue
        category = str(metric.get("category", "")).upper()
        if category in _CRUX_STATUS:
            categories[page.url] = category

    if not categories:
        # CrUX only publishes a URL that has enough real-user samples. No sample is a
        # fact about traffic volume, not a fault in the site.
        return (
            not_applicable_outcome(
                check_id,
                "수집한 URL에 CrUX 표본이 없어 field 값이 존재하지 않습니다. 실제 방문자 "
                "표본이 쌓이면 자동으로 평가 대상이 됩니다.",
            ),
            [],
        )

    evaluated = [page for page in site.pages if page.url in categories]
    failing = [page for page in evaluated if categories[page.url] == "SLOW"]
    middling = [page for page in evaluated if categories[page.url] == "AVERAGE"]

    evidence = [
        ledger.of(
            "crux_record",
            url=page.url,
            payload=f"{_CRUX_METRIC}={categories[page.url]}",
            excerpt=f"INP(field) 구간: {categories[page.url]}",
            detail={"metric": _CRUX_METRIC, "category": categories[page.url]},
        )
        for page in (failing or middling or evaluated[:1])
    ]

    affected = failing or middling
    result = url_ratio_outcome(
        check_id,
        affected=affected,
        evaluated=evaluated,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value=categories,
        clean_note_ko="CrUX가 보고한 INP(field) 구간이 양호합니다.",
        affected_note_ko=f"{len(affected)}개 URL의 INP(field) 구간이 기준에 미치지 못합니다.",
        warning=not failing,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="실제 사용자 기준 INP가 기준을 넘습니다",
            summary_ko=(
                f"CrUX가 보고한 실제 방문자 기준 INP 구간이 {len(affected)}개 URL에서 "
                "양호하지 않습니다. 실험실 값이 아니라 실제 방문 기록입니다."
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=(
                "버튼과 입력에 걸린 무거운 처리를 나누어 실행하고, 스크롤·입력 도중 실행되는 "
                "스크립트를 줄이십시오. 목록을 한 번에 그리는 화면이라면 화면에 보이는 만큼만 "
                "그리도록 바꾸는 편이 효과가 큽니다."
            ),
            reverification_ko="개선 배포 후 4주쯤 지나 CrUX 값이 갱신되면 다시 확인합니다.",
            business_impact_ko="누르고 반응이 없는 순간이 길수록 예약·문의 도중 이탈이 늘어납니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# Observed from the crawl
# --------------------------------------------------------------------------- #


def _viewport(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    problems: dict[str, str] = {}
    for page in site.pages:
        viewport = (page.raw.viewport or "").lower().replace(" ", "")
        if not viewport:
            problems[page.url] = "viewport 메타 태그가 없습니다"
        elif "width=device-width" not in viewport:
            problems[page.url] = "width=device-width가 지정되지 않았습니다"
        elif "user-scalable=no" in viewport or "maximum-scale=1" in viewport:
            problems[page.url] = "확대를 막는 설정이 들어 있습니다"

    affected = [page for page in site.pages if page.url in problems]
    evidence = [
        ledger.page_snippet(
            page, "dom_snippet", f'<meta name="viewport" content="{page.raw.viewport or ""}">'
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.ux.mobile_viewport",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko="모든 페이지에 모바일 viewport가 올바르게 선언되어 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지의 viewport 선언에 문제가 있습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.ux.mobile_viewport",
            title_ko="모바일 viewport 선언에 문제가 있습니다",
            summary_ko="; ".join(f"{url} — {reason}" for url, reason in list(problems.items())[:5]),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                'head에 `<meta name="viewport" content="width=device-width, initial-scale=1">`을 '
                "넣으십시오. 확대를 막는 user-scalable=no는 접근성 문제로도 이어지므로 제거합니다."
            ),
            reverification_ko="수정 후 재수집해 viewport 선언 내용을 확인합니다.",
            business_impact_ko="모바일에서 화면이 깨지면 대부분의 검색 유입이 그대로 이탈합니다.",
            fix_example='<meta name="viewport" content="width=device-width, initial-scale=1">',
        )
    ]


def _https(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    # A completed HTTPS fetch means the certificate chain verified — the fetcher does not
    # disable verification. What cannot be observed from here is expiry margin or a
    # weak chain, so this reports what the handshake proved and nothing more.
    insecure = [page for page in site.pages if not is_https(page.url)]
    evidence = [
        ledger.of(
            "tls_handshake",
            url=page.url,
            payload=f"{page.url} scheme={'https' if is_https(page.url) else 'http'}",
            excerpt=(
                "HTTPS로 응답했고 인증서 검증을 통과했습니다."
                if is_https(page.url)
                else "평문 HTTP로 응답했습니다."
            ),
            detail={"scheme": "https" if is_https(page.url) else "http"},
        )
        for page in (insecure or site.pages[:1])
    ]

    result = site_outcome(
        "seo.security.https_valid",
        passed=not insecure,
        evidence_ids=evidence,
        observed_value={"insecure": [page.url for page in insecure]},
        note=(
            "수집한 모든 URL이 HTTPS로 응답했고 인증서 검증을 통과했습니다."
            if not insecure
            else f"{len(insecure)}개 URL이 평문 HTTP로 응답했습니다."
        ),
    )
    if not insecure:
        return result, []

    return result, [
        issue(
            context,
            "seo.security.https_valid",
            title_ko="일부 URL이 HTTPS로 제공되지 않습니다",
            summary_ko=f"{len(insecure)}개 URL이 평문 HTTP로 응답했습니다.",
            affected_urls=[page.url for page in insecure],
            evidence_ids=evidence,
            remediation_ko=(
                "인증서를 설치하고 HTTP 요청을 같은 경로의 HTTPS로 301 리다이렉트하십시오. "
                "내부 링크와 사이트맵의 주소도 함께 https로 바꿔야 리다이렉트가 쌓이지 않습니다."
            ),
            reverification_ko="적용 후 http 주소로 요청해 https로 한 번에 이동하는지 확인합니다.",
            business_impact_ko="브라우저가 주소창에 경고를 띄워 방문자가 예약·결제를 중단합니다.",
        )
    ]


def _mixed_content(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    secure_pages = [page for page in site.pages if is_https(page.url)]
    if not secure_pages:
        return (
            unknown_outcome(
                "seo.security.no_mixed_content",
                "HTTPS로 응답한 URL이 없어 혼합 콘텐츠를 판단할 대상이 없습니다.",
            ),
            [],
        )

    offenders: dict[str, list[str]] = {}
    for page in secure_pages:
        # The rendered DOM is what the browser actually loaded; prefer it when one exists.
        view = page.effective
        insecure = [
            source
            for source in view.subresources
            if (resolve(page.url, source) or "").startswith("http://")
        ]
        if insecure:
            offenders[page.url] = insecure

    affected = [page for page in secure_pages if page.url in offenders]
    evidence = [
        ledger.of(
            "network_log",
            url=page.url,
            payload="\n".join(offenders.get(page.url, [])) or "평문 HTTP 리소스 없음",
            excerpt="; ".join(offenders.get(page.url, [])[:5]) or "평문 HTTP 리소스 없음",
            detail={
                "source": "rendered_dom" if page.rendered is not None else "raw_html",
                "count": len(offenders.get(page.url, [])),
            },
        )
        for page in (affected or secure_pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.security.no_mixed_content",
        affected=affected,
        evaluated=secure_pages,
        confidence_level=DIRECT,
        evidence_ids=evidence,
        observed_value=offenders or None,
        clean_note_ko="HTTPS 페이지가 평문 HTTP 리소스를 불러오지 않습니다.",
        affected_note_ko=f"{len(affected)}개 HTTPS 페이지가 평문 HTTP 리소스를 불러옵니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    total = sum(len(values) for values in offenders.values())
    return result, [
        issue(
            context,
            "seo.security.no_mixed_content",
            title_ko="HTTPS 페이지가 평문 HTTP 리소스를 불러옵니다",
            summary_ko=(
                f"{len(affected)}개 페이지에서 이미지·스크립트 등 {total}개 리소스를 http로 "
                "불러오고 있습니다. 브라우저가 이를 차단하거나 경고를 표시합니다."
            ),
            affected_urls=list(offenders),
            evidence_ids=evidence,
            remediation_ko=(
                "리소스 주소를 https로 바꾸거나 프로토콜을 생략한 상대 경로로 바꾸십시오. "
                "외부 서비스가 https를 지원하지 않으면 대체 서비스를 찾는 편이 낫습니다."
            ),
            reverification_ko="수정 후 재수집해 http로 시작하는 리소스가 남아 있는지 확인합니다.",
            business_impact_ko="차단된 이미지나 스크립트 때문에 화면이 깨지고 신뢰도가 떨어집니다.",
        )
    ]


__all__ = ["PROVIDER_CRUX", "PROVIDER_PAGESPEED", "PerformanceUxCollector"]
