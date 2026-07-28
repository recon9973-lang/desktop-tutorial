"""구조화 데이터·메타 — absence is fine, contradiction is not.

The specification is explicit that a page with no structured data is NOT_APPLICABLE here
rather than deficient, and this collector honours that literally: with no JSON-LD on the
page, all three ``geo.sd.*`` checks leave the denominator and only the meta checks remain.

What is treated as serious is structured data that says something the page does not. A
declared telephone number nobody can call, or a price nobody is charged, is worse than no
declaration at all — it puts a wrong fact into an answer engine with a machine-readable
stamp on it. That check is the one gated as ``STRUCTURED_DATA_MISMATCH``.
"""

from __future__ import annotations

import re

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    not_applicable_outcome,
)
from veo.geo.entity_graph import EntityGraph
from veo.geo.pagekind import expected_types, type_is_appropriate
from veo.geo.parsing import PageDocument
from veo.geo.reporting import DIRECT, HIGH, MEDIUM, finding, observed, snippet_evidence
from veo.geo.view import TargetView, build_view
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.sd.valid_syntax",
        "geo.sd.matches_visible_content",
        "geo.sd.page_type_appropriate",
        "geo.meta.title_description_descriptive",
        "geo.meta.opengraph_present",
    }
)

#: Declared values a reader would notice were wrong straight away.
HARD_PROPERTIES = frozenset(
    {"name", "telephone", "price", "streetAddress", "ratingValue", "reviewCount"}
)

_NUMERIC_PROPERTIES = frozenset({"price", "ratingValue", "reviewCount"})

_MIN_TITLE_CHARACTERS = 10
_MAX_TITLE_CHARACTERS = 80
_MIN_DESCRIPTION_CHARACTERS = 30
_MAX_DESCRIPTION_CHARACTERS = 200

_THOUSANDS = re.compile(r"(?<=\d),(?=\d)")
_TOKEN = re.compile(r"[0-9A-Za-z가-힣]{2,}")


