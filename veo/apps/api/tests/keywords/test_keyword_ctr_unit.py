"""CTR is already a percentage. Pinned against a real Naver response.

This is the one field that can be silently 100x wrong, and no offline test could settle
it — the API documentation does not state the unit. It was resolved on 2026-07-28 by
calling the live endpoint with a real credential and checking the arithmetic:

    "relKeyword": "임플란트"
    "monthlyPcQcCnt":     4370      searches
    "monthlyAvePcClkCnt":   24.1    clicks
    "monthlyAvePcCtr":       0.59   <- 24.1 / 4370 = 0.55%, so this is 0.59 PERCENT

Read as a ratio, 0.59 would mean 59%, which is 107x the observed click rate. It is a
percentage. Mobile agrees: 119.2 / 20000 = 0.60%, reported as 0.64.

So VEO stores the provider's number verbatim and records the unit beside it. Anything
that renders a CTR must not multiply by 100.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from veo.providers.naver.searchad import CTR_UNIT, normalize_keywordstool

#: Captured from the live API on 2026-07-28. Do not "tidy" these numbers — the whole
#: point is that they are what Naver actually sent.
LIVE_ROW = {
    "relKeyword": "임플란트",
    "monthlyPcQcCnt": 4370,
    "monthlyMobileQcCnt": 20000,
    "plAvgDepth": 10,
    "compIdx": "높음",
    "monthlyAvePcClkCnt": 24.1,
    "monthlyAveMobileClkCnt": 119.2,
    "monthlyAvePcCtr": 0.59,
    "monthlyAveMobileCtr": 0.64,
}


def normalized():  # type: ignore[no-untyped-def]
    payload = {"keywordList": [LIVE_ROW]}
    return normalize_keywordstool(
        payload,
        collected_at=datetime.now(UTC),
        raw_bytes=json.dumps(payload).encode(),
    ).metrics[0]


def test_the_ctr_unit_is_declared_as_percent() -> None:
    """Nobody downstream should have to guess, or re-derive it from clicks."""
    assert CTR_UNIT == "PERCENT"


def test_ctr_is_stored_exactly_as_naver_sent_it() -> None:
    metrics = normalized()
    assert metrics.avg_pc_ctr.value == pytest.approx(0.59)
    assert metrics.avg_mobile_ctr.value == pytest.approx(0.64)


def test_the_stored_ctr_is_consistent_with_clicks_over_searches() -> None:
    """The arithmetic that settled the unit, kept as a live regression check.

    If a future change starts multiplying by 100 somewhere in the adapter, the stored
    CTR stops matching the click rate and this fails.
    """
    metrics = normalized()
    for ctr, clicks, searches in (
        (metrics.avg_pc_ctr.value, LIVE_ROW["monthlyAvePcClkCnt"], LIVE_ROW["monthlyPcQcCnt"]),
        (
            metrics.avg_mobile_ctr.value,
            LIVE_ROW["monthlyAveMobileClkCnt"],
            LIVE_ROW["monthlyMobileQcCnt"],
        ),
    ):
        assert ctr is not None
        observed_percent = clicks / searches * 100
        # Naver's CTR is measured against ad impressions, not searches, so the two are
        # close rather than equal. A factor-of-100 error would be unmissable.
        assert 0.1 < ctr / observed_percent < 10, (
            f"stored CTR {ctr} is not the same magnitude as {observed_percent:.2f}% — "
            "something has rescaled it"
        )


def test_a_ctr_is_never_a_ratio() -> None:
    """Guard the specific 100x mistake: 0.59 must never become 59."""
    metrics = normalized()
    assert metrics.avg_pc_ctr.value is not None
    assert metrics.avg_pc_ctr.value < 5.0, (
        "a click-through rate above 5% for a broad head keyword means the value was "
        "read as a ratio and multiplied by 100"
    )


def test_competition_index_stays_absent_because_naver_sends_a_label() -> None:
    """Naver publishes 높음/중간/낮음, not a 0-100 index. Deriving one would look official."""
    metrics = normalized()
    assert metrics.competition_label == "높음"
    assert metrics.competition_index is None


def test_the_calculated_total_is_marked_as_calculated() -> None:
    """PC + mobile is VEO's arithmetic, not a figure Naver sent."""
    from veo.contracts.enums import DataSource

    metrics = normalized()
    assert metrics.monthly_total_searches.value == 24370
    assert metrics.monthly_total_searches.source is DataSource.CALCULATED
    assert metrics.monthly_pc_searches.source is DataSource.NAVER_SEARCH_AD
