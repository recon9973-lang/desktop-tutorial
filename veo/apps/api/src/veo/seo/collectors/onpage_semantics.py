"""온페이지 시맨틱 — what the page says about itself, in the raw HTML.

Deliberately read from :attr:`PageObservation.raw`, not from the rendered DOM. A title
injected by JavaScript after load is a title the crawler may never see, and reporting it
as present would hide the very problem the customer needs to know about.
"""

from __future__ import annotations

from collections import defaultdict

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
    NO_DOCUMENTS_KO,
    EvidenceLedger,
    SeoCollector,
    all_unknown,
    issue,
    outcome,
    url_ratio_outcome,
)
from veo.seo.observation import SiteObservation
from veo.seo.parsing import normalise, resolve, same_site

#: Observation bounds for a meta description, taken from what search engines display.
#: They decide what VEO reports, never how much a finding costs.
MIN_DESCRIPTION_CHARS = 40
MAX_DESCRIPTION_CHARS = 200

#: Anchor text that tells a reader — and a search engine — nothing about the target.
_VAGUE_EXACT = frozenset(
    {
        "여기",
        "클릭",
        "이곳",
        "더보기",
        "더 보기",
        "자세히",
        "자세히 보기",
        "바로가기",
        "바로 가기",
        "링크",
        "here",
        "click here",
        "read more",
        "learn more",
        "more",
        "link",
        "this page",
    }
)
_VAGUE_CONTAINS = ("클릭", "여기를", "이곳을", "바로가기", "더보기")


