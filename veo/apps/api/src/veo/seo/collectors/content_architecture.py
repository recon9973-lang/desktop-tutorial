"""콘텐츠·정보구조 — is there anything here, and can a reader get to it?

``seo.content.js_render_parity`` is the reason this module reads *both* views of every
page. The raw HTML is what a crawler receives; the rendered DOM is what a browser
displays. When the two disagree the crawler is indexing a different page from the one
customers see — and when no renderer ran, VEO says UNKNOWN rather than assuming they
agree, because assuming agreement is exactly how this fault stays hidden for a year.
"""

from __future__ import annotations

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.scoring import CheckOutcome, CheckStatus
from veo.seo.collectors.base import (
    HEURISTIC_HIGH,
    HEURISTIC_MEDIUM,
    NO_DOCUMENTS_KO,
    EvidenceLedger,
    SeoCollector,
    absent_in_sample_outcome,
    all_unknown,
    issue,
    single_page_outcome,
    unproven_absence_outcome,
    url_ratio_outcome,
)
from veo.seo.observation import PageObservation, SiteObservation
from veo.seo.parsing import content_length, depth_of, resolve, shingle_similarity

#: Observation thresholds. Each decides what VEO *reports*; none decides what it costs.
MIN_BODY_CHARS = 300
"""Non-whitespace characters of main content below which a key page reads as thin."""

NEAR_DUPLICATE_RATIO = 0.8
"""Shingle similarity at or above which two main bodies are near-duplicates."""

MAX_CLICK_DEPTH = 3
"""Clicks from the entry URL beyond which a key page is buried."""

DEEP_HIERARCHY_SEGMENTS = 2
"""Path segments at which a site is deep enough for breadcrumbs to be expected."""

RENDER_PARITY_RATIO = 0.6
"""Similarity between raw and rendered main content below which the two disagree."""


