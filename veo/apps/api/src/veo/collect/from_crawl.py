"""수집 결과를 채점기가 읽는 형태로 옮긴다.

이 함수는 SEO 진단을 위해 쓰였지만 SEO 에 대해 아무것도 모른다 — 명세를 인자로 받고,
나머지는 "무엇을 가져왔는가" 를 옮기는 일뿐이다. 그래서 GEO 준비도도 **같은 수집물로**
같은 방식으로 채점할 수 있다.

두 진단이 이것을 공유하는 것이 중요한 이유가 둘이다.

* **대상 사이트에 두 번 요청하지 않는다.** 한 번 가져온 것으로 둘 다 잰다.
* **여기서 배운 것을 한 번만 고치면 된다.** 사이트맵을 안 넘겨 두 검사가 늘 측정 불가로
  나왔던 일, 모든 페이지를 대표 페이지 중요도로 넣었던 일 — 둘 다 이 자리의 결함이었다.
  복사본이 있었다면 한쪽만 고치고 다른 쪽은 조용히 틀린 채 남았을 것이다.

**같은 수집물로 둘을 채점하더라도 두 점수를 합치지 않는다**(ADR 0003). 재는 재료가
같다는 것과 뜻이 같다는 것은 다른 이야기다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from veo.collect.contract import CollectionContext
from veo.core.settings import get_provider_credentials
from veo.scoring import ScoringSpec
from veo.seo.crawl import CrawlOutcome
from veo.seo.importance import classify_urls


def context_from_crawl(
    *,
    target_url: str,
    spec: ScoringSpec,
    outcome: CrawlOutcome,
    locale: str,
) -> CollectionContext:
    """수집 결과 하나를 어떤 명세로든 채점할 수 있는 맥락으로 바꾼다.

    provider 상태는 설정에서 그대로 가져온다. 자격증명이 없는 provider 는 DISABLED 로
    들어가고, 그 항목은 UNKNOWN 이 되어 측정 범위를 낮춘다 — 감점되지도, 지어내지도
    않는다. 이 값을 ENABLED 로 위장하면 없는 데이터를 있는 것처럼 만들게 된다.

    사이트맵도 같은 이유로 여기서 넘긴다. 예전에는 이 자리에 빈 값이 들어가 있어서,
    사이트맵을 제대로 갖춘 사이트조차 사이트맵 두 항목이 **언제나** 측정 불가로
    나왔다. 그 배점은 분모에 남으므로 모든 고객의 점수가 우리가 수집을 안 만든 만큼
    내려가고 있었다 — 대상 사이트의 문제로 보이는 형태로.
    """
    documents = outcome.documents
    by_url = {document.final_url: document for document in documents}
    primary = documents[0] if documents else None
    return CollectionContext(
        target_url=target_url,
        spec=spec,
        documents=by_url,
        primary_document=primary,
        robots_txt=outcome.robots_txt,
        sitemap_documents=dict(outcome.sitemaps),
        # 렌더링 후 DOM 은 아직 수집하지 않는다. 비워 두면 렌더 비교 항목이 UNKNOWN 이
        # 되고, 원본 HTML 과 같다고 **가정하지 않는다**.
        rendered_dom={},
        provider_states=dict(get_provider_credentials().states()),
        provider_payloads={},
        # 예전에는 수집한 **모든** 페이지가 `CONVERSION_OR_HOME`(3.0) 이었다. 측정 범위는
        # 중요도로 가중되므로, 그 상태에서는 태그 페이지 한 장의 결함이 홈페이지 결함과
        # 같은 무게였다 — 가중치라는 개념이 사실상 없었다.
        url_importance=dict(
            classify_urls(
                (document.final_url for document in documents), entry_url=target_url
            )
        ),
        crawl_is_exhaustive=outcome.discovery_exhausted,
        locale=locale,
        collected_at=datetime.now(UTC),
    )


__all__ = ["context_from_crawl"]