class OnpageSemanticsCollector(SeoCollector):
    category_id = "onpage_semantics"
    check_id_list = (
        "seo.onpage.title_present_and_unique",
        "seo.onpage.meta_description_quality",
        "seo.onpage.single_meaningful_h1",
        "seo.onpage.heading_hierarchy",
        "seo.onpage.html_lang_declared",
        "seo.onpage.image_alt_coverage",
        "seo.onpage.descriptive_anchor_text",
        "seo.onpage.no_duplicate_metadata",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        site = self.observe(context)
        if not site.has_pages:
            return all_unknown(self.check_id_list, NO_DOCUMENTS_KO)

        ledger = EvidenceLedger()
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        for step in (
            _title,
            _meta_description,
            _single_h1,
            _heading_hierarchy,
            _html_lang,
            _image_alt,
            _anchor_text,
            _duplicate_metadata,
        ):
            produced, produced_issues = step(context, site, ledger)
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


def _duplicates(values: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for url, value in values.items():
        grouped[normalise(value)].append(url)
    return {value: urls for value, urls in grouped.items() if len(urls) > 1 and value}


# --------------------------------------------------------------------------- #
# seo.onpage.title_present_and_unique
# --------------------------------------------------------------------------- #


def _title(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    titles = {page.url: (page.raw.title or "").strip() for page in site.pages}
    repeated = _duplicates({url: title for url, title in titles.items() if title})
    repeated_urls = {url for urls in repeated.values() for url in urls}

    affected = [
        page for page in site.pages if not titles[page.url] or page.url in repeated_urls
    ]
    evidence = [
        ledger.page_snippet(page, "dom_snippet", f"<title>{titles[page.url]}</title>")
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.title_present_and_unique",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=titles,
        clean_note_ko="모든 페이지에 서로 다른 title이 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지의 title이 비어 있거나 다른 페이지와 같습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    missing = [page.url for page in affected if not titles[page.url]]
    return result, [
        issue(
            context,
            "seo.onpage.title_present_and_unique",
            title_ko="title이 비어 있거나 페이지끼리 중복됩니다",
            summary_ko=(
                f"title이 없는 페이지 {len(missing)}개, 다른 페이지와 같은 title을 쓰는 페이지 "
                f"{len(repeated_urls)}개가 확인되었습니다."
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=(
                "페이지마다 그 페이지에서만 쓰는 title을 작성하십시오. 핵심 주제를 앞에, "
                "브랜드명을 뒤에 두면 검색 결과에서 잘리더라도 주제가 남습니다."
            ),
            reverification_ko="수정 후 재수집해 title이 모두 채워지고 서로 다른지 확인합니다.",
            business_impact_ko="검색 결과에 표시되는 첫 줄이므로 클릭률에 직접 영향을 줍니다.",
            fix_example="<title>레이저 치료 안내 — 회복 기간과 주의 사항 | 온담의원</title>",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.meta_description_quality
# --------------------------------------------------------------------------- #


def _meta_description(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    descriptions = {page.url: (page.raw.meta_description or "").strip() for page in site.pages}
    repeated = _duplicates({url: value for url, value in descriptions.items() if value})
    repeated_urls = {url for urls in repeated.values() for url in urls}

    problems: dict[str, str] = {}
    for page in site.pages:
        value = descriptions[page.url]
        if not value:
            problems[page.url] = "description이 없습니다"
        elif len(value) < MIN_DESCRIPTION_CHARS:
            problems[page.url] = f"{len(value)}자로 너무 짧습니다"
        elif len(value) > MAX_DESCRIPTION_CHARS:
            problems[page.url] = f"{len(value)}자로 너무 깁니다"
        elif page.url in repeated_urls:
            problems[page.url] = "다른 페이지와 같은 description입니다"

    affected = [page for page in site.pages if page.url in problems]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            f'<meta name="description" content="{descriptions[page.url][:120]}">',
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.meta_description_quality",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko="모든 페이지의 meta description이 적절한 길이로 채워져 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지의 meta description에 문제가 있습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.onpage.meta_description_quality",
            title_ko="meta description이 비어 있거나 길이·중복 문제가 있습니다",
            summary_ko="; ".join(f"{url} — {reason}" for url, reason in list(problems.items())[:5]),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                f"페이지마다 {MIN_DESCRIPTION_CHARS}자에서 {MAX_DESCRIPTION_CHARS}자 사이의 "
                "고유한 설명을 작성하십시오. 페이지에서 얻을 수 있는 정보를 한 문장으로 "
                "요약하면 충분합니다."
            ),
            reverification_ko="수정 후 재수집해 길이와 중복 여부를 다시 확인합니다.",
            business_impact_ko=(
                "검색 결과의 설명문이 자동 생성되면 의도와 다른 문장이 노출될 수 있습니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.single_meaningful_h1
# --------------------------------------------------------------------------- #


def _single_h1(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    problems: dict[str, str] = {}
    for page in site.pages:
        h1s = [text for level, text in page.raw.headings if level == 1 and text.strip()]
        if not h1s:
            problems[page.url] = "의미 있는 H1이 없습니다"
        elif len(h1s) > 1:
            problems[page.url] = f"H1이 {len(h1s)}개 있습니다"

    affected = [page for page in site.pages if page.url in problems]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            " / ".join(f"h{level}: {text}" for level, text in page.raw.headings[:6]),
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.single_meaningful_h1",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko="모든 페이지에 의미 있는 H1이 하나씩 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지의 H1 구성에 문제가 있습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.onpage.single_meaningful_h1",
            title_ko="H1이 없거나 여러 개입니다",
            summary_ko="; ".join(f"{url} — {reason}" for url, reason in list(problems.items())[:5]),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                "페이지의 주제를 담은 H1을 하나만 두고, 나머지 제목은 H2 이하로 내리십시오. "
                "로고나 사이트명은 H1이 아니라 이미지나 링크로 표시하는 편이 맞습니다."
            ),
            reverification_ko="수정 후 재수집해 H1 개수가 하나인지 확인합니다.",
            business_impact_ko="주제를 알리는 가장 강한 신호이므로 본문 이해도에 영향을 줍니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.heading_hierarchy
# --------------------------------------------------------------------------- #


def _heading_hierarchy(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    problems: dict[str, str] = {}
    for page in site.pages:
        levels = [level for level, text in page.raw.headings if text.strip()]
        if not levels:
            problems[page.url] = "제목 요소가 없습니다"
            continue
        previous = levels[0]
        for level in levels[1:]:
            if level > previous + 1:
                problems[page.url] = f"H{previous} 다음에 H{level}이 나옵니다"
                break
            previous = level

    affected = [page for page in site.pages if page.url in problems]
    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            " > ".join(f"h{level}" for level, _ in page.raw.headings),
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.heading_hierarchy",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko="제목 단계가 건너뛰는 곳 없이 이어집니다.",
        affected_note_ko=f"{len(affected)}개 페이지에서 제목 단계가 건너뜁니다.",
        warning=True,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    return result, [
        issue(
            context,
            "seo.onpage.heading_hierarchy",
            title_ko="제목 단계가 건너뜁니다",
            summary_ko="; ".join(f"{url} — {reason}" for url, reason in list(problems.items())[:5]),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                "제목은 H1 다음 H2, H2 다음 H3 순으로 한 단계씩 내려가도록 정리하십시오. "
                "글자 크기를 맞추려고 단계를 건너뛴 경우라면 스타일로 해결하는 편이 맞습니다."
            ),
            reverification_ko="수정 후 재수집해 제목 단계가 순서대로인지 확인합니다.",
            business_impact_ko="본문 구조가 흐려져 발췌 문단이 엉뚱하게 잡힐 수 있습니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.html_lang_declared
# --------------------------------------------------------------------------- #


def _html_lang(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    missing = [page for page in site.pages if not (page.raw.lang or "").strip()]
    evidence = [
        ledger.page_snippet(page, "dom_snippet", f'<html lang="{page.raw.lang or ""}">')
        for page in (missing or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.html_lang_declared",
        affected=missing,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value={page.url: page.raw.lang for page in site.pages},
        clean_note_ko="모든 페이지에 html lang 속성이 선언되어 있습니다.",
        affected_note_ko=f"{len(missing)}개 페이지에 html lang 속성이 없습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.onpage.html_lang_declared",
            title_ko="html lang 속성이 선언되지 않았습니다",
            summary_ko=f"{len(missing)}개 페이지의 html 요소에 lang 속성이 없습니다.",
            affected_urls=[page.url for page in missing],
            evidence_ids=evidence,
            remediation_ko='html 여는 태그에 `<html lang="ko">`처럼 문서 언어를 선언하십시오.',
            reverification_ko="수정 후 재수집해 lang 속성이 있는지 확인합니다.",
            business_impact_ko=(
                "언어가 명시되지 않으면 지역·언어별 검색 결과에서 불리하게 처리될 수 있습니다."
            ),
            fix_example='<html lang="ko">',
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.image_alt_coverage
# --------------------------------------------------------------------------- #


def _image_alt(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    with_images = [page for page in site.pages if page.raw.images]
    if not with_images:
        return (
            not_applicable_outcome(
                "seo.onpage.image_alt_coverage",
                "수집한 페이지에 이미지가 없어 대체 텍스트를 평가할 대상이 없습니다.",
            ),
            [],
        )

    # ``alt=""`` marks a decorative image and is correct. Only a missing attribute counts.
    problems = {
        page.url: [image.src for image in page.raw.images if image.alt is None]
        for page in with_images
    }
    affected = [page for page in with_images if problems[page.url]]
    evidence = [
        ledger.page_snippet(
            page, "dom_snippet", "alt 없는 이미지: " + ", ".join(problems[page.url][:5])
        )
        for page in (affected or with_images[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.image_alt_coverage",
        affected=affected,
        evaluated=with_images,
        evidence_ids=evidence,
        observed_value={url: srcs for url, srcs in problems.items() if srcs} or None,
        clean_note_ko="의미 있는 이미지에 모두 alt 속성이 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지에 alt 속성이 없는 이미지가 있습니다.",
        warning=True,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    total = sum(len(srcs) for srcs in problems.values())
    return result, [
        issue(
            context,
            "seo.onpage.image_alt_coverage",
            title_ko="alt 속성이 없는 이미지가 있습니다",
            summary_ko=(
                f"{len(affected)}개 페이지에서 이미지 {total}개에 alt 속성이 아예 없습니다. "
                '장식용 이미지라면 `alt=""`로 비워 두는 것이 올바른 표기입니다.'
            ),
            affected_urls=[page.url for page in affected],
            evidence_ids=evidence,
            remediation_ko=(
                "내용을 전달하는 이미지에는 무엇이 담겼는지 설명하는 alt를 넣고, 장식용 이미지에는 "
                '`alt=""`를 넣어 의도적으로 비웠음을 표시하십시오.'
            ),
            reverification_ko="수정 후 재수집해 alt 속성이 빠진 이미지가 없는지 확인합니다.",
            business_impact_ko=(
                "이미지 검색 유입이 줄고 화면 낭독기 사용자가 내용을 알 수 없습니다."
            ),
            fix_example='<img src="/img/clinic.jpg" alt="온담의원 1층 접수 데스크">',
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.descriptive_anchor_text
# --------------------------------------------------------------------------- #


def _anchor_text(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    total = 0
    vague: list[tuple[str, str]] = []

    for page in site.pages:
        for anchor in page.raw.links:
            target = resolve(page.url, anchor.href)
            if target is None or not same_site(page.url, target):
                continue
            total += 1
            text = normalise(anchor.accessible_text)
            if not text or text in _VAGUE_EXACT or any(w in text for w in _VAGUE_CONTAINS):
                vague.append((page.url, anchor.accessible_text or "(텍스트 없음)"))

    if total == 0:
        return (
            unknown_outcome(
                "seo.onpage.descriptive_anchor_text",
                "수집 범위 안에 내부 링크가 없어 앵커 텍스트를 평가하지 못했습니다.",
            ),
            [],
        )

    evidence = [
        ledger.of(
            "link_graph",
            url=site.entry_url,
            payload=(
                "\n".join(f"{url}: {text}" for url, text in vague)
                or "설명적이지 않은 앵커 없음"
            ),
            excerpt="; ".join(f"{url} — “{text}”" for url, text in vague[:5]),
            detail={"vague": len(vague), "total": total},
        )
    ]

    result = outcome(
        "seo.onpage.descriptive_anchor_text",
        CheckStatus.PASS if not vague else CheckStatus.WARNING,
        confidence_level=HEURISTIC_HIGH,
        affected=float(len(vague)),
        evaluated=float(total),
        evidence_ids=evidence,
        observed_value=[text for _, text in vague] or None,
        note=(
            f"내부 링크 {total}개의 앵커 텍스트가 모두 목적지를 설명합니다."
            if not vague
            else (
                f"내부 링크 {total}개 가운데 {len(vague)}개의 앵커 텍스트가 "
                "목적지를 설명하지 않습니다."
            )
        ),
    )
    if not vague:
        return result, []

    return result, [
        issue(
            context,
            "seo.onpage.descriptive_anchor_text",
            title_ko="앵커 텍스트가 목적지를 설명하지 않습니다",
            summary_ko=(
                f"“여기”, “클릭”, “더보기”처럼 목적지를 알 수 없는 링크 문구가 {len(vague)}개 "
                f"확인되었습니다(전체 내부 링크 {total}개)."
            ),
            affected_urls=sorted({url for url, _ in vague}),
            evidence_ids=evidence,
            remediation_ko=(
                "링크 문구를 목적지 페이지의 주제로 바꾸십시오. “자세히 보기” 대신 "
                "“레이저 치료 회복 기간 보기”처럼 무엇을 볼 수 있는지 드러내면 됩니다."
            ),
            reverification_ko="수정 후 재수집해 모호한 문구가 남아 있는지 확인합니다.",
            business_impact_ko=(
                "링크 문구는 대상 페이지의 주제를 알리는 신호이므로 그대로 두면 평가가 흐려집니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.onpage.no_duplicate_metadata
# --------------------------------------------------------------------------- #


def _duplicate_metadata(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    if len(site.pages) < 2:
        return (
            not_applicable_outcome(
                "seo.onpage.no_duplicate_metadata",
                "수집한 페이지가 하나뿐이어서 페이지 간 중복을 판단할 수 없습니다.",
            ),
            [],
        )

    titles = _duplicates(
        {page.url: page.raw.title or "" for page in site.pages if (page.raw.title or "").strip()}
    )
    descriptions = _duplicates(
        {
            page.url: page.raw.meta_description or ""
            for page in site.pages
            if (page.raw.meta_description or "").strip()
        }
    )

    affected_urls = {url for urls in titles.values() for url in urls} | {
        url for urls in descriptions.values() for url in urls
    }
    affected = [page for page in site.pages if page.url in affected_urls]

    evidence = [
        ledger.page_snippet(
            page,
            "dom_snippet",
            f"<title>{page.raw.title}</title> / description: {page.raw.meta_description}",
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.onpage.no_duplicate_metadata",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value={"titles": titles, "descriptions": descriptions} if affected else None,
        clean_note_ko="페이지 간 title과 description 중복이 없습니다.",
        affected_note_ko=(
            f"title {len(titles)}건, description {len(descriptions)}건이 여러 페이지에 걸쳐 "
            f"중복됩니다."
        ),
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.onpage.no_duplicate_metadata",
            title_ko="여러 페이지가 같은 title·description을 씁니다",
            summary_ko=(
                f"동일한 title을 쓰는 묶음 {len(titles)}건, 동일한 description을 쓰는 묶음 "
                f"{len(descriptions)}건이 확인되었습니다. 검색엔진이 페이지를 서로 구분하기 "
                "어려워집니다."
            ),
            affected_urls=sorted(affected_urls),
            evidence_ids=evidence,
            remediation_ko=(
                "템플릿에서 고정 문구를 넣는 대신 페이지별 제목과 요약을 값으로 받아 출력하십시오. "
                "목록 페이지라면 분류명과 페이지 번호를 제목에 포함하면 구분됩니다."
            ),
            reverification_ko="템플릿 수정 후 재수집해 중복 묶음이 사라졌는지 확인합니다.",
            business_impact_ko=(
                "유사한 페이지끼리 검색 노출을 나눠 가져 어느 쪽도 제대로 노출되지 않습니다."
            ),
        )
    ]


__all__ = [
    "MAX_DESCRIPTION_CHARS",
    "MIN_DESCRIPTION_CHARS",
    "OnpageSemanticsCollector",
]
