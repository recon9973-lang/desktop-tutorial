"""엔터티 명확성·일관성 — is it unambiguous who this is.

The distinctive rule here is the address check. A business that trades only online has no
premises to be inconsistent about, so ``geo.entity.nap_consistent`` is NOT_APPLICABLE for
it — not a failure, and not a nudge to invent an address. When there *are* premises, the
page, its structured data and the official record are compared against one another, and a
disagreement between any two of them is the finding.

The entity-graph check likewise asks about linkage, not presence. A site with no JSON-LD
at all is excused; a site whose JSON-LD is a heap of unconnected nodes is not.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.geo.entity_graph import EntityGraph
from veo.geo.pagekind import visible_addresses, visible_telephones
from veo.geo.parsing import PageDocument, normalise
from veo.geo.reporting import HIGH, LOW, MEDIUM, finding, observed, snippet_evidence
from veo.geo.view import TargetView, build_view, parsed_documents
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.entity.organization_identified",
        "geo.entity.stable_id_graph",
        "geo.entity.sameas_profiles_present",
        "geo.entity.name_consistent_across_pages",
        "geo.entity.nap_consistent",
        "geo.entity.disambiguation_signals",
    }
)

OFFICIAL_RECORD_PROVIDER = "official_records"

_LEGAL_FORMS = (
    "주식회사", "(주)", "유한회사", "재단법인", "사단법인",
    "inc.", "inc", "ltd.", "ltd", "co.", "llc",
)

_SEPARATORS = ("\u2014", "\u2013", "|", " - ", "\u00b7", ":")

_COPYRIGHT_PATTERN = re.compile(r"©\s*(?:\d{4}\s*)?([^·|\n]{2,40})")

_LOCALITY_PATTERN = re.compile(
    r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
)
_FOUNDING_PATTERN = re.compile(r"\d{4}년[^,\n]{0,6}(개원|설립|창업|창립|오픈)")
_REGISTRATION_PATTERN = re.compile(r"(사업자등록번호|통신판매업|법인등록번호|등록번호)")

#: Hosts that, when linked from a page, are almost always the brand's own profile.
_PROFILE_HOSTS = (
    "map.naver.com",
    "instagram.com",
    "youtube.com",
    "facebook.com",
    "linkedin.com",
)

#: How many distinguishing details a brand needs before a same-name rival stops mattering.
_DISAMBIGUATION_STRONG = 3
_DISAMBIGUATION_WEAK = 2


class EntityClarityCollector:
    """Observes who the site says it is, and whether every source agrees."""

    category_id = "entity_clarity"

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

        outcomes.append(self._organization_outcome(view, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.entity.organization_identified",
                    title_ko="사이트의 주체가 식별되지 않습니다",
                    summary_ko=(
                        "조직 이름과 대표 URL·연락처를 잇는 신호가 없어 어떤 엔터티의 "
                        "페이지인지 판단할 수 없습니다."
                    ),
                    remediation_ko=(
                        "Organization 구조화 데이터 또는 og:site_name과 푸터 상호를 갖추세요."
                    ),
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        outcomes.append(self._graph_outcome(graph, base))
        outcomes.append(self._same_as_outcome(view, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.entity.sameas_profiles_present",
                    title_ko="공식 외부 프로필로 이어지는 연결이 없습니다",
                    summary_ko="sameAs나 공식 프로필 링크가 없어 외부 정보와 이어지지 않습니다.",
                    remediation_ko="네이버 플레이스·공식 SNS·등록 정보를 sameAs로 연결하세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        name_outcome, name_issue, name_evidence = self._name_outcome(context, view.url)
        outcomes.append(name_outcome)
        evidence.extend(name_evidence)
        if name_issue is not None:
            issues.append(name_issue)

        nap_outcome, nap_issue, nap_evidence = self._nap_outcome(context, view, base)
        outcomes.append(nap_outcome)
        evidence.extend(nap_evidence)
        if nap_issue is not None:
            issues.append(nap_issue)

        outcomes.append(self._disambiguation_outcome(page, graph, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.entity.disambiguation_signals",
                    title_ko="동명 브랜드와 구분되는 신호가 없습니다",
                    summary_ko=(
                        "지역, 설립 연도, 등록번호, 공식 프로필 가운데 어느 것도 확인되지 "
                        "않아 같은 이름의 다른 사업자와 섞일 수 있습니다."
                    ),
                    remediation_ko="지역명, 설립 연도, 사업자등록번호를 페이지에 명시하세요.",
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=tuple(evidence), issues=tuple(issues)
        )

    # ------------------------------------------------------------------ #

    def _organization_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        organization = view.graph.primary_organization()
        page: PageDocument = view.page
        site_name = page.property_value("og:site_name")

        if organization is not None and organization.name:
            anchors = [
                bool(organization.url),
                bool(organization.logo),
                bool(organization.telephone),
                bool(organization.address_text),
            ]
            if any(anchors):
                return observed(
                    "geo.entity.organization_identified",
                    CheckStatus.PASS,
                    confidence_level=HIGH,
                    note_ko=f"구조화 데이터가 조직 '{organization.name}'을 식별합니다.",
                    evidence_ids=evidence_ids,
                    observed_value={"name": organization.name},
                )
            return observed(
                "geo.entity.organization_identified",
                CheckStatus.WARNING,
                confidence_level=HIGH,
                note_ko="조직 이름은 있지만 URL·로고·연락처 같은 고정점이 없습니다.",
                evidence_ids=evidence_ids,
            )

        footer_names = [
            m.group(1).strip() for m in _COPYRIGHT_PATTERN.finditer(page.furniture_text)
        ]
        if site_name and (footer_names or page.has_contact_path()):
            return observed(
                "geo.entity.organization_identified",
                CheckStatus.PASS,
                confidence_level=MEDIUM,
                note_ko="구조화 데이터는 없지만 사이트 이름과 표기가 일치합니다.",
                evidence_ids=evidence_ids,
            )
        if site_name or footer_names:
            return observed(
                "geo.entity.organization_identified",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="조직 표기가 한 곳에만 있어 엔터티로 굳히기에는 약합니다.",
                evidence_ids=evidence_ids,
            )
        return observed(
            "geo.entity.organization_identified",
            CheckStatus.FAIL,
            confidence_level=MEDIUM,
            note_ko="조직을 식별할 수 있는 표기가 없습니다.",
            evidence_ids=evidence_ids,
        )

    def _graph_outcome(self, graph: EntityGraph, evidence_ids: tuple[str, ...]) -> CheckOutcome:
        if not graph.has_structured_data:
            return not_applicable_outcome(
                "geo.entity.stable_id_graph",
                "구조화 데이터를 사용하지 않는 페이지입니다.",
                evidence_ids=evidence_ids,
            )
        coherence = graph.coherence()
        value = {
            "nodes": coherence.node_count,
            "identified": coherence.nodes_with_ids,
            "orphans": list(coherence.orphan_ids),
            "unresolved": list(coherence.unresolved_references),
        }
        if coherence.nodes_with_ids == 0:
            return observed(
                "geo.entity.stable_id_graph",
                CheckStatus.FAIL,
                confidence_level=HIGH,
                note_ko="구조화 데이터에 @id가 전혀 없어 엔터티가 서로 연결되지 않습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if coherence.orphan_ids or coherence.unresolved_references:
            return observed(
                "geo.entity.stable_id_graph",
                CheckStatus.WARNING,
                confidence_level=HIGH,
                note_ko="일부 노드가 어디에도 연결되지 않았거나 가리키는 @id가 없습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.entity.stable_id_graph",
            CheckStatus.PASS,
            confidence_level=HIGH,
            note_ko="@id가 엔터티 사이를 빠짐없이 연결합니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _same_as_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        organization = view.graph.primary_organization()
        declared = list(organization.same_as) if organization else []
        if not declared:
            declared = [
                link.href
                for link in view.page.links
                if any(
                    marker in link.href
                    for marker in _PROFILE_HOSTS
                )
            ]
        value = {"profiles": declared}
        if len(declared) >= 2:
            return observed(
                "geo.entity.sameas_profiles_present",
                CheckStatus.PASS,
                confidence_level=HIGH,
                note_ko=f"공식 외부 프로필 {len(declared)}개가 연결되어 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if declared:
            return observed(
                "geo.entity.sameas_profiles_present",
                CheckStatus.WARNING,
                confidence_level=HIGH,
                note_ko="외부 프로필이 하나뿐이라 교차 확인이 약합니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.entity.sameas_profiles_present",
            CheckStatus.FAIL,
            confidence_level=HIGH,
            note_ko="공식 외부 프로필로 이어지는 연결이 없습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _name_outcome(
        self, context: CollectionContext, target_url: str
    ) -> tuple[CheckOutcome, IssueDraft | None, list[EvidenceRecord]]:
        candidates: dict[str, list[str]] = {}
        for url, page in parsed_documents(context).items():
            for candidate in _brand_candidates(page):
                candidates.setdefault(candidate, []).append(url)

        if not candidates:
            return (
                unknown_outcome(
                    "geo.entity.name_consistent_across_pages",
                    "브랜드 명칭으로 볼 만한 표기를 찾지 못했습니다.",
                ),
                None,
                [],
            )

        raw = sorted(candidates)
        stripped = sorted({_strip_legal_form(name) for name in raw})
        record = snippet_evidence(
            target_url, "text_extract", " / ".join(raw), detail={"variants": raw}
        )
        value = {"variants": raw, "normalised": stripped}

        if len(stripped) == 1:
            return (
                observed(
                    "geo.entity.name_consistent_across_pages",
                    CheckStatus.PASS,
                    confidence_level=MEDIUM,
                    note_ko="사이트 전체에서 같은 명칭을 씁니다.",
                    evidence_ids=(record.evidence_id,),
                    observed_value=value,
                ),
                None,
                [record],
            )
        if len(raw) > len(stripped):
            return (
                observed(
                    "geo.entity.name_consistent_across_pages",
                    CheckStatus.WARNING,
                    confidence_level=MEDIUM,
                    note_ko="법인격 표기만 다른 명칭 변형이 있습니다.",
                    evidence_ids=(record.evidence_id,),
                    observed_value=value,
                ),
                None,
                [record],
            )
        outcome = observed(
            "geo.entity.name_consistent_across_pages",
            CheckStatus.FAIL,
            confidence_level=MEDIUM,
            note_ko="사이트 안에서 서로 다른 명칭이 쓰이고 있습니다: " + ", ".join(raw),
            evidence_ids=(record.evidence_id,),
            observed_value=value,
        )
        issue = finding(
            "geo.entity.name_consistent_across_pages",
            title_ko="브랜드 명칭이 페이지마다 다릅니다",
            summary_ko="확인된 표기: " + ", ".join(raw),
            remediation_ko=(
                "공식 표기 하나를 정하고 og:site_name·푸터·구조화 데이터에 같은 값을 쓰세요."
            ),
            remediation_owner="MARKETER",
            urls=sorted({u for urls in candidates.values() for u in urls}),
            evidence_ids=(record.evidence_id,),
        )
        return outcome, issue, [record]

    def _nap_outcome(
        self, context: CollectionContext, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> tuple[CheckOutcome, IssueDraft | None, list[EvidenceRecord]]:
        page: PageDocument = view.page
        organization = view.graph.primary_organization()
        declared_address = organization.address_text if organization else ""
        visible = visible_addresses(page)

        if not visible and not declared_address:
            return (
                not_applicable_outcome(
                    "geo.entity.nap_consistent",
                    "오프라인 거점이 없는 사업자로 보여 주소 일치 여부는 평가하지 않습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
                [],
            )

        official = _official_record(context)
        sources: dict[str, Mapping[str, Any]] = {
            "page": {
                "address": visible[0] if visible else "",
                "telephone": (visible_telephones(page) or ("",))[0],
                "name": page.property_value("og:site_name"),
            }
        }
        if organization is not None:
            sources["structured_data"] = {
                "address": organization.address_text,
                "telephone": organization.telephone,
                "name": organization.name,
            }
        if official:
            sources["official_record"] = official

        if len(sources) < 2:
            return (
                unknown_outcome(
                    "geo.entity.nap_consistent",
                    "대조할 두 번째 출처가 없어 상호·주소·연락처 일치를 확인할 수 없습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
                [],
            )

        disagreements = _nap_disagreements(sources)
        record = snippet_evidence(
            view.url,
            "external_source",
            repr(sources),
            excerpt=str(sources.get("official_record", sources["page"])),
            detail={"disagreeing_fields": disagreements},
        )
        value = {"disagreeing_fields": disagreements, "sources": sorted(sources)}

        if not disagreements:
            return (
                observed(
                    "geo.entity.nap_consistent",
                    CheckStatus.PASS,
                    confidence_level=MEDIUM if not official else HIGH,
                    note_ko="상호·주소·연락처가 모든 출처에서 일치합니다.",
                    evidence_ids=(*evidence_ids, record.evidence_id),
                    observed_value=value,
                ),
                None,
                [record],
            )

        outcome = observed(
            "geo.entity.nap_consistent",
            CheckStatus.FAIL,
            confidence_level=MEDIUM if not official else HIGH,
            note_ko="상호·주소·연락처가 출처마다 다릅니다: " + ", ".join(disagreements),
            evidence_ids=(*evidence_ids, record.evidence_id),
            observed_value=value,
        )
        issue = finding(
            "geo.entity.nap_consistent",
            title_ko="상호·주소·연락처가 서로 다릅니다",
            summary_ko=(
                "불일치 항목: " + ", ".join(disagreements) + ". 화면과 구조화 데이터, 공식 "
                "기록 가운데 어느 것이 맞는지 판단할 수 없습니다."
            ),
            remediation_ko="공식 기록을 기준으로 화면 표기와 구조화 데이터를 같게 맞추세요.",
            remediation_owner="BUSINESS_OWNER",
            urls=[view.url],
            evidence_ids=(record.evidence_id,),
            business_impact_ko="잘못된 주소·전화번호가 답변에 인용될 수 있습니다.",
        )
        return outcome, issue, [record]

    def _disambiguation_outcome(
        self, page: PageDocument, graph: EntityGraph, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        text = page.visible_text
        organization = graph.primary_organization()
        signals = {
            "locality": bool(_LOCALITY_PATTERN.search(text)),
            "founding_year": bool(_FOUNDING_PATTERN.search(text)),
            "registration_number": bool(_REGISTRATION_PATTERN.search(text)),
            "official_profiles": bool(organization and organization.same_as),
            "telephone": bool(visible_telephones(page)),
        }
        present = [name for name, ok in signals.items() if ok]
        value = {"signals": present}

        if len(present) >= _DISAMBIGUATION_STRONG:
            return observed(
                "geo.entity.disambiguation_signals",
                CheckStatus.PASS,
                confidence_level=LOW,
                note_ko="지역·연혁·등록정보 등으로 동명 브랜드와 구분됩니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        if len(present) >= _DISAMBIGUATION_WEAK:
            return observed(
                "geo.entity.disambiguation_signals",
                CheckStatus.WARNING,
                confidence_level=LOW,
                note_ko="구분 신호가 있지만 동명 브랜드와 섞일 여지가 남습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.entity.disambiguation_signals",
            CheckStatus.FAIL,
            confidence_level=LOW,
            note_ko="동명 브랜드와 구분할 신호가 거의 없습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _brand_candidates(page: PageDocument) -> tuple[str, ...]:
    """The one name this page presents as *the brand*, as opposed to its own title.

    Strictly one candidate per document, in order of how deliberate the declaration is.
    Taking several would make an ordinary page — ``og:site_name`` plus a descriptive
    title suffix — look like a naming conflict, and the check would fire on every site
    that writes "브랜드 — 무엇을 하는 곳인지" in its title.
    """
    if site_name := page.property_value("og:site_name"):
        return (normalise(site_name),)
    for match in _COPYRIGHT_PATTERN.finditer(page.furniture_text):
        if name := normalise(match.group(1)):
            return (name,)
    for separator in _SEPARATORS:
        if separator in page.title:
            if tail := normalise(page.title.rsplit(separator, 1)[-1]):
                return (tail,)
            break
    return ()


def _strip_legal_form(name: str) -> str:
    lowered = name.lower()
    for form in _LEGAL_FORMS:
        lowered = lowered.replace(form, "")
    return "".join(lowered.split())


def _official_record(context: CollectionContext) -> Mapping[str, Any]:
    if not context.provider_is_enabled(OFFICIAL_RECORD_PROVIDER):
        return {}
    payload = context.provider_payloads.get(OFFICIAL_RECORD_PROVIDER)
    return payload if isinstance(payload, dict) else {}


def _nap_disagreements(sources: Mapping[str, Mapping[str, Any]]) -> list[str]:
    disagreeing: list[str] = []
    for field_name, comparer in (
        ("name", _names_agree),
        ("telephone", _telephones_agree),
        ("address", _addresses_agree),
    ):
        values = [str(source.get(field_name) or "") for source in sources.values()]
        stated = [value for value in values if value]
        if len(stated) < 2:
            continue
        if not all(comparer(stated[0], other) for other in stated[1:]):
            disagreeing.append(field_name)
    return disagreeing


def _names_agree(left: str, right: str) -> bool:
    return _strip_legal_form(left) == _strip_legal_form(right)


def _telephones_agree(left: str, right: str) -> bool:
    return _digits(left) == _digits(right)


def _addresses_agree(left: str, right: str) -> bool:
    left_tokens = _address_tokens(left)
    right_tokens = _address_tokens(right)
    if not left_tokens or not right_tokens:
        return True
    return bool(left_tokens & right_tokens)


def _address_tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", value) if not token.isdigit()}


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


__all__ = ["CHECK_IDS", "OFFICIAL_RECORD_PROVIDER", "EntityClarityCollector"]
