"""One collector per category of ``veo.seo.readiness``.

The mapping below is the contract between the specification and the code: every category
has exactly one collector and every collector owns exactly that category's check ids.
``apps/api/tests/seo/test_collector_contract.py`` asserts it against the published
specification, so adding a check to the specification fails the suite until someone
implements it — which is the point.
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

CATEGORY_COLLECTORS: dict[str, Callable[[], SeoCollector]] = {
    "crawl_indexability": CrawlIndexabilityCollector,
    "onpage_semantics": OnpageSemanticsCollector,
    "content_architecture": ContentArchitectureCollector,
    "performance_ux": PerformanceUxCollector,
    "structured_data": StructuredDataCollector,
    "search_engine_integration": SearchEngineIntegrationCollector,
    "observability_outcomes": ObservabilityOutcomesCollector,
    "offpage_entity": OffpageEntityCollector,
}

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
