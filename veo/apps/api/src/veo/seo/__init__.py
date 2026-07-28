"""VEO SEO 준비도 수집기.

Eight collectors, one per category of ``veo.seo.readiness``, covering all 47 published
checks. They observe and report; :mod:`veo.seo.service` hands what they report to the
one shared evaluator. No weight, severity or threshold-that-decides-points lives in this
package — those are in ``packages/scoring-specs`` and are authored by VEO-LAB.

Three rules the package exists to keep:

* **N/A is not zero.** A page with no structured data leaves the denominator.
* **UNKNOWN is not failure.** No credential means UNKNOWN with a Korean reason.
* **A fetch failure is not an SEO failure.** A page VEO could not retrieve says UNKNOWN.
"""

from veo.seo.observation import PageObservation, SiteObservation, build_observation
from veo.seo.service import (
    SPEC_ID,
    SeoScanResult,
    UnknownCheck,
    load_seo_spec,
    run_seo_scan,
    score_collection,
    seo_collectors,
    summarise,
)

__all__ = [
    "SPEC_ID",
    "PageObservation",
    "SeoScanResult",
    "SiteObservation",
    "UnknownCheck",
    "build_observation",
    "load_seo_spec",
    "run_seo_scan",
    "score_collection",
    "seo_collectors",
    "summarise",
]
