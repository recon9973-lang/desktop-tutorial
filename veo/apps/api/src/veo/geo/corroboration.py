"""검색 결과를 외부 대조 자료로 바꾼다 — 우리 고객 이야기만 골라서.

수집기(`geo/collectors/external_verifiability.py`)는 `geo_external` 이라는 자료를 기다리고
있었다. 소켓은 처음부터 있었고, 꽂을 것이 없었을 뿐이다. 이 모듈이 그것을 만든다.

## 여기서 가장 조심하는 것은 동명이인이다

"온담한의원" 을 검색하면 1위가 **"백세온담한의원"** 이다. 다른 병원이다. 그 글들을 우리
고객의 평판으로 세면 **없는 사실을 만들어 내는 것**이고, 그것은 이 제품이 하지 않기로
한 일이다(0-A).

그래서 검색 결과를 그대로 쓰지 않고, 관측 엔진이 AI 답변에 쓰는 것과 **같은 판별기**를
통과시킨다(`observations/detection/disambiguation`). 이름이 흔할수록 기준이 높아지고,
주소·전화·자사 도메인 같은 뒷받침이 있으면 낮아진다.

## 그래도 점수에는 넣지 않는다

판별기를 붙여도 네이버 한 곳만 본다는 사실은 그대로다. 명세가 이 항목들을
`REFERENCE_ONLY` 로 두는 이유이고, 이 모듈이 만든 자료는 **참고 구역에만** 쓰인다.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final
from urllib.parse import urlsplit

from veo.collect.contract import CollectionContext
from veo.contracts.enums import ProviderState
from veo.geo.view import build_view
from veo.observations.detection.disambiguation import (
    Attribution,
    BrandProfile,
    ConfidenceBand,
    assess,
)
from veo.observations.detection.normalize import BoundaryStrength, find_surface_matches
from veo.providers.naver.search import NaverSearchClient, SearchItem, SearchOutcome

#: 이 아래로는 우리 고객 이야기라고 볼 수 없다고 판단한다.
#:
#: 관측 엔진과 같은 문턱을 쓴다. 참고 항목이라고 기준을 낮추면, 정작 가장 헷갈리는
#: 자리에서 가장 관대해진다.
ACCEPTED_BANDS: Final = frozenset({ConfidenceBand.HIGH, ConfidenceBand.MEDIUM})

#: 사업자가 스스로 운영하는 채널. "독립적인 외부 출처" 로 세지 않는다.
_SELF_PUBLISHED: Final = frozenset({"local"})


def build_profile(
    *,
    display_name: str,
    own_domains: Sequence[str] = (),
    address_terms: Sequence[str] = (),
    phone_numbers: Sequence[str] = (),
) -> BrandProfile:
    """검색 결과를 판별할 때 쓸 브랜드 정보.

    주소·전화를 함께 넘기는 것이 중요하다. 이름만으로는 "백세온담한의원" 과 "온담한의원"
    을 가를 수 없고, 그때 판별기는 (옳게) 확신을 낮춘다.
    """
    return BrandProfile(
        entity_key="target",
        display_name=display_name,
        own_domains=tuple(own_domains),
        address_terms=tuple(address_terms),
        phone_numbers=tuple(phone_numbers),
        is_own_brand=True,
    )


def attribute(item: SearchItem, profile: BrandProfile) -> Attribution:
    """이 검색 결과가 우리 고객 이야기인가.

    `weak_only` 를 반드시 넘긴다. "백세**온담한의원**" 은 우리 이름을 글자 그대로 품고
    있어서 단순 일치로는 걸러지지 않는다. 판별기는 이름에 알 수 없는 한글이 붙어 있으면
    **더 긴 다른 상호일 수 있다**고 보고 확신을 낮추는데, 그 신호를 안 켜면 남의 가게
    글이 그대로 우리 평판이 된다.
    """
    text = item.text
    matches = find_surface_matches(text, profile.names)
    spans = [(match.start, match.end) for match in matches]
    weak_only = bool(matches) and all(
        match.strength is BoundaryStrength.WEAK for match in matches
    )
    return assess(text, profile, spans=spans, weak_only=weak_only)


def corroboration_payload(
    outcome: SearchOutcome, profile: BrandProfile
) -> dict[str, Any]:
    """`geo_external` 계약대로 자료를 만든다.

    판별을 통과하지 못한 항목은 **빼되 세어 둔다.** 조용히 버리면 "검색은 많이 나오는데
    보고서에는 몇 개 없다" 가 설명되지 않고, 읽는 사람은 우리가 못 찾았다고 이해한다.
    """
    kept: list[dict[str, Any]] = []
    rejected = 0

    for item in outcome.items:
        verdict = attribute(item, profile)
        if verdict.band not in ACCEPTED_BANDS:
            rejected += 1
            continue

        facts: dict[str, str] = {}
        if item.address:
            facts["address"] = item.address
        if item.telephone:
            facts["telephone"] = item.telephone

        kept.append(
            {
                "url": item.url,
                "source_type": item.source_type,
                # 지역 등록은 사업자가 스스로 관리하는 자리다. 외부의 독립된 목소리가 아니다.
                "independent": item.corpus not in _SELF_PUBLISHED,
                "claimed_profile": item.corpus in _SELF_PUBLISHED,
                "facts": facts,
            }
        )

    return {
        "entity_name": profile.display_name,
        "sources": kept,
        # 아래는 계약 밖의 참고 정보다. 수집기는 읽지 않고 화면이 읽는다.
        "lookup": {
            "engine": "NAVER",
            "totals": dict(outcome.totals),
            "considered": len(outcome.items),
            "accepted": len(kept),
            "rejected_as_another_business": rejected,
            "unavailable": dict(outcome.unavailable),
        },
    }


__all__ = [
    "ACCEPTED_BANDS",
    "attribute",
    "build_profile",
    "corroboration_payload",
    "look_up_corroboration",
    "profile_from_site",
]


def profile_from_site(context: CollectionContext) -> BrandProfile | None:
    """수집한 페이지에서 브랜드 정보를 읽어낸다.

    이름을 못 찾으면 **조회하지 않는다.** 도메인 이름을 브랜드로 삼아 검색하면 엉뚱한
    결과가 나오고, 그것을 참고랍시고 보여주면 없는 평판을 만들어 낸다. 못 찾은 것은 못
    찾은 것으로 남긴다.
    """
    view = build_view(context)
    organization = view.graph.primary_organization()
    name = (
        (organization.name if organization else "")
        or view.page.property_value("og:site_name")
        or ""
    ).strip()
    if not name:
        return None

    host = urlsplit(context.target_url).hostname or ""
    address = organization.address_text if organization else ""
    telephone = organization.telephone if organization else ""
    return build_profile(
        display_name=name,
        own_domains=(host,) if host else (),
        address_terms=(address,) if address else (),
        phone_numbers=(telephone,) if telephone else (),
    )


def look_up_corroboration(
    context: CollectionContext, *, client: NaverSearchClient
) -> tuple[dict[str, Any] | None, ProviderState, str]:
    """참고 조회를 실행한다. ``(자료, 제공자 상태, 사유)``.

    자료가 ``None`` 이면 수집기는 네 항목을 측정 불가로 남긴다 — 그것이 맞다. 조회를
    못 했는데 "외부 출처가 없다" 고 적으면 사이트 탓으로 읽힌다.
    """
    if client.state is not ProviderState.ENABLED:
        return None, client.state, "네이버 오픈API 자격증명이 없어 조회하지 않았습니다."

    profile = profile_from_site(context)
    if profile is None:
        return (
            None,
            ProviderState.DISABLED_NO_CREDENTIAL,
            "페이지에서 상호를 찾지 못해 조회하지 않았습니다. 도메인 이름으로 대신 "
            "검색하면 엉뚱한 업체가 잡힙니다.",
        )

    outcome = client.look_up(profile.display_name)
    if not outcome.items and outcome.failure is not None:
        return None, outcome.failure.provider_state, outcome.failure.reason_ko
    return corroboration_payload(outcome, profile), ProviderState.ENABLED, ""
