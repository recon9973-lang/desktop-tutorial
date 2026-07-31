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
    outcome,
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
        "seo.perf.text_compression",
        "seo.perf.modern_image_format",
        "seo.perf.resource_hints",
        "seo.security.certificate_not_expiring",
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

        for step in (
            _viewport,
            _https,
            _mixed_content,
            _text_compression,
            _modern_image_format,
            _resource_hints,
            _certificate_expiry,
        ):
            produced, produced_issues = step(context, site, ledger)
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


# --------------------------------------------------------------------------- #
# Lab metrics — PageSpeed only
# --------------------------------------------------------------------------- #


def lab_sample(context: CollectionContext, site: SiteObservation) -> list[str]:
    """실험실 성능을 잴 페이지 목록. 중요도가 높은 순으로 명세가 정한 수만큼.

    **표본을 고르는 곳이 여기 하나뿐이어야 한다.** 수집기와 파이프라인이 각자 고르면
    "잰 페이지" 와 "재려던 페이지" 가 어긋나고, 그 어긋남은 조용히 점수를 올린다 —
    잰 것만 분모에 넣게 되기 때문이다. 그래서 실제로 호출하는 쪽도 이 함수를 쓴다.

    명세가 `sampling.perf_lab` 을 선언하지 않으면 전 페이지를 돌려준다. 표본을 쓰지
    않는다는 뜻이고, 그것이 기존 명세들의 동작이다(ADR 0012).
    """
    policy = getattr(context.spec, "sampling", None)
    lab = getattr(policy, "perf_lab", None) if policy else None
    urls = [page.url for page in site.pages]
    if lab is None:
        return urls

    ranked = sorted(site.pages, key=lambda page: (-page.importance_value, page.url))
    return [page.url for page in ranked[: lab.max_urls]]


def _too_thin(
    context: CollectionContext, planned: list[str], measured: Mapping[str, Any]
) -> str | None:
    """표본이 너무 얇으면 그 이유를 돌려준다. 충분하면 ``None``.

    이 문턱이 왜 필요한지는 실측이 말해 준다. 2026-08-01, Lighthouse 가
    ``FAILED_DOCUMENT_REQUEST`` 로 페이지를 못 여는 사례가 실제로 나왔다. 그리고
    **못 여는 이유는 대개 그 페이지가 느려서**다. 못 잰 페이지를 분모에서 빼면
    느린 페이지만 골라 빼는 셈이고, 사이트는 실제보다 빨라 보인다.

    문턱을 못 넘으면 검사는 측정 불가다. 측정 불가는 배점을 잃으므로(ADR 0016),
    **덜 재서 이득을 볼 수 없다.**
    """
    policy = getattr(context.spec, "sampling", None)
    lab = getattr(policy, "perf_lab", None) if policy else None
    if lab is None or not planned:
        return None

    hit = sum(1 for url in planned if url in measured)
    ratio = hit / len(planned)
    if ratio >= lab.min_measured_ratio:
        return None

    return (
        f"측정하려던 대표 페이지 {len(planned)}장 가운데 {hit}장만 {{label_ko}} 값을 "
        f"받았습니다(기준 {lab.min_measured_ratio:.0%}). 표본이 얇아 사이트 전체를 "
        "대표한다고 볼 수 없어 측정 불가로 보고합니다 — 값을 받지 못한 페이지는 대개 "
        "느려서 열리지 않은 것이므로, 그것을 빼고 계산하면 실제보다 빠르게 나옵니다."
    )


def _sample_note(site: SiteObservation, measured: Mapping[str, Any]) -> str:
    """"몇 장 중 몇 장을 쟀는지" 를 한 문장으로. 전부 쟀으면 빈 문자열."""
    total = len(site.pages)
    hit = sum(1 for page in site.pages if page.url in measured)
    if hit >= total:
        return ""
    return (
        f" 수집한 {total}장 가운데 중요도가 높은 {hit}장을 측정한 값입니다 — "
        "나머지 페이지의 속도는 이 숫자에 포함되지 않았습니다."
    )


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

    planned = lab_sample(context, site)
    thin = _too_thin(context, planned, measured)
    if thin is not None:
        return unknown_outcome(check_id, thin.format(label_ko=label_ko)), []

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
        # 표본으로 쟀다는 사실을 숫자와 **같은 문장**에 적는다. 따로 떼어 놓으면
        # 읽히지 않고, 읽히지 않으면 "사이트 전체가 양호하다" 로 오해된다.
        # 전 페이지를 잰 경우에는 붙이지 않는다 — 늘 붙는 단서는 무시된다.
        clean_note_ko=f"{label_ko}이(가) 제공자 기준으로 양호합니다.{_sample_note(site, measured)}",
        affected_note_ko=(
            f"{len(affected)}개 URL의 {label_ko}이(가) 제공자 기준에 미치지 못합니다."
            f"{_sample_note(site, measured)}"
        ),
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


