"""외부 검증 가능성 — does anyone other than the site itself say so.

Every check in this category needs material VEO does not hold: directory records, press,
registries, review platforms. When no such provider is configured, all four checks are
UNKNOWN. That is the point of ADR 0004 — a provider that is switched off is a first-class
state, not a reason to guess a value or to mark a site down for our own missing wiring.

The payload this collector reads is supplied by the corroboration provider under the key
``geo_external`` and is shaped as ``{"entity_name": str, "sources": [...]}``. See
``INTEGRATION_REQUEST.md`` for the field-by-field contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    unknown_outcome,
)
from veo.geo.reporting import OUTSIDE, finding, observed, snippet_evidence
from veo.geo.view import TargetView, build_view
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.external.independent_sources_exist",
        "geo.external.official_profiles_claimed",
        "geo.external.source_type_diversity",
        "geo.external.facts_agree_across_sources",
    }
)

CORROBORATION_PROVIDER = "geo_external"

#: Two independent voices is the minimum that stops a claim being self-reported.
_ENOUGH_INDEPENDENT_SOURCES = 2
#: Three kinds of source — say a registry, a directory and press — is meaningfully diverse.
_ENOUGH_SOURCE_TYPES = 3


class ExternalVerifiabilityCollector:
    """Observes whether outside sources corroborate the entity."""

    category_id = "external_verifiability"

    @property
    def check_ids(self) -> frozenset[str]:
        return CHECK_IDS

    def collect(self, context: CollectionContext) -> CollectionResult:
        if not context.provider_is_enabled(CORROBORATION_PROVIDER):
            state = context.provider_states.get(CORROBORATION_PROVIDER)
            reason = (
                f"외부 대조 제공자가 사용 불가 상태입니다({state})."
                if state is not None
                else "외부 대조 제공자가 연결되지 않아 확인할 수 없습니다."
            )
            return CollectionResult(
                outcomes=tuple(unknown_outcome(check_id, reason) for check_id in sorted(CHECK_IDS))
            )

        payload = context.provider_payloads.get(CORROBORATION_PROVIDER)
        if not isinstance(payload, dict):
            reason = "외부 대조 제공자가 응답을 반환하지 않았습니다."
            return CollectionResult(
                outcomes=tuple(unknown_outcome(check_id, reason) for check_id in sorted(CHECK_IDS))
            )

        view = build_view(context)
        sources = _sources(payload)
        record = snippet_evidence(
            view.url,
            "external_source",
            repr(sources),
            excerpt=", ".join(str(s.get("url", "")) for s in sources)[:400],
            detail={"source_count": len(sources)},
        )
        evidence: list[EvidenceRecord] = [record]
        issues: list[IssueDraft] = []
        ids = (record.evidence_id,)

        independent = [s for s in sources if s.get("independent")]
        claimed = [s for s in sources if s.get("claimed_profile")]
        types = sorted({str(s.get("source_type") or "UNKNOWN") for s in sources})
        organization = view.graph.primary_organization()
        declared_profiles = set(organization.same_as) if organization else set()

        outcomes: list[CheckOutcome] = [
            self._independence_outcome(independent, sources, ids),
            self._profiles_outcome(claimed, declared_profiles, ids),
            self._diversity_outcome(types, ids),
        ]
        agreement_outcome, agreement_issue = self._agreement_outcome(
            payload, sources, view, ids
        )
        outcomes.append(agreement_outcome)
        if agreement_issue is not None:
            issues.append(agreement_issue)

        if outcomes[0].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.external.independent_sources_exist",
                    title_ko="독립적인 외부 출처가 없습니다",
                    summary_ko=(
                        "확인된 출처가 자사 채널뿐입니다. 자기 진술만으로는 엔터티가 "
                        "외부에서 확인되지 않습니다."
                    ),
                    remediation_ko=(
                        "공공 등록 정보, 업종 디렉터리, 보도 자료 등에 정보를 등재하세요."
                    ),
                    remediation_owner="MARKETER",
                    urls=[view.url],
                    evidence_ids=ids,
                )
            )

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=tuple(evidence), issues=tuple(issues)
        )

    # ------------------------------------------------------------------ #

    def _independence_outcome(
        self,
        independent: Sequence[Mapping[str, Any]],
        sources: Sequence[Mapping[str, Any]],
        evidence_ids: tuple[str, ...],
    ) -> CheckOutcome:
        value = {"independent": len(independent), "total": len(sources)}
        if len(independent) >= _ENOUGH_INDEPENDENT_SOURCES:
            status, note = CheckStatus.PASS, "독립적인 외부 출처에서 확인됩니다."
        elif independent:
            status, note = CheckStatus.WARNING, "독립적인 외부 출처가 하나뿐입니다."
        else:
            status, note = CheckStatus.FAIL, "독립적인 외부 출처가 없습니다."
        return observed(
            "geo.external.independent_sources_exist",
            status,
            confidence_level=OUTSIDE,
            note_ko=note,
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _profiles_outcome(
        self,
        claimed: Sequence[Mapping[str, Any]],
        declared_profiles: set[str],
        evidence_ids: tuple[str, ...],
    ) -> CheckOutcome:
        linked = [s for s in claimed if str(s.get("url", "")) in declared_profiles]
        value = {"claimed": len(claimed), "linked_from_site": len(linked)}
        if claimed and linked:
            status, note = CheckStatus.PASS, "확보된 공식 프로필이 사이트에서도 연결됩니다."
        elif claimed:
            status, note = (
                CheckStatus.WARNING,
                "공식 프로필은 확보했지만 사이트가 그것을 가리키지 않습니다.",
            )
        else:
            status, note = CheckStatus.FAIL, "확보·정비된 공식 프로필이 없습니다."
        return observed(
            "geo.external.official_profiles_claimed",
            status,
            confidence_level=OUTSIDE,
            note_ko=note,
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _diversity_outcome(
        self, types: Sequence[str], evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        value = {"source_types": list(types)}
        if len(types) >= _ENOUGH_SOURCE_TYPES:
            status, note = CheckStatus.PASS, "출처 유형이 충분히 다양합니다."
        elif len(types) == 2:
            status, note = CheckStatus.WARNING, "출처 유형이 두 가지뿐입니다."
        else:
            status, note = CheckStatus.FAIL, "출처 유형이 한 가지에 몰려 있습니다."
        return observed(
            "geo.external.source_type_diversity",
            status,
            confidence_level=OUTSIDE,
            note_ko=note,
            evidence_ids=evidence_ids,
            observed_value=value,
        )

    def _agreement_outcome(
        self,
        payload: Mapping[str, Any],
        sources: Sequence[Mapping[str, Any]],
        view: TargetView,
        evidence_ids: tuple[str, ...],
    ) -> tuple[CheckOutcome, IssueDraft | None]:
        organization = view.graph.primary_organization()
        own_name = (
            (organization.name if organization else "")
            or view.page.property_value("og:site_name")
            or str(payload.get("entity_name") or "")
        )
        own = {
            "name": own_name,
            "telephone": organization.telephone if organization else "",
            "address": organization.address_text if organization else "",
        }

        conflicts: list[str] = []
        compared = 0
        for source in sources:
            facts = source.get("facts")
            if not isinstance(facts, dict):
                continue
            for key, stated in facts.items():
                ours = own.get(key, "")
                if not ours or not isinstance(stated, str) or not stated:
                    continue
                compared += 1
                if not _values_agree(key, ours, stated):
                    conflicts.append(f"{source.get('url', '?')}::{key}")

        value = {"compared": compared, "conflicts": conflicts}
        if compared == 0:
            return (
                unknown_outcome(
                    "geo.external.facts_agree_across_sources",
                    "대조할 수 있는 공통 항목이 없어 사실 일치를 확인하지 못했습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
            )
        if not conflicts:
            return (
                observed(
                    "geo.external.facts_agree_across_sources",
                    CheckStatus.PASS,
                    confidence_level=OUTSIDE,
                    note_ko="외부 출처의 핵심 사실이 자사 정보와 일치합니다.",
                    evidence_ids=evidence_ids,
                    observed_value=value,
                ),
                None,
            )
        outcome = observed(
            "geo.external.facts_agree_across_sources",
            CheckStatus.FAIL,
            confidence_level=OUTSIDE,
            note_ko="외부 출처와 자사 정보가 어긋납니다: "
            + ", ".join(conflicts[:3]),
            evidence_ids=evidence_ids,
            observed_value=value,
        )
        issue = finding(
            "geo.external.facts_agree_across_sources",
            title_ko="외부 출처와 자사 정보가 다릅니다",
            summary_ko="불일치: " + ", ".join(conflicts[:5]),
            remediation_ko="외부 등록 정보를 최신 상호·주소·연락처로 정정 신청하세요.",
            remediation_owner="BUSINESS_OWNER",
            urls=[view.url],
            evidence_ids=evidence_ids,
            business_impact_ko="답변 엔진이 어느 정보를 믿을지 판단하지 못합니다.",
        )
        return outcome, issue


def _sources(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = payload.get("sources")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _values_agree(key: str, ours: str, theirs: str) -> bool:
    if key == "telephone":
        return _digits(ours) == _digits(theirs)
    if key == "address":
        ours_tokens = _tokens(ours)
        theirs_tokens = _tokens(theirs)
        return not ours_tokens or not theirs_tokens or bool(ours_tokens & theirs_tokens)
    return _squash(ours) == _squash(theirs)


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _squash(value: str) -> str:
    lowered = value.lower()
    for form in ("주식회사", "(주)", "inc.", "ltd.", "co.", "llc"):
        lowered = lowered.replace(form, "")
    return "".join(lowered.split())


def _tokens(value: str) -> set[str]:
    return {token for token in value.replace(",", " ").split() if len(token) >= 2}


__all__ = ["CHECK_IDS", "CORROBORATION_PROVIDER", "ExternalVerifiabilityCollector"]
