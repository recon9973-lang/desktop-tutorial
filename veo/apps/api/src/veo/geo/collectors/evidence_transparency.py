"""근거·출처 투명성 — can a reader check what this page asserts.

The hard part is deciding what counts as a claim that *needs* checking. A page that says
"we opened in 2016" is stating a fact about itself; a page that says "conversion rose 37%
and the average spend is 420,000 KRW" is asserting something a reader cannot verify
without help. Only the second kind is asked for a source here, which is why a corporate
About page comes out NOT_APPLICABLE rather than failing.

The opening summary is deliberately exempt. A lead paragraph restates what the sections
below it prove; demanding a source inside the summary would push writers to clutter the
one passage most likely to be quoted.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    not_applicable_outcome,
)
from veo.geo.extractability import (
    QUANTITY_PATTERN,
    ExtractionSignals,
    analyse_extractability,
)
from veo.geo.pagekind import visible_addresses
from veo.geo.parsing import PageDocument, TextBlock
from veo.geo.reporting import LOW, MEDIUM, finding, observed, snippet_evidence
from veo.geo.view import TargetView, build_view
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.evidence.claims_have_sources",
        "geo.evidence.author_identified",
        "geo.evidence.publisher_identified",
        "geo.evidence.method_disclosed",
        "geo.evidence.primary_source_linked",
    }
)

#: Wording that hands a reader something to check.
SOURCE_MARKERS = (
    "출처", "자료", "근거", "인용", "참고", "따랐", "확인했", "공고", "지침",
    "보고서", "논문", "고지", "according to", "source:", "cited",
)

#: Wording that says how a figure was produced, rather than merely repeating it.
METHOD_MARKERS = (
    "산출", "집계", "측정", "표본", "계산", "방법은", "방식입니다", "기준으로",
    "포함한 금액", "부가세", "methodology", "measured", "sample size",
)

SUPERLATIVES = ("1위", "최고", "최초", "최대", "유일", "가장 ", "업계 최", "no.1", "no. 1")

AUTHOR_MARKERS = ("감수", "작성자", "글 ", "글:", "기자", "취재", "reviewed by", "written by")

#: Hosts that publish the thing itself rather than a retelling of it.
PRIMARY_SOURCE_MARKERS = (
    ".go.kr", ".gov", ".edu", ".ac.kr", ".or.kr", ".int", "doi.org", "who.int",
    "oecd.org", "europa.eu", "arxiv.org", "pubmed",
)

#: Hosts that are almost always someone repeating a source rather than being one.
SECOND_HAND_MARKERS = (
    "blog.naver.com", "cafe.naver.com", "tistory.com", "brunch.co.kr", "medium.com",
    "namu.wiki", "post.naver.com", "velog.io",
)

_REGISTRATION_PATTERN = re.compile(r"(사업자등록번호|통신판매업|등록번호|법인등록)")
_COPYRIGHT_PATTERN = re.compile(r"©\s*(?:\d{4}\s*)?([^·|\n]{2,40})")

_SOURCED_SHARE_GOOD = 0.5


class EvidenceTransparencyCollector:
    """Observes whether assertions on the page can be traced anywhere."""

    category_id = "evidence_transparency"

    @property
    def check_ids(self) -> frozenset[str]:
        return CHECK_IDS

    def collect(self, context: CollectionContext) -> CollectionResult:
        view = build_view(context)
        page = view.page
        signals = analyse_extractability(page)
        host = urlparse(view.url).netloc
        evidence: list[EvidenceRecord] = list(view.evidence)
        issues: list[IssueDraft] = []
        outcomes: list[CheckOutcome] = []
        base = view.evidence_ids

        answer_text = signals.direct_answer.text if signals.direct_answer else ""
        claims = _claim_passages(page, answer_text)
        sourced, unsourced = _split_by_source(page, claims, host)

        # -- claims and their sources ------------------------------------ #
        if not claims:
            outcomes.append(
                not_applicable_outcome(
                    "geo.evidence.claims_have_sources",
                    "검증이 필요한 수치·비교 주장이 없는 페이지입니다.",
                    evidence_ids=base,
                )
            )
        else:
            share = len(sourced) / len(claims)
            value = {"claims": len(claims), "sourced": len(sourced)}
            if share >= _SOURCED_SHARE_GOOD:
                status, note = CheckStatus.PASS, "주요 주장에 출처나 산출 근거가 연결되어 있습니다."
            elif sourced:
                status, note = CheckStatus.WARNING, "일부 주장에만 출처가 연결되어 있습니다."
            else:
                status, note = CheckStatus.FAIL, "검증이 필요한 주장에 아무런 출처가 없습니다."
            record = snippet_evidence(
                view.url, "text_extract", unsourced[0] if unsourced else claims[0]
            )
            evidence.append(record)
            outcomes.append(
                observed(
                    "geo.evidence.claims_have_sources",
                    status,
                    confidence_level=LOW,
                    note_ko=note,
                    evidence_ids=(*base, record.evidence_id),
                    observed_value=value,
                )
            )
            if status is not CheckStatus.PASS:
                issues.append(
                    finding(
                        "geo.evidence.claims_have_sources",
                        title_ko="수치 주장에 출처가 없습니다",
                        summary_ko=(
                            "출처가 붙지 않은 주장 예: " + (unsourced[0][:90] if unsourced else "")
                        ),
                        remediation_ko=(
                            "수치를 제시한 문단 바로 뒤에 원 자료 링크 또는 산출 기준을 적으세요."
                        ),
                        remediation_owner="MARKETER",
                        urls=[view.url],
                        evidence_ids=(record.evidence_id,),
                        business_impact_ko="검증할 수 없는 수치는 답변 근거로 채택되지 않습니다.",
                    )
                )

        # -- author -------------------------------------------------------- #
        outcomes.append(self._author_outcome(view, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.evidence.author_identified",
                    title_ko="작성자 또는 감수자가 없습니다",
                    summary_ko="글을 쓴 사람이나 내용을 감수한 사람이 페이지에 드러나지 않습니다.",
                    remediation_ko="본문 상단에 작성자 또는 감수자와 소속·자격을 표기하세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        # -- publisher ------------------------------------------------------ #
        outcomes.append(self._publisher_outcome(view, base))
        if outcomes[-1].status in {CheckStatus.FAIL, CheckStatus.WARNING}:
            issues.append(
                finding(
                    "geo.evidence.publisher_identified",
                    title_ko="발행 주체와 연락 경로가 확인되지 않습니다",
                    summary_ko=(
                        "누가 만든 사이트인지, 어떻게 연락하는지가 페이지에 없으면 "
                        "엔터티로 인정받기 어렵습니다."
                    ),
                    remediation_ko="푸터에 상호, 주소 또는 전화·이메일 중 하나를 명시하세요.",
                    remediation_owner="BUSINESS_OWNER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        # -- method --------------------------------------------------------- #
        outcomes.append(self._method_outcome(page, signals, base))

        # -- primary sources -------------------------------------------------- #
        outcomes.append(self._primary_source_outcome(page, host, base))

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=tuple(evidence), issues=tuple(issues)
        )

    # ------------------------------------------------------------------ #

    def _author_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        from veo.geo.pagekind import KINDS_EXPECTING_AN_AUTHOR

        if view.kind not in KINDS_EXPECTING_AN_AUTHOR:
            return not_applicable_outcome(
                "geo.evidence.author_identified",
                f"{view.kind} 유형의 페이지에는 작성자 표기가 필요하지 않습니다.",
                evidence_ids=evidence_ids,
            )

        page: PageDocument = view.page
        declared = [
            page.meta("author"),
            *(link.text for link in page.links if "author" in link.rel),
        ]
        in_graph = any(
            key in node.raw for node in view.graph.nodes for key in ("author", "reviewedBy")
        )
        text_markers = [m for m in AUTHOR_MARKERS if m in page.content_text]

        if any(declared) or in_graph:
            return observed(
                "geo.evidence.author_identified",
                CheckStatus.PASS,
                confidence_level=MEDIUM,
                note_ko="작성자 또는 감수자가 구조화 데이터나 메타데이터로 표기되어 있습니다.",
                evidence_ids=evidence_ids,
            )
        if text_markers:
            return observed(
                "geo.evidence.author_identified",
                CheckStatus.PASS,
                confidence_level=LOW,
                note_ko="본문에 작성자 또는 감수자 표기가 있습니다.",
                evidence_ids=evidence_ids,
                observed_value={"markers": text_markers},
            )
        return observed(
            "geo.evidence.author_identified",
            CheckStatus.FAIL,
            confidence_level=MEDIUM,
            note_ko="작성자나 감수자를 찾을 수 없습니다.",
            evidence_ids=evidence_ids,
        )

    def _publisher_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        page: PageDocument = view.page
        organization = view.graph.primary_organization()
        names = [
            page.property_value("og:site_name"),
            organization.name if organization else "",
            *(m.group(1).strip() for m in _COPYRIGHT_PATTERN.finditer(page.furniture_text)),
        ]
        name = next((n for n in names if n), "")

        channels: list[str] = []
        if any(link.href.lower().startswith("tel:") for link in page.links):
            channels.append("telephone_link")
        if any(link.href.lower().startswith("mailto:") for link in page.links):
            channels.append("email_link")
        if visible_addresses(page):
            channels.append("postal_address")
        if _REGISTRATION_PATTERN.search(page.visible_text):
            channels.append("registration_number")
        if organization is not None and (organization.telephone or organization.address_text):
            channels.append("structured_contact")

        value = {"name": name, "channels": channels}
        if name and channels:
            return observed(
                "geo.evidence.publisher_identified",
                CheckStatus.PASS,
                confidence_level=MEDIUM,
                note_ko="발행 주체와 연락 경로가 모두 확인됩니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if name or channels:
            return observed(
                "geo.evidence.publisher_identified",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="발행 주체와 연락 경로 중 하나만 확인됩니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.evidence.publisher_identified",
            CheckStatus.FAIL,
            confidence_level=MEDIUM,
            note_ko="발행 주체도 연락 경로도 확인되지 않습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _method_outcome(
        self,
        page: PageDocument,
        signals: ExtractionSignals,
        evidence_ids: tuple[str, ...],
    ) -> CheckOutcome:
        if not signals.has_quantities_worth_structuring:
            return not_applicable_outcome(
                "geo.evidence.method_disclosed",
                "자체 수치나 비교가 없어 산출 방법을 물을 대상이 아닙니다.",
                evidence_ids=evidence_ids,
            )
        markers = [m for m in METHOD_MARKERS if m in page.content_text]
        if markers:
            return observed(
                "geo.evidence.method_disclosed",
                CheckStatus.PASS,
                confidence_level=LOW,
                note_ko="수치의 산출 기준이나 방법이 본문에 설명되어 있습니다.",
                evidence_ids=evidence_ids,
                observed_value={"markers": markers},
            )
        return observed(
            "geo.evidence.method_disclosed",
            CheckStatus.FAIL,
            confidence_level=LOW,
            note_ko="수치를 제시하면서 산출 방법이나 기준을 밝히지 않았습니다.",
            evidence_ids=evidence_ids,
        )

    def _primary_source_outcome(
        self, page: PageDocument, host: str, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        outbound = page.external_links(host)
        if not outbound:
            return not_applicable_outcome(
                "geo.evidence.primary_source_linked",
                "외부 출처를 인용하지 않는 페이지입니다.",
                evidence_ids=evidence_ids,
            )
        primary = [
            link.href
            for link in outbound
            if any(marker in link.href.lower() for marker in PRIMARY_SOURCE_MARKERS)
        ]
        second_hand = [
            link.href
            for link in outbound
            if any(marker in link.href.lower() for marker in SECOND_HAND_MARKERS)
        ]
        value = {"outbound": len(outbound), "primary": primary, "second_hand": second_hand}

        if primary and len(primary) / len(outbound) >= 0.5:
            return observed(
                "geo.evidence.primary_source_linked",
                CheckStatus.PASS,
                confidence_level=LOW,
                note_ko="원출처로 직접 연결되는 링크가 대부분입니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if primary:
            return observed(
                "geo.evidence.primary_source_linked",
                CheckStatus.WARNING,
                confidence_level=LOW,
                note_ko="원출처 링크와 2차 인용 링크가 섞여 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.evidence.primary_source_linked",
            CheckStatus.FAIL,
            confidence_level=LOW,
            note_ko="원출처 대신 2차 인용 페이지로만 연결됩니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )


# --------------------------------------------------------------------------- #
# Claim detection
# --------------------------------------------------------------------------- #


def _claim_passages(page: PageDocument, answer_text: str) -> tuple[str, ...]:
    """Passages asserting something a reader cannot verify unaided."""
    found: list[str] = []
    for block in _prose_blocks(page):
        if block.own_text == answer_text:
            continue
        quantities = QUANTITY_PATTERN.findall(block.own_text)
        superlative = any(word in block.own_text.lower() for word in SUPERLATIVES)
        if len(quantities) >= 2 or superlative:
            found.append(block.own_text)
    return tuple(found)


def _prose_blocks(page: PageDocument) -> tuple[TextBlock, ...]:
    return tuple(b for b in page.passages() if not b.in_table and not b.in_list)


def _split_by_source(
    page: PageDocument, claims: tuple[str, ...], host: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    prose = [b.own_text for b in _prose_blocks(page)]
    outbound_texts = [
        link.text for link in page.external_links(host) if len(link.text) >= 4
    ]

    def has_support(text: str) -> bool:
        if any(marker in text for marker in SOURCE_MARKERS):
            return True
        return any(anchor in text for anchor in outbound_texts)

    sourced: list[str] = []
    unsourced: list[str] = []
    for claim in claims:
        index = prose.index(claim) if claim in prose else -1
        following = prose[index + 1] if 0 <= index < len(prose) - 1 else ""
        if has_support(claim) or has_support(following):
            sourced.append(claim)
        else:
            unsourced.append(claim)
    return tuple(sourced), tuple(unsourced)


__all__ = ["CHECK_IDS", "EvidenceTransparencyCollector"]