class ContentArchitectureCollector(SeoCollector):
    category_id = "content_architecture"
    check_id_list = (
        "seo.content.no_thin_signal",
        "seo.content.no_duplicate_bodies",
        "seo.content.click_depth_reasonable",
        "seo.content.internal_link_density",
        "seo.content.pagination_signals",
        "seo.content.breadcrumb_present",
        "seo.content.js_render_parity",
        "seo.content.lazy_loading_safe",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        site = self.observe(context)
        if not site.has_pages:
            return all_unknown(self.check_id_list, NO_DOCUMENTS_KO)

        ledger = EvidenceLedger()
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        for step in (
            _thin_content,
            _duplicate_bodies,
            _click_depth,
            _link_density,
            _pagination,
            _breadcrumb,
            _render_parity,
            _lazy_loading_safe,
        ):
            produced, produced_issues = step(context, site, ledger)
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


# --------------------------------------------------------------------------- #
# seo.content.no_thin_signal
# --------------------------------------------------------------------------- #


def _thin_content(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    candidates = list(site.key_pages)
    if not candidates:
        return (
            unknown_outcome(
                "seo.content.no_thin_signal",
                "본문을 평가할 주요 페이지가 수집되지 않았습니다.",
            ),
            [],
        )

    lengths = {page.url: content_length(page.raw.body_text) for page in candidates}
    thin = [page for page in candidates if lengths[page.url] < MIN_BODY_CHARS]
    evidence = [
        ledger.of(
            "text_extract",
            url=page.url,
            payload=page.raw.body_text,
            excerpt=page.raw.body_text[:300] or "(본문 없음)",
            detail={"characters": lengths[page.url]},
        )
        for page in (thin or candidates[:1])
    ]

    result = url_ratio_outcome(
        "seo.content.no_thin_signal",
        affected=thin,
        evaluated=candidates,
        evidence_ids=evidence,
        observed_value=lengths,
        clean_note_ko="주요 페이지의 본문 분량이 충분합니다.",
        affected_note_ko=f"{len(thin)}개 주요 페이지의 본문이 {MIN_BODY_CHARS}자에 못 미칩니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.no_thin_signal",
            title_ko="주요 페이지의 본문이 지나치게 짧습니다",
            summary_ko=(
                f"{len(thin)}개 주요 페이지의 본문이 공백을 뺀 {MIN_BODY_CHARS}자에 미치지 "
                "못합니다. 메뉴와 바닥글을 제외한 실제 내용 기준입니다."
            ),
            affected_urls=[page.url for page in thin],
            evidence_ids=evidence,
            remediation_ko=(
                "방문자가 그 페이지에서 실제로 알아야 하는 내용을 채우십시오. 절차, 준비물, "
                "소요 기간, 자주 나오는 질문처럼 답이 정해진 항목부터 적으면 분량이 자연히 "
                "붙습니다."
            ),
            reverification_ko="보강 후 재수집해 본문 글자 수가 기준을 넘는지 확인합니다.",
            business_impact_ko=(
                "내용이 얕은 페이지는 검색 결과에서 상위에 오르기 어렵고 문의로도 이어지지 "
                "않습니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.content.no_duplicate_bodies
# --------------------------------------------------------------------------- #


def _duplicate_bodies(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    candidates = [page for page in site.pages if page.raw.body_text.strip()]
    if len(site.pages) < 2:
        return (
            single_page_outcome(
                context,
                site,
                "seo.content.no_duplicate_bodies",
                subject_ko="페이지 간 본문 중복",
            ),
            [],
        )
    if len(candidates) < 2:
        # 여러 장을 봤는데 본문이 있는 페이지가 둘 미만이다. 이것은 수집 한계가 아니라
        # 이 사이트에 대한 관측이므로 해당 없음이 맞다.
        return (
            not_applicable_outcome(
                "seo.content.no_duplicate_bodies",
                "본문이 있는 페이지가 둘 미만이라 페이지 간 중복을 판단할 대상이 없습니다.",
            ),
            [],
        )

    pairs: list[tuple[str, str, float]] = []
    duplicated: set[str] = set()
    for index, left in enumerate(candidates):
        for right in candidates[index + 1 :]:
            ratio = shingle_similarity(left.raw.body_text, right.raw.body_text)
            if ratio >= NEAR_DUPLICATE_RATIO:
                pairs.append((left.url, right.url, round(ratio, 4)))
                duplicated.update({left.url, right.url})

    affected = [page for page in candidates if page.url in duplicated]
    if not affected:
        # 표본 안에서 겹치는 본문이 없었다 — 전체를 본 것이 아니면 부재는 미증명이다.
        guard = unproven_absence_outcome(
            context, site, "seo.content.no_duplicate_bodies",
            subject_ko="페이지 간 본문 근접 중복",
        )
        if guard is not None:
            return guard, []
    evidence = [
        ledger.of(
            "similarity_matrix",
            url=site.entry_url,
            payload="\n".join(f"{a} ~ {b}: {ratio}" for a, b, ratio in pairs) or "근접 중복 없음",
            excerpt="; ".join(f"{a} ~ {b} = {ratio}" for a, b, ratio in pairs[:5]),
            detail={"pairs": len(pairs), "compared": len(candidates)},
        )
    ]
    for page in affected[:4]:
        evidence.append(
            ledger.of(
                "text_extract",
                url=page.url,
                payload=page.raw.body_text,
                excerpt=page.raw.body_text[:300],
            )
        )

    result = url_ratio_outcome(
        "seo.content.no_duplicate_bodies",
        affected=affected,
        evaluated=candidates,
        confidence_level=HEURISTIC_HIGH,
        evidence_ids=evidence,
        observed_value=pairs or None,
        clean_note_ko="페이지 본문이 서로 충분히 다릅니다.",
        affected_note_ko=f"{len(pairs)}쌍의 페이지 본문이 근접 중복입니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.no_duplicate_bodies",
            title_ko="본문이 거의 같은 페이지가 있습니다",
            summary_ko=(
                f"{len(pairs)}쌍의 페이지가 본문 유사도 {NEAR_DUPLICATE_RATIO} 이상으로 "
                "겹칩니다. 메뉴와 바닥글을 제외한 본문 기준입니다."
            ),
            affected_urls=sorted(duplicated),
            evidence_ids=evidence,
            remediation_ko=(
                "한 페이지로 합치고 나머지는 합친 주소로 301 리다이렉트하거나, 남겨야 한다면 "
                "canonical로 대표 주소를 지정하십시오. 지역·항목별로 나눈 페이지라면 각 페이지에 "
                "그 지역·항목에서만 유효한 내용을 넣어 구분되게 만드십시오."
            ),
            reverification_ko="정리 후 재수집해 본문 유사도가 기준 아래로 내려갔는지 확인합니다.",
            business_impact_ko=(
                "같은 내용의 페이지끼리 노출 기회를 나눠 가져 어느 쪽도 상위에 오르지 못합니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.content.click_depth_reasonable
# --------------------------------------------------------------------------- #


def _click_depth(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    reachable = [page for page in site.key_pages if page.url in site.click_depth]
    if not reachable:
        return (
            unknown_outcome(
                "seo.content.click_depth_reasonable",
                "진입 URL에서 링크로 도달한 주요 페이지가 없어 클릭 깊이를 계산하지 못했습니다.",
            ),
            [],
        )

    depths = {page.url: site.click_depth[page.url] for page in reachable}
    buried = [page for page in reachable if depths[page.url] > MAX_CLICK_DEPTH]
    evidence = [
        ledger.of(
            "link_graph",
            url=site.entry_url,
            payload="\n".join(f"{url}: {depth}" for url, depth in sorted(depths.items())),
            excerpt=f"최대 클릭 깊이 {max(depths.values())}, 기준 {MAX_CLICK_DEPTH}",
            detail={"depths": depths},
        )
    ]

    result = url_ratio_outcome(
        "seo.content.click_depth_reasonable",
        affected=buried,
        evaluated=reachable,
        evidence_ids=evidence,
        observed_value=depths,
        clean_note_ko=f"주요 페이지가 모두 {MAX_CLICK_DEPTH}번 이내 클릭으로 도달 가능합니다.",
        affected_note_ko=(
            f"{len(buried)}개 주요 페이지가 {MAX_CLICK_DEPTH}번을 넘는 클릭 깊이에 있습니다."
        ),
        warning=True,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.click_depth_reasonable",
            title_ko="주요 페이지가 지나치게 깊이 묻혀 있습니다",
            summary_ko=(
                f"{len(buried)}개 주요 페이지에 도달하려면 진입 페이지에서 "
                f"{MAX_CLICK_DEPTH}번을 넘게 눌러야 합니다."
            ),
            affected_urls=[page.url for page in buried],
            evidence_ids=evidence,
            remediation_ko=(
                "주요 메뉴나 상위 허브 페이지에서 직접 링크를 추가해 경로를 줄이십시오. "
                "관련 문서 목록을 각 페이지 하단에 두는 것만으로도 깊이가 크게 줄어듭니다."
            ),
            reverification_ko="링크 추가 후 재수집해 클릭 깊이가 기준 이내인지 확인합니다.",
            business_impact_ko="깊이 묻힌 페이지는 크롤링 빈도가 낮아 갱신이 늦게 반영됩니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.content.internal_link_density
# --------------------------------------------------------------------------- #


def _link_density(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    candidates = list(site.key_pages)
    # 두 조건은 사유가 다르므로 나눠서 답한다. 페이지가 하나뿐인 것은 대개 **우리가**
    # 한 장만 봤다는 뜻이고, 주요 페이지가 없는 것은 이 사이트에 대한 관측이다.
    if len(site.pages) < 2:
        return (
            single_page_outcome(
                context,
                site,
                "seo.content.internal_link_density",
                subject_ko="내부 링크 밀도",
            ),
            [],
        )
    if not candidates:
        return (
            not_applicable_outcome(
                "seo.content.internal_link_density",
                "주요 페이지로 분류된 페이지가 없어 내부 링크를 판단할 대상이 없습니다.",
            ),
            [],
        )

    # A site cannot link to more pages than it has. Expecting two outbound links from a
    # two-page brochure would be reporting a fault that does not exist.
    expected = min(2, len(site.pages) - 1)
    counts = {page.url: len(site.outbound.get(page.url, ())) for page in candidates}
    sparse = [page for page in candidates if counts[page.url] < expected]

    evidence = [
        ledger.of(
            "link_graph",
            url=site.entry_url,
            payload="\n".join(f"{url}: {count}" for url, count in sorted(counts.items())),
            excerpt=f"페이지당 내부 링크 수, 기대치 {expected}",
            detail={"expected": expected, "counts": counts},
        )
    ]

    result = url_ratio_outcome(
        "seo.content.internal_link_density",
        affected=sparse,
        evaluated=candidates,
        evidence_ids=evidence,
        observed_value=counts,
        clean_note_ko="주요 페이지가 서로 충분히 연결되어 있습니다.",
        affected_note_ko=f"{len(sparse)}개 주요 페이지의 내부 링크가 {expected}개에 못 미칩니다.",
        warning=True,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.internal_link_density",
            title_ko="주제가 이어지는 내부 링크가 부족합니다",
            summary_ko=(
                f"{len(sparse)}개 주요 페이지에서 다른 페이지로 나가는 내부 링크가 "
                f"{expected}개에 미치지 못합니다."
            ),
            affected_urls=[page.url for page in sparse],
            evidence_ids=evidence,
            remediation_ko=(
                "본문에서 자연스럽게 이어지는 문서를 문맥 안에서 링크하십시오. 절차 안내에서 "
                "준비물 문서로, 시술 안내에서 예약 문서로 잇는 식이면 충분합니다."
            ),
            reverification_ko="링크 추가 후 재수집해 페이지당 내부 링크 수를 다시 셉니다.",
            business_impact_ko=(
                "주제 묶음이 약해져 관련 검색어에서 사이트 전체의 평가가 낮아집니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.content.pagination_signals
# --------------------------------------------------------------------------- #


def _pagination(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    paginated = [page for page in site.pages if page.raw.rel_next or page.raw.rel_prev]
    if not paginated:
        return (
            not_applicable_outcome(
                "seo.content.pagination_signals",
                "페이지네이션 표시가 없는 사이트라 해당하지 않습니다.",
            ),
            [],
        )

    problems: dict[str, str] = {}
    for page in paginated:
        canonical = resolve(page.url, page.raw.canonical or "") if page.raw.canonical else None
        if canonical is not None and canonical != page.url:
            problems[page.url] = f"canonical이 자기 자신이 아닌 {canonical}을 가리킵니다"
            continue
        if page.raw.canonical is None:
            problems[page.url] = "canonical이 선언되지 않았습니다"
            continue
        for relation, href in (("next", page.raw.rel_next), ("prev", page.raw.rel_prev)):
            if not href:
                continue
            target = resolve(page.url, href)
            if target is None:
                problems[page.url] = f"rel={relation} 주소를 해석할 수 없습니다"
                break
            neighbour = site.page(target)
            if neighbour is not None and not neighbour.is_ok:
                problems[page.url] = f"rel={relation} 대상이 {neighbour.status}로 응답합니다"
                break

    affected = [page for page in paginated if page.url in problems]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            f'rel=next: {page.raw.rel_next} / rel=prev: {page.raw.rel_prev} / '
            f"canonical: {page.raw.canonical}",
        )
        for page in (affected or paginated[:1])
    ]

    result = url_ratio_outcome(
        "seo.content.pagination_signals",
        affected=affected,
        evaluated=paginated,
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko=(
            "페이지네이션 각 쪽이 자기 자신을 canonical로 선언하고 이웃 쪽이 정상 응답합니다."
        ),
        affected_note_ko=f"{len(affected)}개 페이지네이션 URL의 신호가 어긋납니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.pagination_signals",
            title_ko="페이지네이션 신호가 어긋납니다",
            summary_ko="; ".join(f"{url} — {reason}" for url, reason in list(problems.items())[:5]),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                "2쪽 이후의 목록 페이지도 자기 자신을 canonical로 선언해야 합니다. 1쪽으로 "
                "canonical을 몰아 두면 2쪽 이후에만 있는 항목이 색인에서 사라집니다."
            ),
            reverification_ko="수정 후 각 쪽의 canonical과 rel 링크를 재수집해 확인합니다.",
            business_impact_ko="목록 뒤쪽에만 있는 상품이나 글이 검색에서 아예 사라집니다.",
            fix_example='<link rel="canonical" href="https://example.kr/list/page/2/">',
        )
    ]


# --------------------------------------------------------------------------- #
# seo.content.breadcrumb_present
# --------------------------------------------------------------------------- #


def _breadcrumb(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    deep = [page for page in site.pages if depth_of(page.url) >= DEEP_HIERARCHY_SEGMENTS]
    if not deep:
        return (
            absent_in_sample_outcome(
                context,
                site,
                "seo.content.breadcrumb_present",
                absent_ko=(
                    f"모든 URL이 경로 {DEEP_HIERARCHY_SEGMENTS}단계 미만이라 breadcrumb이 "
                    "필요한 깊이가 아닙니다."
                ),
                subject_ko=f"경로 {DEEP_HIERARCHY_SEGMENTS}단계 이상인 페이지",
            ),
            [],
        )

    missing = [page for page in deep if not _has_breadcrumb(page)]
    missing_urls = {page.url for page in missing}
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            "breadcrumb 표시 없음" if page.url in missing_urls else "breadcrumb 표시 확인",
        )
        for page in (missing or deep[:1])
    ]

    result = url_ratio_outcome(
        "seo.content.breadcrumb_present",
        affected=missing,
        evaluated=deep,
        confidence_level=HEURISTIC_HIGH,
        evidence_ids=evidence,
        observed_value={page.url: page.url not in missing_urls for page in deep},
        clean_note_ko="계층이 깊은 페이지에 breadcrumb이 제공됩니다.",
        affected_note_ko=f"{len(missing)}개 하위 페이지에 breadcrumb이 없습니다.",
        warning=True,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.breadcrumb_present",
            title_ko="하위 페이지에 breadcrumb이 없습니다",
            summary_ko=(
                f"경로가 {DEEP_HIERARCHY_SEGMENTS}단계 이상인 {len(deep)}개 페이지 가운데 "
                f"{len(missing)}개에 상위 경로를 보여 주는 breadcrumb이 없습니다."
            ),
            affected_urls=[page.url for page in missing],
            evidence_ids=evidence,
            remediation_ko=(
                "본문 위에 상위 경로를 순서대로 보여 주는 breadcrumb을 넣고, 같은 내용을 "
                "BreadcrumbList 구조화 데이터로도 선언하십시오."
            ),
            reverification_ko="추가 후 재수집해 breadcrumb 표시와 구조화 데이터를 함께 확인합니다.",
            business_impact_ko=(
                "검색 결과에 경로가 표시되지 않아 어떤 분류의 문서인지 전달되지 않습니다."
            ),
        )
    ]


def _has_breadcrumb(page: PageObservation) -> bool:
    if page.raw.has_breadcrumb:
        return True
    return any("breadcrumblist" in block.lower() for block in page.raw.json_ld_blocks)


# --------------------------------------------------------------------------- #
# seo.content.js_render_parity
# --------------------------------------------------------------------------- #


def _render_parity(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    rendered = [page for page in site.pages if page.rendered is not None]
    if not rendered:
        return (
            unknown_outcome(
                "seo.content.js_render_parity",
                "렌더러가 실행되지 않아 원본 HTML과 렌더링 DOM을 비교하지 못했습니다. "
                "일치한다고 가정하지 않습니다.",
            ),
            [],
        )

    diverging: list[PageObservation] = []
    detail: dict[str, object] = {}

    for page in rendered:
        assert page.rendered is not None
        ratio = shingle_similarity(page.raw.body_text, page.rendered.body_text)
        raw_length = content_length(page.raw.body_text)
        rendered_length = content_length(page.rendered.body_text)
        title_changed = (page.raw.title or "") != (page.rendered.title or "")
        detail[page.url] = {
            "similarity": round(ratio, 4),
            "raw_characters": raw_length,
            "rendered_characters": rendered_length,
            "title_changed": title_changed,
        }
        if ratio < RENDER_PARITY_RATIO or title_changed:
            diverging.append(page)

    evidence: list[str] = []
    for page in diverging or rendered[:1]:
        assert page.rendered is not None
        evidence.append(
            ledger.of(
                "raw_html",
                url=page.url,
                payload=page.document.body or b"",
                excerpt=page.raw.body_text[:300] or "(원본 HTML에 본문 없음)",
                detail={"characters": content_length(page.raw.body_text)},
            )
        )
        evidence.append(
            ledger.of(
                "rendered_dom",
                url=page.url,
                payload=page.rendered.body_text,
                excerpt=page.rendered.body_text[:300],
                detail={"characters": content_length(page.rendered.body_text)},
            )
        )

    result = url_ratio_outcome(
        "seo.content.js_render_parity",
        affected=diverging,
        evaluated=rendered,
        confidence_level=HEURISTIC_MEDIUM,
        evidence_ids=evidence,
        observed_value=detail,
        clean_note_ko="원본 HTML과 렌더링 DOM의 핵심 콘텐츠가 일치합니다.",
        affected_note_ko=f"{len(diverging)}개 URL에서 원본 HTML과 렌더링 DOM이 크게 다릅니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.js_render_parity",
            title_ko="크롤러가 받는 HTML과 브라우저가 보여 주는 화면이 다릅니다",
            summary_ko=(
                f"{len(diverging)}개 URL에서 원본 HTML의 본문이 렌더링 결과와 크게 다릅니다. "
                "자바스크립트 실행 전에는 핵심 내용이 비어 있다는 뜻입니다."
            ),
            affected_urls=[page.url for page in diverging],
            evidence_ids=evidence,
            remediation_ko=(
                "핵심 본문과 제목을 서버에서 미리 렌더링해 첫 응답 HTML에 담으십시오. "
                "서버 렌더링이 어렵다면 최소한 제목, 본문 요약, 주요 링크만이라도 정적으로 "
                "출력해야 합니다."
            ),
            reverification_ko=(
                "배포 후 자바스크립트를 끈 상태의 원본 HTML을 다시 받아 본문이 담겨 있는지 "
                "확인합니다."
            ),
            business_impact_ko=(
                "크롤러가 빈 화면을 색인하면 페이지 내용 전체가 검색에서 사라집니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.content.lazy_loading_safe
# --------------------------------------------------------------------------- #

#: 첫 화면에 들어온다고 볼 이미지의 개수. 레이아웃을 계산하지 않으므로 정확한 접힘선은
#: 알 수 없고, **문서 순서상 맨 앞** 을 대신 쓴다. 그래서 판정 신뢰도를 직접 관측이
#: 아닌 휴리스틱으로 낮춰 기록한다.
#:
#: 하나로 잡은 이유: 첫 이미지는 대개 LCP 대상이라 거의 확실히 접힘선 위지만, 두 번째
#: 부터는 화면 크기와 배치에 따라 갈린다. 넓게 잡으면 제대로 만든 사이트를 지적하게
#: 되고, 그런 지적이 몇 번 반복되면 보고서 전체를 믿지 않게 된다.
ABOVE_FOLD_IMAGES = 1


def _lazy_loading_safe(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    """지연 로딩은 속도 기법이 아니라 **색인 위험**이다.

    구글은 잘못 구현한 지연 로딩이 "콘텐츠를 검색에서 숨길 수 있다" 고 명시한다. 여기서
    보는 것은 두 가지다:

    * 첫 화면 이미지에 `loading="lazy"` 가 걸린 경우 — LCP 가 늦어지고, 대표 이미지가
      검색 결과의 미리보기로 뽑히지 않을 수 있다.
    * 본문을 담은 iframe 에 지연 로딩이 걸린 경우 — 크롤러는 스크롤하지 않으므로 그
      안의 내용을 보지 못할 수 있다.

    지연 로딩을 아예 쓰지 않는 페이지는 이 검사의 대상이 아니다. 안 쓰는 것이 결함은
    아니므로 해당 없음으로 둔다.
    """
    users = [
        page
        for page in site.pages
        if page.raw.lazy_iframes or any(img.loading == "lazy" for img in page.raw.images)
    ]
    if not users:
        return (
            absent_in_sample_outcome(
                context,
                site,
                "seo.content.lazy_loading_safe",
                absent_ko="지연 로딩을 사용하는 페이지가 없어 해당하지 않습니다.",
                subject_ko="지연 로딩을 사용하는 페이지",
            ),
            [],
        )

    problems: dict[str, str] = {}
    for page in users:
        reasons: list[str] = []
        early = [
            img
            for img in page.raw.images
            if img.loading == "lazy" and img.order < ABOVE_FOLD_IMAGES
        ]
        if early:
            reasons.append(
                f"첫 화면에 올 이미지 {len(early)}개에 loading=\"lazy\" 가 걸려 있습니다"
            )
        if page.raw.lazy_iframes:
            reasons.append(
                f"iframe {page.raw.lazy_iframes}개가 지연 로딩되어 내용이 색인되지 "
                "않을 수 있습니다"
            )
        if reasons:
            problems[page.url] = " / ".join(reasons)

    affected = [page for page in users if page.url in problems]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            " / ".join(
                f'<img src="{img.src}" loading="{img.loading}">'
                for img in page.raw.images[:3]
                if img.loading
            )
            or f"lazy iframe {page.raw.lazy_iframes}개",
        )
        for page in (affected or users[:1])
    ]

    result = url_ratio_outcome(
        "seo.content.lazy_loading_safe",
        affected=affected,
        evaluated=users,
        confidence_level=HEURISTIC_MEDIUM,
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko=(
            f"지연 로딩을 쓰는 {len(users)}개 페이지 모두, 첫 화면 이미지와 본문 iframe 은 "
            "지연 로딩 대상이 아닙니다."
        ),
        affected_note_ko=(
            f"{len(affected)}개 페이지의 지연 로딩이 콘텐츠를 숨길 수 있습니다."
        ),
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.content.lazy_loading_safe",
            title_ko="지연 로딩이 콘텐츠를 숨길 수 있습니다",
            summary_ko="; ".join(f"{url} — {why}" for url, why in list(problems.items())[:5]),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                "첫 화면에 보이는 이미지에서는 loading=\"lazy\" 를 빼고 loading=\"eager\" "
                "를 쓰십시오. 본문을 담은 iframe 은 지연 로딩 대신 그대로 두거나, 내용을 "
                "HTML 로 옮겨 크롤러가 스크롤 없이 읽을 수 있게 하십시오."
            ),
            reverification_ko=(
                "수정 후 재수집해 첫 이미지에 lazy 가 없고 본문 iframe 이 즉시 로딩되는지 "
                "확인합니다."
            ),
            business_impact_ko=(
                "대표 이미지가 검색 결과 미리보기로 뽑히지 않고, iframe 안의 진료 안내가 "
                "색인에서 빠질 수 있습니다."
            ),
            fix_example='<img src="/hero.webp" alt="진료실" loading="eager" fetchpriority="high">',
        )
    ]


__all__ = [
    "ABOVE_FOLD_IMAGES",
    "DEEP_HIERARCHY_SEGMENTS",
    "MAX_CLICK_DEPTH",
    "MIN_BODY_CHARS",
    "NEAR_DUPLICATE_RATIO",
    "RENDER_PARITY_RATIO",
    "ContentArchitectureCollector",
]
