"""Shared machinery for the eight SEO collectors.

Everything in this module is about *reporting*, never about scoring. The helpers build
the three shapes a collector is allowed to hand back — an outcome, an evidence record
and an issue draft — and they refuse to let a collector invent the one field it must
never choose for itself: an issue's owner always comes from the specification.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, ClassVar

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.contracts.enums import ProviderState
from veo.scoring import CheckOutcome, CheckStatus
from veo.seo.observation import PageObservation, SiteObservation, build_observation

#: Confidence vocabulary, taken from the specification's ``confidence_levels`` table.
#: These are labels, not numbers — the evaluator resolves them.
DIRECT = "DIRECT_OBSERVATION"
OFFICIAL_API = "OFFICIAL_API"
HEURISTIC_HIGH = "HEURISTIC_HIGH"
HEURISTIC_MEDIUM = "HEURISTIC_MEDIUM"


class EvidenceLedger:
    """Collects the evidence one ``collect()`` call referred to, without duplicates."""

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def add(self, record: EvidenceRecord) -> str:
        self._records.setdefault(record.evidence_id, record)
        return record.evidence_id

    def of(
        self,
        kind: str,
        *,
        url: str | None,
        payload: bytes | str,
        excerpt: str = "",
        detail: Mapping[str, object] | None = None,
    ) -> str:
        return self.add(
            EvidenceRecord.of(kind, url=url, payload=payload, excerpt=excerpt, detail=detail)
        )

    def page_snippet(self, page: PageObservation, kind: str, excerpt: str) -> str:
        return self.of(
            kind,
            url=page.url,
            payload=page.document.body or page.url.encode("utf-8"),
            excerpt=excerpt,
            detail={"status": page.status, "importance": page.importance},
        )

    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records.values())


class SeoCollector:
    """Base class carrying the parts every SEO collector repeats.

    A collector declares its check ids as a class attribute so the suite can compare them
    against the published specification without instantiating a crawl.
    """

    category_id: ClassVar[str] = ""
    check_id_list: ClassVar[tuple[str, ...]] = ()

    def __init__(self, observation: SiteObservation | None = None) -> None:
        self._observation = observation

    @property
    def check_ids(self) -> frozenset[str]:
        return frozenset(self.check_id_list)

    def collect(self, context: CollectionContext) -> CollectionResult:  # pragma: no cover
        raise NotImplementedError

    def observe(self, context: CollectionContext) -> SiteObservation:
        if self._observation is not None and self._observation.context is context:
            return self._observation
        return build_observation(context)


# --------------------------------------------------------------------------- #
# Outcomes
# --------------------------------------------------------------------------- #


def outcome(
    check_id: str,
    status: CheckStatus,
    *,
    confidence_level: str = DIRECT,
    affected: float = 1.0,
    evaluated: float = 1.0,
    evidence_ids: Sequence[str] = (),
    observed_value: Any = None,
    note: str | None = None,
) -> CheckOutcome:
    """A plain observation. No severity, no points — the evaluator supplies both."""
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence_level=confidence_level,
        affected_weight=round(affected, 6),
        evaluated_weight=round(evaluated, 6),
        evidence_ids=tuple(evidence_ids),
        observed_value=observed_value,
        note=note,
    )


def url_ratio_outcome(
    check_id: str,
    *,
    affected: Sequence[PageObservation],
    evaluated: Sequence[PageObservation],
    confidence_level: str = DIRECT,
    evidence_ids: Sequence[str] = (),
    observed_value: Any = None,
    clean_note_ko: str | None = None,
    affected_note_ko: str | None = None,
    warning: bool = False,
) -> CheckOutcome:
    """Report a URL-scope check over several pages, weighted by URL importance.

    The importance table comes from the specification. The collector never decides how
    much a home page is worth relative to a tag page; it only counts which pages are
    affected out of which were evaluated.
    """
    evaluated_total = sum(page.importance_value for page in evaluated)
    affected_total = sum(page.importance_value for page in affected)

    if not evaluated:
        return unknown_outcome(check_id, affected_note_ko or "평가할 수 있는 URL이 없습니다.")

    if evaluated_total <= 0.0:
        return not_applicable_outcome(
            check_id, "평가 대상 URL이 모두 의도된 색인 제외 페이지입니다."
        )

    if not affected:
        return outcome(
            check_id,
            CheckStatus.PASS,
            confidence_level=confidence_level,
            affected=0.0,
            evaluated=evaluated_total,
            evidence_ids=evidence_ids,
            observed_value=observed_value,
            note=clean_note_ko,
        )

    return outcome(
        check_id,
        CheckStatus.WARNING if warning else CheckStatus.FAIL,
        confidence_level=confidence_level,
        affected=affected_total,
        evaluated=evaluated_total,
        evidence_ids=evidence_ids,
        observed_value=observed_value,
        note=affected_note_ko,
    )


def site_outcome(
    check_id: str,
    *,
    passed: bool,
    confidence_level: str = DIRECT,
    evidence_ids: Sequence[str] = (),
    observed_value: Any = None,
    note: str | None = None,
    warning: bool = False,
) -> CheckOutcome:
    """A site-scope yes/no observation, at full coverage either way."""
    status = CheckStatus.PASS if passed else (
        CheckStatus.WARNING if warning else CheckStatus.FAIL
    )
    return outcome(
        check_id,
        status,
        confidence_level=confidence_level,
        affected=0.0 if passed else 1.0,
        evaluated=1.0,
        evidence_ids=evidence_ids,
        observed_value=observed_value,
        note=note,
    )


# --------------------------------------------------------------------------- #
# Issues
# --------------------------------------------------------------------------- #


def issue(
    context: CollectionContext,
    check_id: str,
    *,
    title_ko: str,
    summary_ko: str,
    affected_urls: Iterable[str],
    evidence_ids: Iterable[str],
    remediation_ko: str,
    reverification_ko: str,
    business_impact_ko: str = "",
    fix_example: str | None = None,
) -> IssueDraft:
    """Build an issue whose owner and title come from the published specification.

    A collector may describe what it saw and what to do about it. It may not decide who
    is accountable — that is a field of the check, and letting a checker pick it would
    put the routing of work in eight different places.
    """
    spec_check = context.spec.check(check_id)
    return IssueDraft(
        check_id=check_id,
        title_ko=title_ko or spec_check.title_ko,
        summary_ko=summary_ko,
        affected_urls=tuple(dict.fromkeys(affected_urls)),
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        remediation_ko=remediation_ko,
        remediation_owner=spec_check.remediation_owner,
        business_impact_ko=business_impact_ko,
        fix_example=fix_example,
        reverification_note_ko=reverification_ko,
    )


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #


def provider_payload(
    context: CollectionContext, provider: str
) -> tuple[Mapping[str, Any] | None, str | None]:
    """The provider's answer, or the Korean reason there is not one.

    Never a guess. A missing credential, a degraded provider and an empty response are
    all reported as UNKNOWN with the reason spelled out, because a number VEO invented
    is worse than a gap VEO admitted.
    """
    state = context.provider_states.get(provider)
    if state is None:
        return None, f"{_provider_name_ko(provider)} 연동이 구성되어 있지 않아 측정하지 못했습니다."
    if state is not ProviderState.ENABLED:
        return None, (
            f"{_provider_name_ko(provider)} 연동 상태가 {_state_ko(state)}이라 "
            "측정하지 못했습니다."
        )

    payload = context.provider_payloads.get(provider)
    if not isinstance(payload, Mapping) or not payload:
        return None, f"{_provider_name_ko(provider)}에서 받은 응답이 없어 측정하지 못했습니다."
    return payload, None


_PROVIDER_NAMES_KO = {
    "GOOGLE_PAGESPEED": "Google PageSpeed Insights",
    "GOOGLE_CRUX": "Chrome UX 리포트(CrUX)",
    "GOOGLE_SEARCH_CONSOLE": "Google Search Console",
    "NAVER_SEARCH_ADVISOR": "네이버 서치어드바이저",
    "INDEXNOW": "IndexNow",
    "BACKLINK_INDEX": "백링크 색인",
    "BRAND_MENTIONS": "브랜드 언급 수집",
}

_STATE_NAMES_KO = {
    ProviderState.DISABLED_NO_CREDENTIAL: "자격증명 없음",
    ProviderState.DISABLED_BY_CONFIG: "설정으로 비활성화",
    ProviderState.DEGRADED: "일시적 장애",
    ProviderState.CIRCUIT_OPEN: "회로 차단",
}


def _provider_name_ko(provider: str) -> str:
    return _PROVIDER_NAMES_KO.get(provider, provider)


def _state_ko(state: ProviderState) -> str:
    return _STATE_NAMES_KO.get(state, str(state))


NO_DOCUMENTS_KO = "수집된 문서가 없어 이 항목을 확인하지 못했습니다. 사이트 상태와는 무관합니다."


def all_unknown(check_ids: Sequence[str], reason_ko: str) -> CollectionResult:
    """Every declared check answered UNKNOWN with one reason. Used when a crawl is empty."""
    return CollectionResult(
        outcomes=tuple(unknown_outcome(check_id, reason_ko) for check_id in check_ids)
    )


def sample_is_the_whole_site(context: CollectionContext, site: SiteObservation) -> bool:
    """우리가 본 것이 이 사이트의 **전부**인가, 아니면 일부인가.

    이 하나의 질문이 ``해당 없음`` 과 ``측정 불가`` 를 가른다. 둘은 점수에서 정반대로
    움직인다 — 앞은 분모에서 빠지고, 뒤는 분모에 남아 0점이다(ADR 0016). 그래서 근거
    없이 앞을 고르면 **덜 재는 편이 유리해진다.**

    "수집한 페이지 중에 그런 것이 없다" 와 "이 사이트에 그런 것이 없다" 는 다른 문장이다.
    홈페이지 한 장만 보고 "이 사이트에는 깊은 URL 이 없다" 거나 "지연 로딩을 쓰는
    페이지가 없다" 고 단정하면, 없는 사실을 만들어 내는 것이면서 동시에 표본을 좁힌
    쪽에 점수를 얹어 주는 것이 된다.

    **전부라고 말하려면 두 가지가 필요하다.**

    1. 발견 크롤이 상한·예산에 걸리지 않고 가져올 주소를 다 가져왔다
       (``crawl_is_exhaustive``).
    2. 그 크롤이 실제로 작동했다는 증거. 페이지를 둘 이상 가져왔다면 링크 추적이
       동작한 것이고, 한 장뿐이라면 사이트가 스스로 sitemap 으로 "페이지가 하나다" 라고
       선언해 주어야 한다.

    두 번째가 필요한 이유는 메뉴를 자바스크립트로만 그리는 사이트다. 원본 HTML 에
    링크가 없으니 크롤은 "더 볼 것이 없다" 고 판단하지만 실제로는 페이지가 많다. 그때
    해당 없음으로 접으면 **링크를 숨긴 사이트가 유리해진다.**
    """
    if not context.crawl_is_exhaustive:
        return False
    if len(site.pages) >= 2:
        return True
    declared = site.sitemap_locations
    return bool(declared) and len(declared) < 2


def single_page_outcome(
    context: CollectionContext,
    site: SiteObservation,
    check_id: str,
    *,
    subject_ko: str,
) -> CheckOutcome:
    """페이지가 한 장뿐일 때, 페이지 간 비교 검사가 내놓아야 하는 답.

    사유에 무엇을 하면 판정되는지 함께 적는다 — "측정 불가" 만 띄우면 고장으로 읽힌다.
    """
    if sample_is_the_whole_site(context, site):
        return not_applicable_outcome(
            check_id,
            f"사이트 전체를 수집했고 sitemap도 페이지가 하나임을 확인해 주므로, "
            f"{subject_ko}가 성립하지 않습니다.",
        )
    if context.crawl_is_exhaustive:
        return unknown_outcome(
            check_id,
            f"수집한 페이지가 하나뿐이어서 {subject_ko}을 판단할 수 없습니다. "
            "링크를 따라가 봤지만 다른 페이지를 찾지 못했습니다 — 메뉴가 자바스크립트로만 "
            "그려지는 경우가 흔합니다. sitemap을 두시면 한 장짜리 사이트임을 확인할 수 "
            "있고, 그때 이 항목은 배점에서 빠집니다.",
        )
    return unknown_outcome(
        check_id,
        f"수집한 페이지가 하나뿐이어서 {subject_ko}을 판단할 수 없습니다. "
        "사이트 전체 진단으로 다시 재면 판정됩니다.",
    )


def absent_in_sample_outcome(
    context: CollectionContext,
    site: SiteObservation,
    check_id: str,
    *,
    absent_ko: str,
    subject_ko: str,
) -> CheckOutcome:
    """수집한 페이지 중에 검사 대상이 하나도 없을 때의 답.

    사이트 전체를 봤다면 "이 사이트에는 그것이 없다" 가 사실이고 해당 없음이 맞다.
    일부만 봤다면 그것은 **표본에 대한 사실**일 뿐이므로 측정 불가다.
    """
    if sample_is_the_whole_site(context, site):
        return not_applicable_outcome(check_id, absent_ko)
    return unknown_outcome(
        check_id,
        f"수집한 페이지 중에는 {subject_ko}이 없었습니다. 다만 사이트 전체를 본 것이 "
        "아니므로 다른 페이지에 있는지는 확인하지 못했습니다. 사이트 전체 진단으로 다시 "
        "재면 판정됩니다.",
    )


__all__ = [
    "DIRECT",
    "HEURISTIC_HIGH",
    "HEURISTIC_MEDIUM",
    "NO_DOCUMENTS_KO",
    "OFFICIAL_API",
    "EvidenceLedger",
    "SeoCollector",
    "absent_in_sample_outcome",
    "all_unknown",
    "issue",
    "outcome",
    "provider_payload",
    "sample_is_the_whole_site",
    "single_page_outcome",
    "site_outcome",
    "url_ratio_outcome",
]
