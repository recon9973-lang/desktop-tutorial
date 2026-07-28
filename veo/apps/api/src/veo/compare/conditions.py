"""What a measurement was measured under, and whether two of them may be compared.

A competitor comparison is the easiest place in this product to produce a confident lie.
Crawl four pages of one site and two hundred of another, put the two scores side by side,
and the chart looks authoritative while meaning nothing. Nobody reading it can tell.

So the conditions travel with every score, and comparison is gated on them. The rules:

* Methodology differences are **never** waivable. A score from spec 1.0.0 and a score
  from 2.0.0 are different units, not different values, and no flag makes them one.
* Scope differences (how many pages) are blocking by default but an analyst may waive
  them deliberately — and the waiver does not make the difference disappear from the
  report. It stays, marked, so the reader sees what was accepted on their behalf.
* Everything else that changes what the number means — device, renderer, locale, which
  providers were enabled — blocks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

#: Beyond this ratio the crawls are not sampling the same thing.
DEFAULT_MAX_PAGE_RATIO = 3.0

#: Two measurements further apart than this describe different points in time.
DEFAULT_MAX_AGE_GAP_DAYS = 30


_FIELD_LABELS_KO = {
    "spec_id": "측정 명세",
    "spec_version": "방법론 버전",
    "spec_checksum": "명세 체크섬",
    "collector_version": "수집기 버전",
    "locale": "언어·지역",
    "device": "기기",
    "renderer": "렌더링 방식",
    "enabled_providers": "활성 제공자",
    "pages_examined": "검사 페이지 수",
    "measured_at": "측정 시점",
}


class ComparabilityError(ValueError):
    """Two measurements may not be placed beside each other."""

    def __init__(self, differences: list[ConditionDifference]) -> None:
        self.differences = differences
        # Both the field name and its Korean label appear: the field name so a developer
        # can grep for it, the label so the message can be shown to an analyst as-is.
        detail = "; ".join(
            f"{_FIELD_LABELS_KO.get(d.field, d.field)}({d.field}) {d.left} vs {d.right}"
            for d in differences
        )
        super().__init__(f"측정 조건이 달라 비교할 수 없습니다 — {detail}")


@dataclass(frozen=True, slots=True)
class ConditionDifference:
    """One way in which two measurements were not alike."""

    field: str
    left: Any
    right: Any
    blocking: bool
    explanation_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "left": _plain(self.left),
            "right": _plain(self.right),
            "blocking": self.blocking,
            "explanation_ko": self.explanation_ko,
        }


@dataclass(frozen=True, slots=True)
class MeasurementConditions:
    """The setup a score was produced under.

    Stored with every result and shown next to every comparison. Without it a score is
    a number without a unit.
    """

    spec_id: str
    spec_version: str
    spec_checksum: str
    collector_version: str
    pages_examined: int
    locale: str
    device: str
    renderer: str
    enabled_providers: tuple[str, ...]
    measured_at: datetime

    #: Fields that define the *unit* of the score. Any difference is fatal.
    METHODOLOGY_FIELDS = ("spec_id", "spec_version", "spec_checksum", "collector_version")
    #: Fields that define *what was looked at*. A difference changes the meaning.
    OBSERVATION_FIELDS = ("locale", "device", "renderer")

    def __post_init__(self) -> None:
        if self.pages_examined < 0:
            raise ValueError("pages_examined cannot be negative")

    @property
    def fingerprint(self) -> str:
        """A stable id for "measured the same way".

        Excludes ``measured_at`` and ``pages_examined``: two crawls minutes apart that
        happened to reach a different number of pages were still set up identically, and
        grouping them is useful. Time and scope are compared separately, with tolerances.
        """
        payload = {
            field: getattr(self, field)
            for field in (*self.METHODOLOGY_FIELDS, *self.OBSERVATION_FIELDS)
        }
        payload["enabled_providers"] = sorted(self.enabled_providers)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "spec_version": self.spec_version,
            "spec_checksum": self.spec_checksum,
            "collector_version": self.collector_version,
            "pages_examined": self.pages_examined,
            "locale": self.locale,
            "device": self.device,
            "renderer": self.renderer,
            "enabled_providers": list(self.enabled_providers),
            "measured_at": self.measured_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MeasurementConditions:
        return cls(
            spec_id=payload["spec_id"],
            spec_version=payload["spec_version"],
            spec_checksum=payload["spec_checksum"],
            collector_version=payload["collector_version"],
            pages_examined=int(payload["pages_examined"]),
            locale=payload["locale"],
            device=payload["device"],
            renderer=payload["renderer"],
            enabled_providers=tuple(payload["enabled_providers"]),
            measured_at=datetime.fromisoformat(payload["measured_at"]),
        )

    def with_pages(self, pages: int) -> MeasurementConditions:
        return replace(self, pages_examined=pages)


def describe_differences(
    left: MeasurementConditions,
    right: MeasurementConditions,
    *,
    max_page_ratio: float = DEFAULT_MAX_PAGE_RATIO,
    max_age_gap_days: int = DEFAULT_MAX_AGE_GAP_DAYS,
) -> list[ConditionDifference]:
    """Every way the two setups differ, blocking or not.

    Always call this for the report, even when the comparison is allowed: a tolerated
    difference is still a difference the reader deserves to see.
    """
    found: list[ConditionDifference] = []

    for field in MeasurementConditions.METHODOLOGY_FIELDS:
        a, b = getattr(left, field), getattr(right, field)
        if a != b:
            found.append(
                ConditionDifference(
                    field=field,
                    left=a,
                    right=b,
                    blocking=True,
                    explanation_ko=(
                        f"{_FIELD_LABELS_KO[field]}이(가) 다릅니다. 서로 다른 방법론으로 계산된 "
                        "점수는 같은 단위가 아니므로 나란히 놓을 수 없습니다."
                    ),
                )
            )

    for field in MeasurementConditions.OBSERVATION_FIELDS:
        a, b = getattr(left, field), getattr(right, field)
        if a != b:
            found.append(
                ConditionDifference(
                    field=field,
                    left=a,
                    right=b,
                    blocking=True,
                    explanation_ko=(
                        f"{_FIELD_LABELS_KO[field]}이(가) 달라 같은 조건의 측정이 아닙니다."
                    ),
                )
            )

    if sorted(left.enabled_providers) != sorted(right.enabled_providers):
        found.append(
            ConditionDifference(
                field="enabled_providers",
                left=sorted(left.enabled_providers),
                right=sorted(right.enabled_providers),
                blocking=True,
                explanation_ko=(
                    "한쪽에만 연동된 외부 데이터가 있습니다. 한쪽은 측정하고 다른 쪽은 "
                    "'측정 불가'인 항목이 생기므로 점수를 직접 비교할 수 없습니다."
                ),
            )
        )

    page_difference = _page_scope_difference(left, right, max_page_ratio)
    if page_difference is not None:
        found.append(page_difference)

    gap_days = abs((left.measured_at - right.measured_at).total_seconds()) / 86400
    if gap_days > max_age_gap_days:
        found.append(
            ConditionDifference(
                field="measured_at",
                left=left.measured_at.isoformat(),
                right=right.measured_at.isoformat(),
                blocking=True,
                explanation_ko=(
                    f"측정 시점이 {gap_days:.0f}일 차이 납니다 (허용 {max_age_gap_days}일). "
                    "그 사이 사이트가 바뀌었을 수 있어 같은 기간의 비교로 볼 수 없습니다."
                ),
            )
        )

    return found


def _page_scope_difference(
    left: MeasurementConditions, right: MeasurementConditions, max_ratio: float
) -> ConditionDifference | None:
    if left.pages_examined == right.pages_examined:
        return None

    smaller = min(left.pages_examined, right.pages_examined)
    larger = max(left.pages_examined, right.pages_examined)

    if smaller == 0:
        return ConditionDifference(
            field="pages_examined",
            left=left.pages_examined,
            right=right.pages_examined,
            blocking=True,
            explanation_ko=("한쪽은 페이지를 한 건도 수집하지 못했습니다. 비교의 근거가 없습니다."),
        )

    ratio = larger / smaller
    blocking = ratio > max_ratio
    if blocking:
        explanation = (
            f"검사 페이지 수가 {smaller}건 대 {larger}건으로 {ratio:.1f}배 차이 납니다. "
            "표본 크기가 다르면 같은 문제라도 coverage가 다르게 계산되므로, 점수 차이를 "
            "사이트의 차이로 읽으면 안 됩니다."
        )
    else:
        explanation = (
            f"검사 페이지 수가 {smaller}건 대 {larger}건으로 다릅니다. 허용 범위 안이지만 "
            "해석할 때 감안해야 합니다."
        )

    return ConditionDifference(
        field="pages_examined",
        left=left.pages_examined,
        right=right.pages_examined,
        blocking=blocking,
        explanation_ko=explanation,
    )


def assert_comparable(
    left: MeasurementConditions,
    right: MeasurementConditions,
    *,
    allow_scope_variance: bool = False,
    max_page_ratio: float = DEFAULT_MAX_PAGE_RATIO,
    max_age_gap_days: int = DEFAULT_MAX_AGE_GAP_DAYS,
) -> None:
    """Raise unless these two measurements may be presented side by side.

    ``allow_scope_variance`` waives an uneven crawl only. It cannot waive a methodology,
    observation, provider or time difference — those change what the number means, and a
    caller who wants past them is asking for the wrong thing.
    """
    differences = describe_differences(
        left, right, max_page_ratio=max_page_ratio, max_age_gap_days=max_age_gap_days
    )
    blocking = [d for d in differences if d.blocking]

    if allow_scope_variance:
        blocking = [d for d in blocking if d.field != "pages_examined"]

    if blocking:
        raise ComparabilityError(blocking)


def is_comparable(
    left: MeasurementConditions,
    right: MeasurementConditions,
    *,
    allow_scope_variance: bool = False,
) -> bool:
    try:
        assert_comparable(left, right, allow_scope_variance=allow_scope_variance)
    except ComparabilityError:
        return False
    return True


def _plain(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return list(value)
    return value
