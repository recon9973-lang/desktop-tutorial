"""One collector per category of the ``veo.geo.readiness`` specification.

The split follows the specification exactly: seven categories, seven collectors, no check
owned twice and none owned by nobody. ``veo.geo.service`` asserts that against the spec on
every run, and ``tests/geo/test_coverage_contract.py`` asserts it against the file on
disk, so a new check in a published specification fails the suite until somebody
implements it.
"""

from veo.geo.collectors.access_eligibility import AccessEligibilityCollector
from veo.geo.collectors.answer_extractability import AnswerExtractabilityCollector
from veo.geo.collectors.entity_clarity import EntityClarityCollector
from veo.geo.collectors.evidence_transparency import EvidenceTransparencyCollector
from veo.geo.collectors.external_verifiability import ExternalVerifiabilityCollector
from veo.geo.collectors.freshness_signals import FreshnessSignalsCollector
from veo.geo.collectors.structured_data_meta import StructuredDataMetaCollector

__all__ = [
    "AccessEligibilityCollector",
    "AnswerExtractabilityCollector",
    "EntityClarityCollector",
    "EvidenceTransparencyCollector",
    "ExternalVerifiabilityCollector",
    "FreshnessSignalsCollector",
    "StructuredDataMetaCollector",
]
