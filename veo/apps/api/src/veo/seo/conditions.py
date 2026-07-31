"""What a saved SEO scan was measured under.

:class:`~veo.compare.conditions.MeasurementConditions` says of itself that it is "stored
with every result and shown next to every comparison. Without it a score is a number
without a unit." It was stored with no result at all.

``scan_runs`` already had columns for three of these facts, and every one of them was
being written as a constant:

.. code-block:: python

    device_profile="DESKTOP",   # no desktop browser is involved
    provider_states={},         # the context knew them and they were dropped
    user_agent=None             # never set

The consequence is not cosmetic. ``veo.compare.conditions.assert_comparable`` exists to
refuse a comparison between measurements produced different ways; with nothing recorded,
that guard can never run against a stored scan, and two runs made under different
conditions sit side by side looking like a change in the site.

This module turns a finished crawl into that block, and reads it back.
"""

from __future__ import annotations

from typing import Any

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import DEFAULT_USER_AGENT
from veo.compare.conditions import MeasurementConditions
from veo.competitors.conditions import conditions_from_seo_scan
from veo.seo.service import SeoScanResult

#: How VEO presents itself to the site being measured.
#:
#: An identified bot: no viewport, no JavaScript engine, no cookies. ``"DESKTOP"`` was
#: written here before, and that is a claim about what the customer's visitors see —
#: it would put a bot fetch and a desktop-browser fetch in the same comparison bucket.
DEVICE_PROFILE = "BOT"

#: The checks read the HTML exactly as it arrived.
RENDERER_RAW_HTML = "RAW_HTML"

#: A renderer ran first and the checks read the resulting DOM.
RENDERER_RENDERED_DOM = "RENDERED_DOM"


def renderer_for(context: CollectionContext) -> str:
    """Which DOM the checks actually read.

    A fact about this run, not a setting. When no renderer ran, ``rendered_dom`` is empty
    and the parity checks stay UNKNOWN — recording ``RENDERED_DOM`` anyway would make a
    score derived from raw HTML comparable with one derived from a browser, and those two
    numbers answer different questions about the same page.
    """
    return RENDERER_RENDERED_DOM if context.rendered_dom else RENDERER_RAW_HTML


def conditions_for_scan(
    result: SeoScanResult,
    context: CollectionContext,
    *,
    collector_version: str,
) -> MeasurementConditions:
    """The conditions block for one completed console scan.

    Every field comes from the run itself. Nothing here has a default that would let a
    missing fact pass as a measured one.
    """
    return conditions_from_seo_scan(
        result,
        context,
        collector_version=collector_version,
        device=DEVICE_PROFILE,
        renderer=renderer_for(context),
    )


def conditions_from_stored(payload: Any) -> MeasurementConditions | None:
    """Read back what was recorded, or ``None`` for a run saved before this existed.

    ``None`` is not an error and must not be replaced with a plausible block. A run whose
    conditions were never recorded genuinely cannot be compared — inventing one would
    hand the comparison guard a reason to say yes.
    """
    if not isinstance(payload, dict) or not payload:
        return None
    try:
        return MeasurementConditions.from_dict(payload)
    except (KeyError, TypeError, ValueError):
        # A malformed block is the same situation as a missing one, and for the same
        # reason: we do not know how this was measured.
        return None


__all__ = [
    "DEFAULT_USER_AGENT",
    "DEVICE_PROFILE",
    "RENDERER_RAW_HTML",
    "RENDERER_RENDERED_DOM",
    "conditions_for_scan",
    "conditions_from_stored",
    "renderer_for",
]
