"""오프페이지·엔터티 신호 — three checks about the world outside the site.

Referring domains, spam signals and how a brand is written elsewhere are all statements
about other people's pages. VEO does not crawl the open web to find out, so with no
external source connected all three are UNKNOWN with a Korean reason. Inferring a
backlink profile from anything on the site itself would be fabricating a measurement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    IssueDraft,
    unknown_outcome,
)
from veo.scoring import CheckOutcome
from veo.seo.collectors.base import (
    OFFICIAL_API,
    EvidenceLedger,
    SeoCollector,
    issue,
    provider_payload,
    site_outcome,
)
from veo.seo.parsing import normalise

PROVIDER_BACKLINKS = "BACKLINK_INDEX"
PROVIDER_BRAND_MENTIONS = "BRAND_MENTIONS"

#: Proportion of sampled referring domains flagged as spam that is worth reporting.
MAX_SPAM_RATIO = 0.25


class OffpageEntityCollector(SeoCollector):
    category_id = "offpage_entity"
    check_id_list = (
        "seo.offpage.referring_domains_present",
        "seo.offpage.brand_name_consistency",
        "seo.offpage.no_spam_signal",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        ledger = EvidenceLedger()
        backlinks, backlink_reason = provider_payload(context, PROVIDER_BACKLINKS)
        mentions, mention_reason = provider_payload(context, PROVIDER_BRAND_MENTIONS)

        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        for produced, produced_issues in (
            _referring_domains(context, ledger, backlinks, backlink_reason),
            _brand_consistency(context, ledger, mentions, mention_reason),
            _spam_signal(context, ledger, backlinks, backlink_reason),
        ):
            outcomes.append(produced)
            issues.extend(produced_issues)

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=ledger.records(), issues=tuple(issues)
        )


def _record(ledger: EvidenceLedger, kind: str, payload: Mapping[str, Any], excerpt: str) -> str:
    return ledger.of(
        kind,
        url=None,
        payload=repr(sorted(payload.items())),
        excerpt=excerpt,
    )


def _referring_domains(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.offpage.referring_domains_present"
    if payload is None:
        return unknown_outcome(check_id, reason_ko or "참조 도메인 정보를 조회하지 못했습니다."), []

    count = int(payload.get("referring_domains", 0) or 0)
    passed = count > 0
    evidence = [_record(ledger, "provider_response", payload, f"참조 도메인 {count}개")]

    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"referring_domains": count},
        note=(
            f"참조 도메인이 {count}개 확인됩니다."
            if passed
            else "외부에서 이 사이트를 링크하는 도메인이 확인되지 않습니다."
        ),
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="외부에서 링크하는 도메인이 없습니다",
            summary_ko=(
                "이 사이트를 링크하는 외부 도메인이 하나도 확인되지 않습니다. 사이트가 새로 "
                "만들어졌거나 외부에 알려질 창구가 없는 상태입니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "업종 협회, 지역 정보 페이지, 제휴사 소개처럼 실제 관계가 있는 곳에 사이트 주소가 "
                "실리도록 하십시오. 링크를 사는 방식은 스팸 신호로 처리되므로 피해야 합니다."
            ),
            reverification_ko="다음 수집 주기에 참조 도메인 수가 늘었는지 확인합니다.",
            business_impact_ko="외부 신뢰 신호가 없어 경쟁 사이트와 같은 조건에서 밀립니다.",
        )
    ]


def _brand_consistency(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.offpage.brand_name_consistency"
    if payload is None:
        return (
            unknown_outcome(
                check_id,
                reason_ko or "외부 채널의 브랜드 표기를 수집하지 못해 비교하지 못했습니다.",
            ),
            [],
        )

    canonical = str(payload.get("canonical_name", "")).strip()
    observed = payload.get("observed_names")
    if not canonical or not isinstance(observed, Sequence) or isinstance(observed, str | bytes):
        return unknown_outcome(check_id, "응답에 비교할 브랜드 표기 목록이 없습니다."), []

    names = [str(name).strip() for name in observed if str(name).strip()]
    if not names:
        return unknown_outcome(check_id, "외부 채널에서 수집된 브랜드 표기가 없습니다."), []

    differing = sorted({name for name in names if normalise(name) != normalise(canonical)})
    passed = not differing

    evidence = [
        _record(
            ledger,
            "external_source",
            payload,
            f"기준 표기 “{canonical}”, 확인된 표기 {', '.join(sorted(set(names)))}",
        )
    ]

    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"canonical_name": canonical, "differing": differing},
        note=(
            "외부 채널의 브랜드 표기가 기준 표기와 일치합니다."
            if passed
            else f"{len(differing)}가지 다른 표기가 외부 채널에서 확인됩니다."
        ),
        warning=True,
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="외부 채널의 브랜드 표기가 서로 다릅니다",
            summary_ko=(
                f"기준 표기는 “{canonical}”인데 외부 채널에서 "
                f"{', '.join(f'“{name}”' for name in differing[:5])} 표기가 함께 쓰이고 있습니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "상호, 주소, 전화번호 표기를 한 가지로 정하고 지도 등록, 소셜 프로필, 보도자료에 "
                "같은 형태로 반영하십시오. 띄어쓰기와 영문 표기까지 통일해야 합니다."
            ),
            reverification_ko="정리 후 외부 표기 목록을 다시 수집해 일치 여부를 확인합니다.",
            business_impact_ko=(
                "표기가 갈리면 같은 사업체로 인식되지 않아 지역 검색에서 불리합니다."
            ),
        )
    ]


def _spam_signal(
    context: CollectionContext,
    ledger: EvidenceLedger,
    payload: Mapping[str, Any] | None,
    reason_ko: str | None,
) -> tuple[CheckOutcome, list[IssueDraft]]:
    check_id = "seo.offpage.no_spam_signal"
    if payload is None:
        return unknown_outcome(check_id, reason_ko or "스팸 링크 신호를 조회하지 못했습니다."), []

    sampled = int(payload.get("sampled_domains", 0) or 0)
    flagged = int(payload.get("spam_flagged_domains", 0) or 0)
    if sampled <= 0:
        return (
            unknown_outcome(check_id, "표본으로 확인한 참조 도메인이 없어 판단하지 못했습니다."),
            [],
        )

    ratio = flagged / sampled
    passed = ratio <= MAX_SPAM_RATIO

    evidence = [
        _record(
            ledger,
            "provider_response",
            payload,
            f"표본 {sampled}개 가운데 스팸 표시 {flagged}개 ({round(ratio * 100, 1)}%)",
        )
    ]

    result = site_outcome(
        check_id,
        passed=passed,
        confidence_level=OFFICIAL_API,
        evidence_ids=evidence,
        observed_value={"sampled": sampled, "flagged": flagged, "ratio": round(ratio, 4)},
        note=(
            "명백한 스팸 링크 신호가 확인되지 않습니다."
            if passed
            else f"표본 참조 도메인의 {round(ratio * 100, 1)}%가 스팸으로 표시되어 있습니다."
        ),
    )
    if passed:
        return result, []

    return result, [
        issue(
            context,
            check_id,
            title_ko="스팸으로 표시된 참조 도메인 비중이 높습니다",
            summary_ko=(
                f"확인한 참조 도메인 {sampled}개 가운데 {flagged}개가 스팸으로 표시되어 "
                "있습니다. 링크를 구매했거나 자동 생성 사이트에 노출된 경우에 나타나는 형태입니다."
            ),
            affected_urls=[context.target_url],
            evidence_ids=evidence,
            remediation_ko=(
                "관계가 없는 링크는 해당 사이트에 삭제를 요청하고, 회수되지 않는 링크는 "
                "Search Console의 링크 부인 기능으로 정리하십시오. 부인은 되돌리기 번거로우니 "
                "목록을 확인한 뒤 신청해야 합니다."
            ),
            reverification_ko="정리 후 다음 수집에서 스팸 표시 비중이 낮아졌는지 확인합니다.",
            business_impact_ko=(
                "스팸 링크가 쌓이면 수동 조치로 검색 노출이 크게 줄어들 수 있습니다."
            ),
        )
    ]


__all__ = [
    "MAX_SPAM_RATIO",
    "PROVIDER_BACKLINKS",
    "PROVIDER_BRAND_MENTIONS",
    "OffpageEntityCollector",
]