def _origin_category(
    context: CollectionContext, payload: Mapping[str, Any]
) -> tuple[str, str] | None:
    """사이트 전체 범위의 INP 구간. 없으면 ``None``.

    명세가 `sampling.perf_field.prefer_origin_scope` 를 켜지 않았으면 쓰지 않는다 —
    기존 명세는 페이지 값만 보던 동작 그대로다(ADR 0012).
    """
    policy = getattr(context.spec, "sampling", None)
    field = getattr(policy, "perf_field", None) if policy else None
    if field is None or not field.prefer_origin_scope:
        return None

    for key, entry in payload.items():
        if not isinstance(entry, Mapping) or entry.get("scope") != "ORIGIN":
            continue
        metrics = entry.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        metric = metrics.get(_CRUX_METRIC)
        if not isinstance(metric, Mapping):
            continue
        category = str(metric.get("category", "")).upper()
        if category in _CRUX_STATUS:
            return str(key), category
    return None


def _origin_outcome(
    context: CollectionContext,
    ledger: EvidenceLedger,
    check_id: str,
    origin: tuple[str, str],
) -> tuple[CheckOutcome, list[IssueDraft]]:
    """사이트 전체 값 하나로 판정한다. 범위를 문구에 반드시 적는다."""
    key, category = origin
    evidence = [
        ledger.of(
            "crux_record",
            url=key,
            payload=f"{_CRUX_METRIC}={category} (scope=ORIGIN)",
            excerpt=f"INP(field) 사이트 전체 구간: {category}",
            detail={"metric": _CRUX_METRIC, "category": category, "scope": "ORIGIN"},
        )
    ]
    note = (
        f"페이지별 CrUX 표본이 없어 **사이트 전체** 실사용자 값으로 판정했습니다"
        f"(구간 {category}). 특정 페이지의 값이 아니라 방문이 많은 페이지가 지배하는 "
        "사이트 평균입니다."
    )
    status = _CRUX_STATUS[category]
    return (
        outcome(
            check_id,
            status,
            confidence_level=OFFICIAL_API,
            # 사이트 전체 값은 페이지 비율이 아니다. 하나의 사실이므로 1/1 로 센다 —
            # 여기에 페이지 수를 넣으면 있지도 않은 페이지별 판정을 지어내는 것이 된다.
            affected=1.0 if status is not CheckStatus.PASS else 0.0,
            evaluated=1.0,
            evidence_ids=evidence,
            observed_value={key: {"category": category, "scope": "ORIGIN"}},
            note=note,
        ),
        [],
    )


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
        # 페이지별 표본이 없으면 **사이트 전체(origin) 값**을 본다.
        #
        # 구글은 크롬 사용자에게서 모은 값을 두 범위로 준다: 이 URL 과 이 사이트 전체.
        # 2026-08-01 실측(seoul.go.kr) — 페이지 값 LCP 1041ms·INP 96ms, 사이트 전체 값
        # LCP 1011ms·INP 122ms 가 **같은 응답**에 함께 왔다. 페이지마다 부를 이유가
        # 없고, 따라서 이 지표에는 표본 문제가 없다.
        #
        # 범위를 섞지는 않는다. 사이트 전체 값은 방문이 많은 페이지가 지배하므로 특정
        # URL 에 갖다 붙이면 그 URL 이 겪지 않은 트래픽으로 칭찬하거나 깎게 된다.
        # 그래서 페이지 값이 하나라도 있으면 그것만 쓰고, 하나도 없을 때만 사이트 값을
        # 쓰되 **문구에 그렇게 적는다.**
        origin = _origin_category(context, payload)
        if origin is not None:
            return _origin_outcome(context, ledger, check_id, origin)

        # 페이지 값도 사이트 값도 없다. 방문자 수에 관한 사실이지 사이트의 결함이 아니다.
        return (
            not_applicable_outcome(
                check_id,
                "수집한 URL에도 사이트 전체에도 CrUX 표본이 없어 field 값이 존재하지 "
                "않습니다. 실제 방문자 표본이 쌓이면 자동으로 평가 대상이 됩니다.",
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


def _viewport_directives(value: str) -> dict[str, str]:
    """`width=device-width,initial-scale=1` 을 키-값으로 나눈다."""
    directives: dict[str, str] = {}
    for part in value.split(","):
        key, _, raw = part.partition("=")
        directives[key.strip()] = raw.strip()
    return directives


def _blocks_zoom(value: str) -> bool:
    """확대를 막는 설정인가.

    부분 문자열로 찾으면 안 된다. `"maximum-scale=1" in viewport` 는 **`maximum-scale=10`
    에도 걸린다** — 확대를 10배까지 허용하는 설정을 확대 금지라고 지적하던 원인이다.
    값을 숫자로 읽고 1 이하일 때만 확대가 막힌 것으로 본다.
    """
    directives = _viewport_directives(value)
    if directives.get("user-scalable") in {"no", "0"}:
        return True
    try:
        return float(directives["maximum-scale"]) <= 1.0
    except (KeyError, ValueError):
        return False


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
        elif _blocks_zoom(viewport):
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


# --------------------------------------------------------------------------- #
# seo.perf.text_compression
# --------------------------------------------------------------------------- #

#: 서버가 텍스트를 압축해 보냈다고 말하는 값들. `identity` 는 압축하지 않았다는 뜻이다.
_COMPRESSED_ENCODINGS = frozenset({"gzip", "br", "deflate", "zstd", "compress"})


def _text_compression(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    """압축 전송은 전송량을 줄여 LCP 에 직접 영향을 준다.

    응답 헤더가 말해 주는 사실이므로 추정이 아니다. 다만 우리가 `Accept-Encoding` 을
    보냈는데도 압축이 오지 않은 경우만 지적할 수 있다 — 서버가 우리에게 압축을 주지
    않았다는 것 이상은 알 수 없다.
    """
    observed: dict[str, str] = {}
    affected = []
    for page in site.pages:
        encoding = (page.header("content-encoding") or "").strip().lower()
        observed[page.url] = encoding or "(없음)"
        tokens = {token.strip() for token in encoding.split(",")}
        if not tokens & _COMPRESSED_ENCODINGS:
            affected.append(page)

    evidence = [
        ledger.page_snippet(
            page,
            "http_response",
            f"content-encoding: {observed[page.url]}",
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.perf.text_compression",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=observed,
        clean_note_ko="모든 페이지가 압축되어 전송됩니다.",
        affected_note_ko=f"{len(affected)}개 페이지가 압축 없이 전송됩니다.",
        warning=True,
    )
    if result.status is not CheckStatus.WARNING:
        return result, []

    return result, [
        issue(
            context,
            "seo.perf.text_compression",
            title_ko="HTML이 압축 없이 전송됩니다",
            summary_ko="; ".join(
                f"{page.url} — content-encoding {observed[page.url]}" for page in affected[:5]
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=(
                "웹서버에서 gzip 또는 brotli 압축을 켜십시오. Nginx 는 gzip on, "
                "Apache 는 mod_deflate, 카페24·가비아 같은 호스팅은 관리 화면에 "
                "압축 설정이 있습니다."
            ),
            reverification_ko=(
                "수정 후 재수집해 응답 헤더에 content-encoding 이 오는지 확인합니다."
            ),
            business_impact_ko=(
                "같은 화면을 보여주는 데 전송량이 몇 배로 늘어, 모바일에서 첫 화면이 "
                "늦게 뜹니다."
            ),
            fix_example="gzip on;\ngzip_types text/html text/css application/javascript;",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.perf.modern_image_format
# --------------------------------------------------------------------------- #

_MODERN_IMAGE_SUFFIXES = (".webp", ".avif")
_LEGACY_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".bmp")


def _image_suffix(src: str) -> str:
    path = src.split("?", 1)[0].split("#", 1)[0].lower()
    _, _, tail = path.rpartition("/")
    return tail[tail.rfind(".") :] if "." in tail else ""


def _modern_image_format(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    """WebP·AVIF 는 같은 화질에서 용량이 작다.

    구글이 특정 포맷을 요구하지는 않는다. 그래서 필수 항목이 아니라 개선 여지로 본다 —
    실패가 아니라 주의로 남기고, 이미지가 없는 페이지는 대상에서 뺀다.
    """
    counted: dict[str, dict[str, int]] = {}
    candidates = []
    for page in site.pages:
        legacy = [
            img for img in page.raw.images if _image_suffix(img.src) in _LEGACY_IMAGE_SUFFIXES
        ]
        modern = [
            img for img in page.raw.images if _image_suffix(img.src) in _MODERN_IMAGE_SUFFIXES
        ]
        if not legacy and not modern:
            continue  # 이미지가 없거나 확장자를 알 수 없는 페이지는 판단하지 않는다
        candidates.append(page)
        counted[page.url] = {"legacy": len(legacy), "modern": len(modern)}

    if not candidates:
        return (
            not_applicable_outcome(
                "seo.perf.modern_image_format",
                "포맷을 확인할 수 있는 이미지가 없어 해당하지 않습니다.",
            ),
            [],
        )

    affected = [page for page in candidates if counted[page.url]["legacy"] > 0]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            " / ".join(img.src for img in page.raw.images[:4]) or "(이미지 없음)",
        )
        for page in (affected or candidates[:1])
    ]

    result = url_ratio_outcome(
        "seo.perf.modern_image_format",
        affected=affected,
        evaluated=candidates,
        evidence_ids=evidence,
        observed_value=counted,
        clean_note_ko="이미지가 모두 WebP 또는 AVIF 로 제공됩니다.",
        affected_note_ko=(
            f"{len(affected)}개 페이지에 JPEG·PNG 이미지가 남아 있습니다 — "
            "WebP 로 바꾸면 용량이 줄어듭니다."
        ),
        warning=True,
    )
    if result.status is not CheckStatus.WARNING:
        return result, []

    return result, [
        issue(
            context,
            "seo.perf.modern_image_format",
            title_ko="이미지가 옛 포맷으로 제공됩니다",
            summary_ko="; ".join(
                f"{page.url} — JPEG·PNG {counted[page.url]['legacy']}개" for page in affected[:5]
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=(
                "이미지를 WebP 로 변환하고, 옛 브라우저를 위해 picture 요소로 원본을 "
                "함께 두십시오. 워드프레스는 변환 플러그인이 자동으로 처리합니다."
            ),
            reverification_ko="변환 후 재수집해 이미지 확장자가 바뀌었는지 확인합니다.",
            business_impact_ko=(
                "사진이 많은 병원 홈페이지일수록 전송량이 커져 모바일 첫 화면이 늦어집니다."
            ),
            fix_example=(
                "<picture>\n"
                '  <source srcset="/hero.webp" type="image/webp">\n'
                '  <img src="/hero.jpg" alt="진료실">\n'
                "</picture>"
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.perf.resource_hints
# --------------------------------------------------------------------------- #


def _resource_hints(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    """preload·preconnect 는 첫 화면 리소스를 앞당긴다.

    있으면 좋은 것이지 없으면 잘못인 것이 아니므로 주의로 남긴다. 힌트가 실제로 옳은
    리소스를 가리키는지까지는 보지 않는다 — 그것은 렌더링을 해 봐야 알 수 있고, 여기서
    말할 수 있는 것은 "선언이 있는가" 뿐이다.
    """
    observed = {
        page.url: [f"{rel}: {href}" for rel, href in page.raw.resource_hints]
        for page in site.pages
    }
    affected = [page for page in site.pages if not page.raw.resource_hints]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            " / ".join(observed[page.url][:3]) or "리소스 힌트 선언 없음",
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.perf.resource_hints",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=observed,
        clean_note_ko="모든 페이지에 우선 로딩 힌트가 선언되어 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지에 우선 로딩 힌트가 없습니다.",
        warning=True,
    )
    if result.status is not CheckStatus.WARNING:
        return result, []

    return result, [
        issue(
            context,
            "seo.perf.resource_hints",
            title_ko="우선 로딩 힌트가 선언되어 있지 않습니다",
            summary_ko=(
                f"{len(affected)}개 페이지에 preload·preconnect 선언이 없습니다. "
                "첫 화면 이미지와 외부 폰트가 늦게 시작됩니다."
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=(
                "첫 화면의 대표 이미지에 preload 를, 외부 폰트·분석 도구 도메인에 "
                "preconnect 를 선언하십시오. 남발하면 오히려 느려지므로 첫 화면에 "
                "실제로 필요한 것만 넣습니다."
            ),
            reverification_ko="수정 후 재수집해 head 에 힌트 선언이 있는지 확인합니다.",
            business_impact_ko="첫 화면이 뜨는 시점이 늦어져 이탈이 늘어납니다.",
            fix_example=(
                '<link rel="preload" as="image" href="/hero.webp">\n'
                '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.security.certificate_not_expiring
# --------------------------------------------------------------------------- #

#: Let's Encrypt 를 비롯한 자동 갱신은 만료 30일 전에 시작한다. 이 구간에 들어와 있다는
#: 것은 **첫 갱신 시도가 이미 실패했다** 는 신호다.
RENEWAL_WINDOW_DAYS = 30

#: 주말이 끼면 손쓸 시간이 없는 구간. 여러 번 실패했다는 뜻이다.
CERTIFICATE_ALARM_DAYS = 7


def _certificate_expiry(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    """인증서가 곧 만료되지 않는가.

    자동 갱신이 실패한 인증서는 만료되는 순간 사이트가 통째로 열리지 않는다. 순위가
    내려가는 것이 아니라 **아무도 못 들어온다.** 핸드셰이크에서 이미 받은 값이므로
    추가 요청 없이 미리 알 수 있고, 미리 아는 것이 이 검사의 전부다.
    """
    check_id = "seo.security.certificate_not_expiring"
    entry = next((page for page in site.pages if page.url == site.entry_url), site.pages[0])

    if not is_https(entry.url):
        return (
            not_applicable_outcome(
                check_id,
                "평문 HTTP 로 응답하는 사이트라 확인할 인증서가 없습니다. HTTPS 사용 여부는 "
                "별도 항목에서 판정합니다.",
            ),
            [],
        )

    # 여러 문서 중 가장 이른 만료일을 본다. 가장 먼저 끊기는 것이 사고 시점이다.
    moments = [
        page.document.tls_expires_at
        for page in site.pages
        if page.document.tls_expires_at is not None
    ]
    if not moments:
        return (
            unknown_outcome(
                check_id,
                "인증서 만료일을 수집하지 못했습니다. 미리 수집된 자료로 채점하는 경우, "
                "수집 단계에서 만료일이 함께 전달되어야 판정할 수 있습니다.",
            ),
            [],
        )

    expires_at = min(moments)
    remaining = (expires_at - context.collected_at).total_seconds() / 86400
    days = int(remaining) if remaining >= 0 else -int(-remaining // 1 + 1)
    observed = {"expires_at": expires_at.isoformat(), "days_remaining": round(remaining, 1)}
    evidence = [
        ledger.page_snippet(
            entry, "http_response", f"인증서 만료 {expires_at.isoformat()} (남은 {days}일)"
        )
    ]

    if remaining >= RENEWAL_WINDOW_DAYS:
        return (
            site_outcome(
                check_id,
                passed=True,
                evidence_ids=evidence,
                observed_value=observed,
                note=(
                    f"인증서 만료까지 {days}일 남았습니다. "
                    "자동 갱신 구간에 아직 들어오지 않았습니다."
                ),
            ),
            [],
        )

    expired = remaining <= 0
    warning = remaining >= CERTIFICATE_ALARM_DAYS
    if expired:
        note = (
            f"인증서가 이미 만료되었습니다({expires_at.isoformat()}). 브라우저가 경고 화면을 "
            "띄우고 검색엔진은 크롤링하지 못합니다."
        )
    elif warning:
        note = (
            f"인증서 만료까지 {days}일 남았습니다. 자동 갱신은 보통 30일 전에 시작하므로, "
            "이 구간에 있다는 것은 첫 갱신 시도가 실패했을 가능성이 큽니다."
        )
    else:
        note = f"인증서 만료까지 {days}일뿐입니다. 갱신이 반복 실패하고 있을 가능성이 큽니다."

    result = site_outcome(
        check_id,
        passed=False,
        evidence_ids=evidence,
        observed_value=observed,
        note=note,
        warning=warning,
    )
    return result, [
        issue(
            context,
            check_id,
            title_ko=(
                "HTTPS 인증서가 만료되었습니다" if expired else "HTTPS 인증서 만료가 임박했습니다"
            ),
            summary_ko=note,
            affected_urls=[entry.url],
            evidence_ids=evidence,
            remediation_ko=(
                "인증서를 즉시 갱신하고, 자동 갱신이 왜 실패했는지 확인하십시오. "
                "certbot 을 쓴다면 갱신 타이머가 살아 있는지와 갱신 시 웹서버가 재시작되는지를 "
                "함께 보십시오. 호스팅 업체가 발급한 인증서라면 관리 화면에서 자동 갱신 설정을 "
                "확인하십시오."
            ),
            reverification_ko=(
                "갱신 후 재수집해 만료일이 미래로 밀렸는지 확인합니다."
            ),
            business_impact_ko=(
                "만료되는 순간 방문자에게 보안 경고 화면이 뜨고 사이트가 열리지 않습니다. "
                "순위가 내려가는 정도가 아니라 예약·문의가 전부 끊깁니다."
            ),
            fix_example="sudo certbot renew --force-renewal && sudo systemctl reload nginx",
        )
    ]


__all__ = [
    "CERTIFICATE_ALARM_DAYS",
    "PROVIDER_CRUX",
    "PROVIDER_PAGESPEED",
    "RENEWAL_WINDOW_DAYS",
    "PerformanceUxCollector",
]