class StructuredDataMetaCollector:
    """Observes what the markup declares, and whether the page bears it out."""

    category_id = "structured_data_meta"

    @property
    def check_ids(self) -> frozenset[str]:
        return CHECK_IDS

    def collect(self, context: CollectionContext) -> CollectionResult:
        view = build_view(context)
        page = view.page
        graph = view.graph
        evidence: list[EvidenceRecord] = list(view.evidence)
        issues: list[IssueDraft] = []
        outcomes: list[CheckOutcome] = []
        base = view.evidence_ids

        if not graph.has_structured_data:
            reason = "구조화 데이터가 없는 페이지입니다. 부재 자체는 오류가 아닙니다."
            for check_id in (
                "geo.sd.valid_syntax",
                "geo.sd.matches_visible_content",
                "geo.sd.page_type_appropriate",
            ):
                outcomes.append(not_applicable_outcome(check_id, reason, evidence_ids=base))
        else:
            record = snippet_evidence(
                view.url,
                "dom_snippet",
                "\n".join(page.json_ld_blocks),
                detail={"blocks": len(page.json_ld_blocks)},
            )
            evidence.append(record)
            ids = (*base, record.evidence_id)

            outcomes.append(self._syntax_outcome(graph, ids))
            if outcomes[-1].status is CheckStatus.FAIL:
                issues.append(
                    finding(
                        "geo.sd.valid_syntax",
                        title_ko="구조화 데이터가 파싱되지 않습니다",
                        summary_ko="오류: " + "; ".join(graph.parse_errors[:2]),
                        remediation_ko="JSON-LD 문법 오류를 수정하고 검증기로 다시 확인하세요.",
                        remediation_owner="DEVELOPER",
                        urls=[view.url],
                        evidence_ids=ids,
                    )
                )

            match_outcome, match_issue = self._match_outcome(view, ids)
            outcomes.append(match_outcome)
            if match_issue is not None:
                issues.append(match_issue)

            outcomes.append(self._type_outcome(view, ids))
            if outcomes[-1].status is CheckStatus.FAIL:
                issues.append(
                    finding(
                        "geo.sd.page_type_appropriate",
                        title_ko="페이지 성격과 맞지 않는 schema 타입입니다",
                        summary_ko=(
                            f"선언된 타입: {', '.join(graph.declared_types())} / "
                            f"페이지 유형: {view.kind}"
                        ),
                        remediation_ko="페이지 의도에 맞는 타입으로 바꾸세요.",
                        remediation_owner="DEVELOPER",
                        urls=[view.url],
                        evidence_ids=ids,
                    )
                )

        outcomes.append(self._title_outcome(page, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.meta.title_description_descriptive",
                    title_ko="title 또는 description이 페이지를 설명하지 않습니다",
                    summary_ko=(
                        f"title: '{page.title}' / "
                        f"description 길이: {len(page.meta('description'))}자"
                    ),
                    remediation_ko="페이지 주제를 담은 제목과 요약 설명을 작성하세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        outcomes.append(self._opengraph_outcome(page, base))

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=tuple(evidence), issues=tuple(issues)
        )

    # ------------------------------------------------------------------ #

    def _syntax_outcome(
        self, graph: EntityGraph, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        if graph.parse_errors:
            return observed(
                "geo.sd.valid_syntax",
                CheckStatus.FAIL,
                confidence_level=DIRECT,
                note_ko=f"{len(graph.parse_errors)}개 블록이 JSON으로 파싱되지 않습니다.",
                evidence_ids=evidence_ids,
                observed_value={"errors": list(graph.parse_errors)},
            )
        untyped = [node.node_id or "(무명)" for node in graph.nodes if not node.types]
        if untyped:
            return observed(
                "geo.sd.valid_syntax",
                CheckStatus.WARNING,
                confidence_level=DIRECT,
                note_ko="@type이 없는 노드가 있어 해석되지 않을 수 있습니다.",
                evidence_ids=evidence_ids,
                observed_value={"untyped_nodes": untyped},
            )
        return observed(
            "geo.sd.valid_syntax",
            CheckStatus.PASS,
            confidence_level=DIRECT,
            note_ko="구조화 데이터가 오류 없이 파싱됩니다.",
            evidence_ids=evidence_ids,
        )

    def _match_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> tuple[CheckOutcome, IssueDraft | None]:
        page: PageDocument = view.page
        visible = _THOUSANDS.sub("", page.visible_text)
        digits = "".join(ch for ch in visible if ch.isdigit())

        disagreeing: list[str] = []
        checked = 0
        for claim in view.graph.claims():
            checked += 1
            if _claim_is_visible(claim.property_name, claim.value, visible, digits):
                continue
            disagreeing.append(claim.property_name)

        hard = sorted({name for name in disagreeing if name in HARD_PROPERTIES})
        soft = sorted({name for name in disagreeing if name not in HARD_PROPERTIES})
        value = {"checked": checked, "disagreeing_fields": sorted(set(disagreeing))}

        if not disagreeing:
            return (
                observed(
                    "geo.sd.matches_visible_content",
                    CheckStatus.PASS,
                    confidence_level=HIGH,
                    note_ko="구조화 데이터의 값이 모두 화면에서 확인됩니다.",
                    evidence_ids=evidence_ids,
                    observed_value=value,
                ),
                None,
            )
        if not hard:
            return (
                observed(
                    "geo.sd.matches_visible_content",
                    CheckStatus.WARNING,
                    confidence_level=HIGH,
                    note_ko="화면에서 확인되지 않는 부가 항목이 있습니다: " + ", ".join(soft),
                    evidence_ids=evidence_ids,
                    observed_value=value,
                ),
                None,
            )

        outcome = observed(
            "geo.sd.matches_visible_content",
            CheckStatus.FAIL,
            confidence_level=HIGH,
            note_ko="구조화 데이터가 화면과 다른 값을 선언합니다: " + ", ".join(hard),
            evidence_ids=evidence_ids,
            observed_value=value,
        )
        issue = finding(
            "geo.sd.matches_visible_content",
            title_ko="구조화 데이터가 화면 내용과 다릅니다",
            summary_ko=(
                "불일치 항목: " + ", ".join(hard) + ". 사람이 보는 값과 기계가 읽는 값이 "
                "다르면 잘못된 정보가 그대로 답변에 인용됩니다."
            ),
            remediation_ko="화면에 실제로 표시되는 값으로 구조화 데이터를 맞추세요.",
            remediation_owner="DEVELOPER",
            urls=[view.url],
            evidence_ids=evidence_ids,
            business_impact_ko="허위 표기로 간주될 수 있는 위험 항목입니다.",
            reverification_note_ko="수정 후 화면 값과 JSON-LD 값을 함께 재수집해 대조합니다.",
        )
        return outcome, issue

    def _type_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        declared = view.graph.declared_types()
        if not declared:
            return observed(
                "geo.sd.page_type_appropriate",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="선언된 @type이 없어 페이지 의도와의 적합성을 판단할 수 없습니다.",
                evidence_ids=evidence_ids,
            )
        unexpected = type_is_appropriate(view.kind, declared)
        matching = expected_types(view.kind, declared)
        value = {"kind": str(view.kind), "declared": list(declared), "unexpected": list(unexpected)}

        if not unexpected:
            return observed(
                "geo.sd.page_type_appropriate",
                CheckStatus.PASS,
                confidence_level=MEDIUM,
                note_ko="페이지 의도에 맞는 타입을 사용합니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if matching:
            return observed(
                "geo.sd.page_type_appropriate",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="일부 타입이 페이지 성격과 어긋납니다: " + ", ".join(unexpected),
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.sd.page_type_appropriate",
            CheckStatus.FAIL,
            confidence_level=MEDIUM,
            note_ko="선언된 타입이 페이지 성격과 전혀 맞지 않습니다: " + ", ".join(unexpected),
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _title_outcome(self, page: PageDocument, evidence_ids: tuple[str, ...]) -> CheckOutcome:
        title = page.title
        description = page.meta("description") or page.property_value("og:description")
        value = {"title_length": len(title), "description_length": len(description)}

        if len(title) < _MIN_TITLE_CHARACTERS or not description:
            return observed(
                "geo.meta.title_description_descriptive",
                CheckStatus.FAIL,
                confidence_level=MEDIUM,
                note_ko="제목이 지나치게 짧거나 설명이 없습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )

        headings = [h.text for h in page.content_headings() if h.level == 1]
        subject = headings[0] if headings else page.content_text[:200]
        shared = _shared_tokens(title, subject) | _shared_tokens(description, subject)

        if (
            len(title) > _MAX_TITLE_CHARACTERS
            or not (_MIN_DESCRIPTION_CHARACTERS <= len(description) <= _MAX_DESCRIPTION_CHARACTERS)
            or not shared
        ):
            return observed(
                "geo.meta.title_description_descriptive",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="제목·설명의 길이나 본문과의 일치가 충분하지 않습니다.",
                evidence_ids=evidence_ids,
                observed_value=value | {"shared_terms": sorted(shared)},
            )
        return observed(
            "geo.meta.title_description_descriptive",
            CheckStatus.PASS,
            confidence_level=MEDIUM,
            note_ko="제목과 설명이 본문 주제를 정확히 설명합니다.",
            evidence_ids=evidence_ids,
            observed_value=value | {"shared_terms": sorted(shared)},
        )

    def _opengraph_outcome(self, page: PageDocument, evidence_ids: tuple[str, ...]) -> CheckOutcome:
        present = [
            name
            for name in ("og:title", "og:description", "og:image")
            if page.property_value(name)
        ]
        value = {"present": present}
        if len(present) == 3:
            return observed(
                "geo.meta.opengraph_present",
                CheckStatus.PASS,
                confidence_level=DIRECT,
                note_ko="공유용 메타데이터가 모두 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if present:
            return observed(
                "geo.meta.opengraph_present",
                CheckStatus.WARNING,
                confidence_level=DIRECT,
                note_ko="공유용 메타데이터가 일부만 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.meta.opengraph_present",
            CheckStatus.FAIL,
            confidence_level=DIRECT,
            note_ko="공유용 메타데이터가 없습니다. 정보 항목이라 점수에는 영향이 없습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _claim_is_visible(property_name: str, value: str, visible: str, digits: str) -> bool:
    if property_name == "telephone":
        wanted = "".join(ch for ch in value if ch.isdigit())
        return bool(wanted) and wanted in digits
    if property_name in _NUMERIC_PROPERTIES:
        wanted = value.replace(",", "")
        if wanted.endswith(".0"):
            wanted = wanted[:-2]
        return bool(wanted) and wanted in _THOUSANDS.sub("", visible)
    return value.lower() in visible.lower()


def _shared_tokens(left: str, right: str) -> set[str]:
    return set(_TOKEN.findall(left.lower())) & set(_TOKEN.findall(right.lower()))


__all__ = ["CHECK_IDS", "HARD_PROPERTIES", "StructuredDataMetaCollector"]
