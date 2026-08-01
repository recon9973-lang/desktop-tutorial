"""답변 추출성 — can a passage be lifted out of this page and still make sense.

Everything in this category is judgement, so every outcome carries a ``HEURISTIC_*``
confidence. The alternative — calling a guess a direct observation — would let a weak
signal weigh as much as an HTTP status code, which is exactly the failure mode the
specification's confidence levels exist to prevent.
"""

from __future__ import annotations

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    not_applicable_outcome,
)
from veo.collect.sample import single_page_outcome, unproven_absence_outcome
from veo.geo.extractability import (
    ExtractionSignals,
    analyse_extractability,
    repeatable_passages,
)
from veo.geo.reporting import (
    HIGH,
    LOW,
    MEDIUM,
    finding,
    observed,
    sample_scope,
    snippet_evidence,
)
from veo.geo.view import build_view, parsed_documents
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.extract.direct_answer_present",
        "geo.extract.passage_self_contained",
        "geo.extract.heading_structure_semantic",
        "geo.extract.tables_lists_machine_readable",
        "geo.extract.low_boilerplate_ratio",
        "geo.extract.no_duplicate_answer_blocks",
    }
)

_SELF_CONTAINED_GOOD = 0.8
_SELF_CONTAINED_WEAK = 0.5

_CONTENT_SHARE_GOOD = 0.55
_CONTENT_SHARE_WEAK = 0.35


