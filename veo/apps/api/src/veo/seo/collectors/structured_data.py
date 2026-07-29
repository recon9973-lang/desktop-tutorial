"""구조화 데이터 — and the clearest place in the product where **N/A is not zero**.

A brochure site that declares no JSON-LD has not failed anything. There is nothing to
parse, nothing to validate and nothing that could contradict the page, so all five
checks report NOT_APPLICABLE and the whole category leaves the denominator. Marking them
FAIL would punish a site for the absence of an optional enhancement, and the resulting
number would be a lie about what was measured.

The second rule here is narrower but just as important: VEO does not know every type on
schema.org. When a page declares a type this module has no requirements table for, the
required-properties check reports UNKNOWN. Guessing would invent a finding.
"""

from __future__ import annotations

import json
from typing import Any, Final

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.scoring import CheckOutcome, CheckStatus
from veo.seo.collectors.base import (
    HEURISTIC_MEDIUM,
    NO_DOCUMENTS_KO,
    EvidenceLedger,
    SeoCollector,
    all_unknown,
    issue,
    url_ratio_outcome,
)
from veo.seo.observation import PageObservation, SiteObservation
from veo.seo.parsing import normalise

#: Properties without which a declared type cannot produce a rich result. Types absent
#: from this table are reported as UNKNOWN, never as failures.
REQUIRED_PROPERTIES: dict[str, frozenset[str]] = {
    "article": frozenset({"headline"}),
    "newsarticle": frozenset({"headline"}),
    "blogposting": frozenset({"headline"}),
    "breadcrumblist": frozenset({"itemlistelement"}),
    "dentist": frozenset({"name", "address"}),
    "event": frozenset({"name", "startdate"}),
    "faqpage": frozenset({"mainentity"}),
    "hospital": frozenset({"name", "address"}),
    "localbusiness": frozenset({"name", "address"}),
    "medicalbusiness": frozenset({"name", "address"}),
    "medicalclinic": frozenset({"name", "address"}),
    "organization": frozenset({"name"}),
    "person": frozenset({"name"}),
    "physician": frozenset({"name", "address"}),
    "product": frozenset({"name"}),
    "recipe": frozenset({"name"}),
    "videoobject": frozenset({"name", "thumbnailurl", "uploaddate"}),
    "website": frozenset({"name", "url"}),
}

#: Types Google documents as eligible for a rich result.
GOOGLE_SUPPORTED_TYPES = frozenset(
    {
        "article",
        "blogposting",
        "breadcrumblist",
        "course",
        "dataset",
        "dentist",
        "event",
        "faqpage",
        "hospital",
        "howto",
        "jobposting",
        "localbusiness",
        "medicalbusiness",
        "medicalclinic",
        "newsarticle",
        "organization",
        "person",
        "physician",
        "product",
        "profilepage",
        "qapage",
        "recipe",
        "review",
        "softwareapplication",
        "specialannouncement",
        "videoobject",
        "website",
    }
)

#: Open Graph properties Naver relies on alongside structured data.
NO_STRUCTURED_DATA_KO = (
    "구조화 데이터를 선언하지 않은 사이트입니다. 선택 항목이므로 감점하지 않으며, "
    "도입하면 평가 대상이 됩니다."
)


