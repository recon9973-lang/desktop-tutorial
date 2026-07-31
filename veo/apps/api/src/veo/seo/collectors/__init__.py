"""수집기 목록 — 명세의 모든 검사를 정확히 한 번씩 잰다.

이 목록이 명세와 코드 사이의 계약이다: **명세의 모든 검사에 수집기가 하나씩 있고,
수집기가 재는 검사는 전부 명세에 있다.** `tests/seo/test_collector_contract.py` 가
발행된 명세에 대고 확인하므로, 명세에 검사를 더하면 누군가 구현할 때까지 시험이
깨진다 — 그게 목적이다.

**수집기 묶음과 채점 영역은 다른 것이다.** 2026-08-01 이전에는 둘이 1:1 이었고
그래서 같은 것처럼 보였는데, 우연이었다. 수집기는 **무엇을 어떻게 재는가**로 묶인다
(HTML 을 파싱하는 것끼리, 크롤 구조를 보는 것끼리, 제공자 API 를 부르는 것끼리).
채점 영역은 **결함이 검색에 어떻게 작용하는가**로 묶인다(색인 차단 → 해석 불가 →
경쟁력 …). 두 관점이 같은 선으로 갈릴 이유가 없다.

명세 1.8.0 이 채점 영역을 검색 여정의 여섯 단계로 다시 나누면서 이 사실이 드러났다.
예를 들어 `seo.perf.cls_lab` 은 성능 수집기가 재지만 채점은 '경쟁력' 단계에 속하고,
`seo.perf.tbt_lab` 은 같은 수집기가 재지만 '위생' 단계다. 어느 화면에 묶어 보여줄지는
명세가 정하고(`spec.category_of`), 누가 재는지는 이 목록이 정한다.
"""

from collections.abc import Callable

from veo.seo.collectors.base import SeoCollector
from veo.seo.collectors.content_architecture import ContentArchitectureCollector
from veo.seo.collectors.crawl_indexability import CrawlIndexabilityCollector
from veo.seo.collectors.observability_outcomes import ObservabilityOutcomesCollector
from veo.seo.collectors.offpage_entity import OffpageEntityCollector
from veo.seo.collectors.onpage_semantics import OnpageSemanticsCollector
from veo.seo.collectors.performance_ux import PerformanceUxCollector
from veo.seo.collectors.search_engine_integration import SearchEngineIntegrationCollector
from veo.seo.collectors.structured_data import StructuredDataCollector

#: 이름은 수집기가 **무엇을 보는지**를 말한다. 채점 영역 이름과 같을 필요가 없다.
SEO_COLLECTORS: dict[str, Callable[[], SeoCollector]] = {
    "crawl_indexability": CrawlIndexabilityCollector,
    "onpage_semantics": OnpageSemanticsCollector,
    "content_architecture": ContentArchitectureCollector,
    "performance_ux": PerformanceUxCollector,
    "structured_data": StructuredDataCollector,
    "search_engine_integration": SearchEngineIntegrationCollector,
    "observability_outcomes": ObservabilityOutcomesCollector,
    "offpage_entity": OffpageEntityCollector,
}

#: 옛 이름. 채점 영역으로 묶여 있다는 뜻을 담고 있어 더는 사실이 아니다.
CATEGORY_COLLECTORS = SEO_COLLECTORS

#: Which checks can only ever be answered by an external provider. Used by the router to
#: tell a customer, before a scan runs, what a missing credential will leave unmeasured.
PROVIDER_BACKED_CHECKS = frozenset(
    set(PerformanceUxCollector.check_id_list[:4])
    | set(SearchEngineIntegrationCollector.check_id_list)
    | set(ObservabilityOutcomesCollector.check_id_list)
    | set(OffpageEntityCollector.check_id_list)
)

__all__ = [
    "CATEGORY_COLLECTORS",
    "PROVIDER_BACKED_CHECKS",
    "SEO_COLLECTORS",
    "ContentArchitectureCollector",
    "CrawlIndexabilityCollector",
    "ObservabilityOutcomesCollector",
    "OffpageEntityCollector",
    "OnpageSemanticsCollector",
    "PerformanceUxCollector",
    "SearchEngineIntegrationCollector",
    "SeoCollector",
    "StructuredDataCollector",
]