class AnswerExtractabilityCollector:
    """Observes whether the page offers a quotable, self-standing answer."""

    category_id = "answer_extractability"

    @property
    def check_ids(self) -> frozenset[str]:
        return CHECK_IDS

    def collect(self, context: CollectionContext) -> CollectionResult:
        view = build_view(context)
        signals = analyse_extractability(view.page)
        evidence: list[EvidenceRecord] = list(view.evidence)
        issues: list[IssueDraft] = []
        outcomes: list[CheckOutcome] = []

        base = view.evidence_ids

        # -- a direct answer --------------------------------------------- #
        if signals.direct_answer is not None:
            record = snippet_evidence(
                view.url,
                "text_extract",
                signals.direct_answer.text,
                detail={"shared_terms": list(signals.direct_answer.shared_terms)},
            )
            evidence.append(record)
            outcomes.append(
                observed(
                    "geo.extract.direct_answer_present",
                    CheckStatus.PASS,
                    confidence_level=MEDIUM,
                    note_ko="제목의 질문에 곧바로 답하는 문단이 상단에 있습니다.",
                    evidence_ids=(*base, record.evidence_id),
                    observed_value={"shared_terms": list(signals.direct_answer.shared_terms)},
                )
            )
        else:
            outcomes.append(
                observed(
                    "geo.extract.direct_answer_present",
                    CheckStatus.FAIL,
                    confidence_level=MEDIUM,
                    note_ko=(
                        "제목이 던지는 질문에 직접 답하는 독립 문단을 찾지 못했습니다."
                        if signals.topic_terms
                        else "제목이 주제를 드러내지 않아 답변 문단을 특정할 수 없습니다."
                    ),
                    evidence_ids=base,
                    observed_value={"topic_terms": list(signals.topic_terms)},
                )
            )
            issues.append(
                finding(
                    "geo.extract.direct_answer_present",
                    title_ko="핵심 질문에 답하는 문단이 없습니다",
                    summary_ko=(
                        "AI 답변 엔진은 한 문단만 떼어 인용합니다. 제목이 묻는 것에 두세 "
                        "문장으로 답하는 문단이 본문 첫머리에 없으면 인용 후보가 되지 않습니다."
                    ),
                    remediation_ko=(
                        "h1 바로 아래에 결론을 먼저 쓰는 60~200자 문단을 추가하세요."
                    ),
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                    business_impact_ko="답변에 인용될 문단 자체가 없습니다.",
                )
            )

        # -- passages that survive extraction ---------------------------- #
        outcomes.append(self._self_contained_outcome(signals, base))
        if outcomes[-1].status in {CheckStatus.FAIL, CheckStatus.WARNING}:
            issues.append(
                finding(
                    "geo.extract.passage_self_contained",
                    title_ko="문단이 앞 문맥에 기대고 있습니다",
                    summary_ko=(
                        "'이것은', '위에서 말씀드린 것처럼' 같은 표현으로 시작하는 문단은 "
                        "떼어내면 뜻이 사라집니다. 발견된 예: "
                        + ", ".join(signals.dependent_openings[:3])
                    ),
                    remediation_ko="각 문단의 첫 문장에 주어와 대상을 다시 적으세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        # -- headings ----------------------------------------------------- #
        outcomes.append(self._heading_outcome(signals, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.extract.heading_structure_semantic",
                    title_ko="제목 구조가 주제 단위로 나뉘어 있지 않습니다",
                    summary_ko=(
                        f"h1 {signals.headings.h1_count}개, h2 {signals.headings.section_count}개."
                        " 제목 단위가 없으면 어느 구간이 어떤 질문의 답인지 판단할 수 없습니다."
                    ),
                    remediation_ko="페이지당 h1 하나를 두고, 질문 단위로 h2를 나누세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        # -- tables and lists --------------------------------------------- #
        outcomes.append(self._structure_outcome(signals, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.extract.tables_lists_machine_readable",
                    title_ko="비교·수치 정보가 문장 속에만 있습니다",
                    summary_ko=(
                        "본문에서 확인된 수치: " + ", ".join(signals.quantities[:5]) + ". "
                        "표나 목록으로 정리되지 않으면 값과 항목의 짝이 사라집니다."
                    ),
                    remediation_ko="가격·기간·사양 비교는 표 또는 목록으로 옮기세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        # -- boilerplate --------------------------------------------------- #
        outcomes.append(self._content_share_outcome(signals, base))
        if outcomes[-1].status in {CheckStatus.FAIL, CheckStatus.WARNING}:
            issues.append(
                finding(
                    "geo.extract.low_boilerplate_ratio",
                    title_ko="본문보다 반복 요소가 많습니다",
                    summary_ko=(
                        f"본문 {signals.content_characters}자, 머리·꼬리·내비게이션 "
                        f"{signals.furniture_characters}자입니다."
                    ),
                    remediation_ko=(
                        "내비게이션과 푸터를 줄이거나 본문을 보강해 페이지의 주제를 분명히 하세요."
                    ),
                    remediation_owner="DEVELOPER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        # -- duplication across URLs ---------------------------------------- #
        duplicate_outcome, duplicate_issue, duplicate_evidence = self._duplication_outcome(
            context, view.url
        )
        outcomes.append(duplicate_outcome)
        evidence.extend(duplicate_evidence)
        if duplicate_issue is not None:
            issues.append(duplicate_issue)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=tuple(evidence), issues=tuple(issues)
        )

    # ------------------------------------------------------------------ #

    def _self_contained_outcome(
        self, signals: ExtractionSignals, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        if signals.judged_passage_count == 0:
            return observed(
                "geo.extract.passage_self_contained",
                CheckStatus.FAIL,
                confidence_level=MEDIUM,
                note_ko="독립성을 판단할 만한 길이의 문단이 없습니다.",
                evidence_ids=evidence_ids,
            )
        ratio = signals.self_contained_ratio
        value = {
            "self_contained_ratio": round(ratio, 3),
            "judged_passages": signals.judged_passage_count,
        }
        if ratio >= _SELF_CONTAINED_GOOD:
            return observed(
                "geo.extract.passage_self_contained",
                CheckStatus.PASS,
                confidence_level=MEDIUM,
                note_ko="문단 대부분이 앞 문맥 없이도 이해됩니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        status = CheckStatus.WARNING if ratio >= _SELF_CONTAINED_WEAK else CheckStatus.FAIL
        return observed(
            "geo.extract.passage_self_contained",
            status,
            confidence_level=MEDIUM,
            note_ko="앞 문맥에 기대는 문단이 있어 발췌 시 뜻이 흐려집니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _heading_outcome(
        self, signals: ExtractionSignals, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        report = signals.headings
        value = {
            "h1_count": report.h1_count,
            "section_count": report.section_count,
            "skipped_levels": [list(pair) for pair in report.skipped_levels],
        }
        if report.h1_count != 1:
            return observed(
                "geo.extract.heading_structure_semantic",
                CheckStatus.FAIL,
                confidence_level=HIGH,
                note_ko=f"본문 h1이 {report.h1_count}개입니다. 페이지당 하나여야 합니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if report.skipped_levels or report.section_count < 2:
            return observed(
                "geo.extract.heading_structure_semantic",
                CheckStatus.WARNING,
                confidence_level=HIGH,
                note_ko="제목 단계가 건너뛰었거나 주제 구분이 충분하지 않습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.extract.heading_structure_semantic",
            CheckStatus.PASS,
            confidence_level=HIGH,
            note_ko="제목이 주제 단위로 나뉘어 있습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _structure_outcome(
        self, signals: ExtractionSignals, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        if not signals.has_quantities_worth_structuring:
            return not_applicable_outcome(
                "geo.extract.tables_lists_machine_readable",
                "비교하거나 표로 정리할 수치 정보가 없는 페이지입니다.",
                evidence_ids=evidence_ids,
            )
        value = {
            "quantities": len(signals.quantities),
            "tabulated": len(signals.tabulated_quantities),
        }
        if len(signals.tabulated_quantities) >= 2:
            return observed(
                "geo.extract.tables_lists_machine_readable",
                CheckStatus.PASS,
                confidence_level=MEDIUM,
                note_ko="수치가 표 또는 목록으로 구조화되어 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if signals.has_structured_container:
            return observed(
                "geo.extract.tables_lists_machine_readable",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="표나 목록은 있지만 수치 대부분이 문장 속에 남아 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.extract.tables_lists_machine_readable",
            CheckStatus.FAIL,
            confidence_level=MEDIUM,
            note_ko="비교·수치 정보가 문장 속에만 있어 항목과 값의 짝을 잃습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _content_share_outcome(
        self, signals: ExtractionSignals, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        share = signals.main_content_ratio
        value = {
            "content_share": round(share, 3),
            "content_characters": signals.content_characters,
            "furniture_characters": signals.furniture_characters,
        }
        if share >= _CONTENT_SHARE_GOOD:
            status = CheckStatus.PASS
            note = "본문이 반복 요소보다 충분히 많습니다."
        elif share >= _CONTENT_SHARE_WEAK:
            status = CheckStatus.WARNING
            note = "본문 비중이 낮아 페이지의 주제가 흐려집니다."
        else:
            status = CheckStatus.FAIL
            note = "내비게이션·푸터가 본문을 압도합니다."
        return observed(
            "geo.extract.low_boilerplate_ratio",
            status,
            confidence_level=MEDIUM,
            note_ko=note,
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _duplication_outcome(
        self, context: CollectionContext, target_url: str
    ) -> tuple[CheckOutcome, IssueDraft | None, list[EvidenceRecord]]:
        pages = parsed_documents(context)
        if len(pages) < 2:
            # 한 장만 가져온 것은 "이 사이트에 비교할 페이지가 없다" 가 아니다. 우리가
            # 못 잰 것이므로 배점을 분모에 남긴 채 0점이어야 한다 — 해당 없음으로 접으면
            # 덜 재는 편이 유리해진다.
            return (
                single_page_outcome(
                    sample_scope(context),
                    "geo.extract.no_duplicate_answer_blocks",
                    subject_ko="페이지 간 답변 블록 중복 여부",
                ),
                None,
                [],
            )

        by_passage: dict[str, list[str]] = {}
        for url, page in pages.items():
            for passage in repeatable_passages(page):
                by_passage.setdefault(passage, []).append(url)

        repeated = {p: urls for p, urls in by_passage.items() if len(urls) > 1}
        evaluated = float(len(pages))
        if not repeated:
            # 부재 주장은 표본이 전체일 때만 PASS 다. SEO 쪽과 같은 함수가 가른다 —
            # 규칙이 두 벌이면 한쪽만 고쳐지고, 실제로 그랬던 적이 있다(sample.py 모듈 문서).
            guard = unproven_absence_outcome(
                sample_scope(context),
                "geo.extract.no_duplicate_answer_blocks",
                subject_ko="페이지 간 답변 블록 중복",
                seen_pages=len(pages),
            )
            if guard is not None:
                return guard, None, []
            return (
                observed(
                    "geo.extract.no_duplicate_answer_blocks",
                    CheckStatus.PASS,
                    confidence_level=MEDIUM,
                    note_ko="수집한 URL 사이에 통째로 반복되는 답변 블록이 없습니다.",
                    evaluated_weight=evaluated,
                    affected_weight=evaluated,
                ),
                None,
                [],
            )

        affected = {url for urls in repeated.values() for url in urls}
        sample = next(iter(repeated))
        record = snippet_evidence(
            target_url,
            "text_extract",
            sample,
            detail={"repeated_on": sorted(affected)},
        )
        outcome = observed(
            "geo.extract.no_duplicate_answer_blocks",
            CheckStatus.FAIL if len(affected) == len(pages) else CheckStatus.WARNING,
            confidence_level=LOW,
            note_ko=f"{len(repeated)}개 문단이 {len(affected)}개 URL에 그대로 반복됩니다.",
            evidence_ids=(record.evidence_id,),
            observed_value={"repeated_blocks": len(repeated), "urls": sorted(affected)},
            affected_weight=float(len(affected)),
            evaluated_weight=evaluated,
        )
        issue = finding(
            "geo.extract.no_duplicate_answer_blocks",
            title_ko="같은 답변 블록이 여러 URL에 반복됩니다",
            summary_ko=(
                "반복 문단 예: " + sample[:80] + " … 어느 URL이 원본인지 판단할 수 없으면 "
                "인용 대상이 흩어집니다."
            ),
            remediation_ko="대표 URL 한 곳에만 본문을 두고 나머지는 요약과 링크로 바꾸세요.",
            remediation_owner="MARKETER",
            urls=sorted(affected),
            evidence_ids=(record.evidence_id,),
        )
        return outcome, issue, [record]


__all__ = ["CHECK_IDS", "AnswerExtractabilityCollector"]