class StructuredDataCollector(SeoCollector):
    category_id = "structured_data"
    check_id_list = (
        "seo.sd.jsonld_parses",
        "seo.sd.required_properties_present",
        "seo.sd.matches_visible_content",
        "seo.sd.google_supported_type",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        site = self.observe(context)
        if not site.has_pages:
            return all_unknown(self.check_id_list, NO_DOCUMENTS_KO)

        declaring = [page for page in site.pages if page.raw.json_ld_blocks]
        if not declaring:
            return CollectionResult(
                outcomes=tuple(
                    not_applicable_outcome(check_id, NO_STRUCTURED_DATA_KO)
                    for check_id in self.check_id_list
                ),
                notes_ko=(NO_STRUCTURED_DATA_KO,),
            )

        ledger = EvidenceLedger()
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        parsed = {page.url: _parse_blocks(page) for page in declaring}

        for step in (_parses, _required_properties, _matches_visible, _google_type):
            produced, produced_issues = step(context, site, ledger, declaring, parsed)
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


class _Blocks:
    """The JSON-LD on one page, split into what parsed and what did not."""

    def __init__(self) -> None:
        self.objects: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.raw: list[str] = []


def _parse_blocks(page: PageObservation) -> _Blocks:
    blocks = _Blocks()
    for raw in page.raw.json_ld_blocks:
        blocks.raw.append(raw)
        try:
            document = json.loads(raw)
        except (ValueError, RecursionError) as exc:
            blocks.errors.append(str(exc))
            continue
        blocks.objects.extend(_flatten(document))
    return blocks


def _flatten(document: Any) -> list[dict[str, Any]]:
    """Every node that declares a ``@type``, including ``@graph`` members."""
    found: list[dict[str, Any]] = []
    if isinstance(document, list):
        for item in document:
            found.extend(_flatten(item))
        return found
    if not isinstance(document, dict):
        return found
    if "@graph" in document:
        found.extend(_flatten(document["@graph"]))
    if "@type" in document:
        found.append(document)
    return found


def _types(node: dict[str, Any]) -> list[str]:
    declared = node.get("@type")
    if isinstance(declared, str):
        return [declared.lower()]
    if isinstance(declared, list):
        return [str(item).lower() for item in declared]
    return []


def _lower_keys(node: dict[str, Any]) -> set[str]:
    return {str(key).lower() for key in node}


# --------------------------------------------------------------------------- #
# seo.sd.jsonld_parses
# --------------------------------------------------------------------------- #


def _parses(
    context: CollectionContext,
    site: SiteObservation,
    ledger: EvidenceLedger,
    declaring: list[PageObservation],
    parsed: dict[str, _Blocks],
) -> tuple[CheckOutcome, list[IssueDraft]]:
    broken = [page for page in declaring if parsed[page.url].errors]
    evidence = [
        ledger.of(
            "dom_snippet",
            url=page.url,
            payload="\n".join(parsed[page.url].raw),
            excerpt=(
                "; ".join(parsed[page.url].errors)
                if parsed[page.url].errors
                else parsed[page.url].raw[0][:300]
            ),
            detail={"blocks": len(parsed[page.url].raw), "errors": parsed[page.url].errors},
        )
        for page in (broken or declaring[:1])
    ]

    result = url_ratio_outcome(
        "seo.sd.jsonld_parses",
        affected=broken,
        evaluated=declaring,
        evidence_ids=evidence,
        observed_value={page.url: parsed[page.url].errors for page in broken} or None,
        clean_note_ko="선언된 JSON-LD가 모두 문법 오류 없이 파싱됩니다.",
        affected_note_ko=f"{len(broken)}개 페이지의 JSON-LD에 문법 오류가 있습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.sd.jsonld_parses",
            title_ko="JSON-LD에 문법 오류가 있습니다",
            summary_ko=(
                f"{len(broken)}개 페이지의 구조화 데이터가 JSON으로 읽히지 않습니다. "
                "검색엔진은 이 블록 전체를 무시합니다."
            ),
            affected_urls=[page.url for page in broken],
            evidence_ids=evidence,
            remediation_ko=(
                "마지막 항목 뒤의 쉼표, 닫히지 않은 괄호, 큰따옴표가 아닌 따옴표를 확인하십시오. "
                "템플릿에서 값을 끼워 넣는 경우 값 안의 따옴표를 escape 처리해야 합니다."
            ),
            reverification_ko="수정 후 재수집해 JSON-LD 블록이 파싱되는지 확인합니다.",
            business_impact_ko="리치 결과가 전혀 표시되지 않아 검색 결과에서 눈에 덜 띕니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.sd.required_properties_present
# --------------------------------------------------------------------------- #


def _required_properties(
    context: CollectionContext,
    site: SiteObservation,
    ledger: EvidenceLedger,
    declaring: list[PageObservation],
    parsed: dict[str, _Blocks],
) -> tuple[CheckOutcome, list[IssueDraft]]:
    known: list[PageObservation] = []
    problems: dict[str, list[str]] = {}

    for page in declaring:
        page_has_known_type = False
        missing: list[str] = []
        for node in parsed[page.url].objects:
            for declared in _types(node):
                required = REQUIRED_PROPERTIES.get(declared)
                if required is None:
                    continue
                page_has_known_type = True
                absent = sorted(required - _lower_keys(node))
                if absent:
                    missing.append(f"{declared}: {', '.join(absent)} 없음")
        if page_has_known_type:
            known.append(page)
            if missing:
                problems[page.url] = missing

    if not known:
        return (
            unknown_outcome(
                "seo.sd.required_properties_present",
                "선언된 타입에 대한 필수 속성 기준을 VEO가 가지고 있지 않아 판단하지 않았습니다. "
                "추측으로 오류를 만들지 않습니다.",
            ),
            [],
        )

    affected = [page for page in known if page.url in problems]
    evidence = [
        ledger.of(
            "validator_output",
            url=page.url,
            payload="\n".join(problems.get(page.url, ["필수 속성 충족"])),
            excerpt="; ".join(problems.get(page.url, ["필수 속성 충족"])),
            detail={"missing": problems.get(page.url, [])},
        )
        for page in (affected or known[:1])
    ]

    result = url_ratio_outcome(
        "seo.sd.required_properties_present",
        affected=affected,
        evaluated=known,
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko="선언한 타입의 필수 속성이 모두 채워져 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지에서 필수 속성이 빠져 있습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.sd.required_properties_present",
            title_ko="구조화 데이터의 필수 속성이 빠져 있습니다",
            summary_ko="; ".join(
                f"{url} — {', '.join(values)}" for url, values in list(problems.items())[:5]
            ),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                "선언한 타입에서 요구하는 속성을 모두 채우십시오. 값이 없는 속성은 빈 문자열로 "
                "남기지 말고 실제 값을 넣거나, 채울 수 없다면 그 타입 선언 자체를 빼는 편이 "
                "낫습니다."
            ),
            reverification_ko="수정 후 재수집해 각 타입의 필수 속성이 채워졌는지 확인합니다.",
            business_impact_ko=(
                "속성이 빠지면 리치 결과 자격이 사라져 구조화 데이터를 넣은 효과가 없습니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.sd.matches_visible_content
# --------------------------------------------------------------------------- #


#: 화면과 대조할 값들. `name`/`headline` 만 보던 시절에는 정작 꾸며지는 값 —
#: 평점, 후기 수, 전화번호, 주소 — 을 아무도 보지 않았다.
_CLAIMED_TEXT: Final = ("name", "headline", "telephone", "address")
_CLAIMED_LABELS_KO: Final = {
    "telephone": "전화번호",
    "address": "주소",
    "ratingvalue": "평점",
    "reviewcount": "후기 수",
    "ratingcount": "평가 수",
}


def _digits(text: str) -> str:
    """숫자만 남긴다. `02-555-1234` 와 `02) 555-1234` 를 같은 것으로 보기 위해서다."""
    return "".join(ch for ch in text if ch.isdigit())


def _national_number(value: str) -> str:
    """국제 표기를 국내 표기로 맞춘다.

    `+82-2-000-0000` 과 `02-000-0000` 은 같은 번호다 — 국제 표기는 시외국번 앞의 0 을
    빼고 국가번호 82 를 붙인다. schema.org 는 국제 표기를 권장하므로, 이 둘을 다른
    값으로 보면 **제대로 만든 사이트일수록 어긋난다고 보고**하게 된다.
    """
    digits = _digits(value)
    if digits.startswith("82"):
        return "0" + digits[2:]
    return digits


def _flat_text(value: object) -> str:
    """주소는 문자열일 수도 `PostalAddress` 객체일 수도 있다. 둘 다 사람이 읽는 값으로."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = [_flat_text(v) for k, v in value.items() if not str(k).startswith("@")]
        return " ".join(part for part in parts if part)
    if isinstance(value, list):
        return " ".join(part for part in (_flat_text(v) for v in value) if part)
    return ""


def _claims(node: dict[str, Any]) -> list[tuple[str, str]]:
    """이 노드가 주장하는 값들. (사람이 읽을 이름, 값)"""
    found: list[tuple[str, str]] = []
    lowered = {str(k).lower(): v for k, v in node.items()}

    for key in _CLAIMED_TEXT:
        text = _flat_text(lowered.get(key))
        if text:
            found.append((_CLAIMED_LABELS_KO.get(key, ""), text))

    # 평점과 후기 수는 화면에 없으면 지어낸 값이다. 구글 정책 위반이자, 병원이라면
    # 의료법 제56조가 금지하는 환자 후기·평가 광고에 해당한다.
    rating = lowered.get("aggregaterating")
    if isinstance(rating, dict):
        inner = {str(k).lower(): v for k, v in rating.items()}
        for key in ("ratingvalue", "reviewcount", "ratingcount"):
            text = _flat_text(inner.get(key))
            if text:
                found.append((_CLAIMED_LABELS_KO[key], text))
    return found


def _is_visible(value: str, visible: str, digits_visible: str) -> bool:
    """화면에서 확인되는가.

    숫자만으로 이루어진 값(전화번호·평점·후기 수)은 표기가 제각각이라 문자열로 맞대면
    멀쩡한 페이지가 실패한다. 숫자만 뽑아 한 번 더 본다.
    """
    if normalise(value) in visible:
        return True
    digits = _national_number(value)
    return bool(digits) and digits in digits_visible


def _matches_visible(
    context: CollectionContext,
    site: SiteObservation,
    ledger: EvidenceLedger,
    declaring: list[PageObservation],
    parsed: dict[str, _Blocks],
) -> tuple[CheckOutcome, list[IssueDraft]]:
    mismatched: list[PageObservation] = []
    problems: dict[str, list[str]] = {}

    for page in declaring:
        visible = normalise(page.raw.full_text)
        # 화면 쪽도 같은 규칙으로 맞춘다 — 어느 쪽이 국제 표기든 대조되도록.
        digits_visible = (
            _digits(page.raw.full_text) + " " + _national_number(page.raw.full_text)
        )
        absent: list[str] = []

        for node in parsed[page.url].objects:
            for label, value in _claims(node):
                if _is_visible(value, visible, digits_visible):
                    continue
                absent.append(f"{label} {value}" if label else value)

        if absent:
            mismatched.append(page)
            problems[page.url] = absent

    evidence = [
        ledger.of(
            "text_extract",
            url=page.url,
            payload=page.raw.full_text,
            excerpt=(
                "화면에 없는 선언값: " + ", ".join(problems[page.url])
                if page.url in problems
                else page.raw.full_text[:200]
            ),
            detail={"absent": problems.get(page.url, [])},
        )
        for page in (mismatched or declaring[:1])
    ]

    result = url_ratio_outcome(
        "seo.sd.matches_visible_content",
        affected=mismatched,
        evaluated=declaring,
        confidence_level=HEURISTIC_MEDIUM,
        evidence_ids=evidence,
        observed_value=problems or None,
        clean_note_ko="구조화 데이터가 선언한 값이 화면에서도 모두 확인됩니다.",
        affected_note_ko=(
            f"{len(mismatched)}개 페이지의 구조화 데이터가 화면 내용과 어긋납니다. "
            # 무엇이 어긋났는지 말하지 않으면 어디를 고쳐야 할지 알 수 없다.
            + "화면에서 확인되지 않는 값: "
            + ", ".join(sorted({v for values in problems.values() for v in values})[:6])
        ),
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.sd.matches_visible_content",
            title_ko="구조화 데이터가 화면에 없는 내용을 선언합니다",
            summary_ko="; ".join(
                f"{url} — “{', '.join(values)}”가 화면에 없습니다"
                for url, values in list(problems.items())[:5]
            ),
            affected_urls=list(problems),
            evidence_ids=evidence,
            remediation_ko=(
                "구조화 데이터의 name·headline은 페이지에 실제로 보이는 문구와 같아야 합니다. "
                "화면에 없는 값을 선언하면 스팸 정책 위반으로 처리될 수 있으므로, 값을 화면에 "
                "표시하거나 선언에서 빼십시오."
            ),
            reverification_ko="수정 후 재수집해 선언값이 본문에서 확인되는지 다시 비교합니다.",
            business_impact_ko=(
                "정책 위반으로 판단되면 리치 결과가 사이트 단위로 제한될 수 있습니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.sd.google_supported_type
# --------------------------------------------------------------------------- #


def _google_type(
    context: CollectionContext,
    site: SiteObservation,
    ledger: EvidenceLedger,
    declaring: list[PageObservation],
    parsed: dict[str, _Blocks],
) -> tuple[CheckOutcome, list[IssueDraft]]:
    unsupported: dict[str, list[str]] = {}
    evaluated: list[PageObservation] = []

    for page in declaring:
        declared = [name for node in parsed[page.url].objects for name in _types(node)]
        if not declared:
            continue
        evaluated.append(page)
        outside = sorted({name for name in declared if name not in GOOGLE_SUPPORTED_TYPES})
        if outside and not any(name in GOOGLE_SUPPORTED_TYPES for name in declared):
            unsupported[page.url] = outside

    if not evaluated:
        return (
            unknown_outcome(
                "seo.sd.google_supported_type",
                "파싱된 구조화 데이터에 @type 선언이 없어 지원 여부를 판단하지 못했습니다.",
            ),
            [],
        )

    affected = [page for page in evaluated if page.url in unsupported]
    evidence = [
        ledger.of(
            "validator_output",
            url=page.url,
            payload=", ".join(unsupported.get(page.url, ["지원 타입"])),
            excerpt="Google 리치 결과 미지원 타입: " + ", ".join(unsupported.get(page.url, [])),
            detail={"unsupported": unsupported.get(page.url, [])},
        )
        for page in (affected or evaluated[:1])
    ]

    result = url_ratio_outcome(
        "seo.sd.google_supported_type",
        affected=affected,
        evaluated=evaluated,
        evidence_ids=evidence,
        observed_value=unsupported or None,
        clean_note_ko="Google이 리치 결과로 지원하는 타입을 선언하고 있습니다.",
        affected_note_ko=f"{len(affected)}개 페이지가 지원되지 않는 타입만 선언합니다.",
        warning=True,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    return result, [
        issue(
            context,
            "seo.sd.google_supported_type",
            title_ko="Google이 리치 결과로 지원하지 않는 타입만 선언되어 있습니다",
            summary_ko="; ".join(
                f"{url} — {', '.join(values)}" for url, values in list(unsupported.items())[:5]
            ),
            affected_urls=list(unsupported),
            evidence_ids=evidence,
            remediation_ko=(
                "페이지 성격에 맞는 지원 타입을 함께 선언하십시오. 안내 문서라면 Article, "
                "지점 정보라면 LocalBusiness, 목록 경로라면 BreadcrumbList가 맞습니다."
            ),
            reverification_ko="추가 후 재수집해 지원 타입이 선언되었는지 확인합니다.",
            business_impact_ko="검색 결과에 별점·경로·FAQ 같은 추가 표시가 나타나지 않습니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.sd.naver_supported_type
# --------------------------------------------------------------------------- #


