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
        "seo.perf.text_compression",
        "seo.perf.modern_image_format",
        "seo.perf.resource_hints",
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


__all__ = ["PROVIDER_CRUX", "PROVIDER_PAGESPEED", "PerformanceUxCollector"]
