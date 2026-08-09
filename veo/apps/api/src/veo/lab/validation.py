"""Validating a candidate specification, and describing it against what is published.

Two jobs.

**Validation.** Schema conformance and internal consistency already live in
:func:`veo.scoring.build_spec`; this module runs them and adds the rules that only matter
when a human is about to approve something: the category weights must total 100, every
check id a cap or gate names must exist, and no check id may appear twice. ``build_spec``
raises on the first problem it finds, which is right for a loader and wrong for a review
screen, so the structural checks here are run over the raw document as well and every
finding is collected before anything is reported.

**The diff.** A reviewer approving a methodology change needs to see what changed, in
Korean, without reading YAML: which category weights moved, which checks came and went,
which severities were reclassified, which caps and gates were added, removed or loosened.
:func:`diff_specs` produces that, and :meth:`SpecDiff.lines_ko` renders it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from veo.lab.errors import SpecificationRejectedError
from veo.scoring import (
    ScoringSpec,
    ScoringSpecError,
    SpecCap,
    SpecCheck,
    build_spec,
)

#: VEO's published specifications normalise category weights to 100. Keeping the total
#: fixed is what makes "이 카테고리 배점이 25에서 30으로 올랐다" mean something: on a
#: floating total the same edit could raise or lower the category's real influence.
CATEGORY_WEIGHT_TOTAL = 100.0
WEIGHT_TOLERANCE = 1e-6


def _num(value: float) -> str:
    """Render a number the way a reviewer writes it: 70, not 70.0; 12.5 stays 12.5."""
    rounded = value
    if abs(rounded - round(rounded)) < 1e-9:
        return str(round(rounded))
    return f"{rounded:g}"


def _signed(value: float) -> str:
    rendered = _num(abs(value))
    return f"+{rendered}" if value >= 0 else f"-{rendered}"


# --------------------------------------------------------------------------- #
# Diff
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class WeightChange:
    category_id: str
    name_ko: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before


@dataclass(frozen=True)
class CheckChange:
    check_id: str
    category_id: str
    title_ko: str
    severity: str


@dataclass(frozen=True)
class SeverityChange:
    check_id: str
    title_ko: str
    before: str
    after: str


@dataclass(frozen=True)
class CapChange:
    cap_id: str
    before_max: float
    after_max: float


@dataclass(frozen=True)
class SpecDiff:
    """What a candidate changes relative to the currently published specification."""

    baseline_version: str | None
    baseline_checksum: str | None
    candidate_version: str
    candidate_checksum: str
    categories_added: tuple[str, ...] = ()
    categories_removed: tuple[str, ...] = ()
    weight_changes: tuple[WeightChange, ...] = ()
    checks_added: tuple[CheckChange, ...] = ()
    checks_removed: tuple[CheckChange, ...] = ()
    severity_changes: tuple[SeverityChange, ...] = ()
    caps_added: tuple[CapChange, ...] = ()
    caps_removed: tuple[CapChange, ...] = ()
    cap_changes: tuple[CapChange, ...] = ()
    gates_added: tuple[str, ...] = ()
    gates_removed: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(
            self.categories_added
            or self.categories_removed
            or self.weight_changes
            or self.checks_added
            or self.checks_removed
            or self.severity_changes
            or self.caps_added
            or self.caps_removed
            or self.cap_changes
            or self.gates_added
            or self.gates_removed
        )

    def lines_ko(self) -> tuple[str, ...]:
        if self.baseline_version is None:
            return (
                "이전 발행본이 없습니다. 이 명세가 해당 계열의 첫 발행본이므로 "
                "비교 대상이 없습니다.",
            )
        if not self.has_changes:
            return (
                f"이전 발행본 {self.baseline_version}과(와) 비교해 배점·검사·상한·게이트가 "
                "모두 같습니다.",
            )

        lines: list[str] = []
        for category_id in self.categories_added:
            lines.append(f"카테고리 추가: {category_id}")
        for category_id in self.categories_removed:
            lines.append(f"카테고리 삭제: {category_id}")
        for change in self.weight_changes:
            lines.append(
                f"가중치 변경: {change.name_ko}({change.category_id}) "
                f"{_num(change.before)} → {_num(change.after)} ({_signed(change.delta)})"
            )
        for added in self.checks_added:
            lines.append(
                f"검사 추가: {added.check_id} — {added.title_ko} "
                f"(심각도 {added.severity}, 카테고리 {added.category_id})"
            )
        for removed in self.checks_removed:
            lines.append(
                f"검사 삭제: {removed.check_id} — {removed.title_ko} "
                f"(심각도 {removed.severity}, 카테고리 {removed.category_id})"
            )
        for severity in self.severity_changes:
            lines.append(
                f"심각도 변경: {severity.check_id} — {severity.title_ko} "
                f"{severity.before} → {severity.after}"
            )
        for cap in self.caps_added:
            lines.append(f"상한 추가: {cap.cap_id} 최대 점수 {_num(cap.after_max)}")
        for cap in self.caps_removed:
            lines.append(f"상한 삭제: {cap.cap_id} (기존 최대 점수 {_num(cap.before_max)})")
        for cap in self.cap_changes:
            lines.append(
                f"상한 조정: {cap.cap_id} 최대 점수 "
                f"{_num(cap.before_max)} → {_num(cap.after_max)}"
            )
        for gate_id in self.gates_added:
            lines.append(f"게이트 추가: {gate_id}")
        for gate_id in self.gates_removed:
            lines.append(f"게이트 삭제: {gate_id}")
        return tuple(lines)

    def summary_ko(self) -> str:
        if self.baseline_version is None:
            return (
                f"{self.candidate_version}은(는) 비교할 이전 발행본이 없는 첫 명세입니다."
            )
        if not self.has_changes:
            return (
                f"{self.baseline_version} → {self.candidate_version}: "
                "측정 방법에 영향을 주는 변경이 없습니다."
            )
        counts = [
            ("가중치", len(self.weight_changes)),
            ("검사 추가", len(self.checks_added)),
            ("검사 삭제", len(self.checks_removed)),
            ("심각도", len(self.severity_changes)),
            (
                "상한",
                len(self.caps_added) + len(self.caps_removed) + len(self.cap_changes),
            ),
            ("게이트", len(self.gates_added) + len(self.gates_removed)),
        ]
        detail = ", ".join(f"{name} {count}건" for name, count in counts if count)
        return f"{self.baseline_version} → {self.candidate_version}: {detail}."

    def to_record(self) -> dict[str, Any]:
        return {
            "baseline_version": self.baseline_version,
            "baseline_checksum": self.baseline_checksum,
            "candidate_version": self.candidate_version,
            "candidate_checksum": self.candidate_checksum,
            "has_changes": self.has_changes,
            "summary_ko": self.summary_ko(),
            "lines_ko": list(self.lines_ko()),
            "weight_changes": [
                {
                    "category_id": change.category_id,
                    "name_ko": change.name_ko,
                    "before": change.before,
                    "after": change.after,
                    "delta": change.delta,
                }
                for change in self.weight_changes
            ],
            "checks_added": [change.check_id for change in self.checks_added],
            "checks_removed": [change.check_id for change in self.checks_removed],
            "severity_changes": [
                {
                    "check_id": change.check_id,
                    "before": change.before,
                    "after": change.after,
                }
                for change in self.severity_changes
            ],
            "cap_changes": [
                {
                    "cap_id": change.cap_id,
                    "before_max": change.before_max,
                    "after_max": change.after_max,
                }
                for change in self.cap_changes
            ],
            "caps_added": [change.cap_id for change in self.caps_added],
            "caps_removed": [change.cap_id for change in self.caps_removed],
            "gates_added": list(self.gates_added),
            "gates_removed": list(self.gates_removed),
        }


def _checks_of(spec: ScoringSpec) -> dict[str, tuple[str, SpecCheck]]:
    return {
        check.id: (category.id, check)
        for category in spec.categories
        for check in category.checks
    }


def _caps_of(spec: ScoringSpec) -> dict[str, SpecCap]:
    return {cap.id: cap for cap in spec.caps}


def diff_specs(baseline: ScoringSpec | None, candidate: ScoringSpec) -> SpecDiff:
    """Describe ``candidate`` against ``baseline``. ``None`` means there is no baseline."""
    if baseline is None:
        return SpecDiff(
            baseline_version=None,
            baseline_checksum=None,
            candidate_version=candidate.version,
            candidate_checksum=candidate.checksum,
        )

    before_categories = {category.id: category for category in baseline.categories}
    after_categories = {category.id: category for category in candidate.categories}

    weight_changes = tuple(
        WeightChange(
            category_id=category_id,
            name_ko=after_categories[category_id].name_ko,
            before=before_categories[category_id].weight,
            after=after_categories[category_id].weight,
        )
        for category_id in after_categories
        if category_id in before_categories
        and abs(after_categories[category_id].weight - before_categories[category_id].weight)
        > WEIGHT_TOLERANCE
    )

    before_checks = _checks_of(baseline)
    after_checks = _checks_of(candidate)

    checks_added = tuple(
        CheckChange(
            check_id=check_id,
            category_id=category_id,
            title_ko=check.title_ko,
            severity=str(check.severity),
        )
        for check_id, (category_id, check) in after_checks.items()
        if check_id not in before_checks
    )
    checks_removed = tuple(
        CheckChange(
            check_id=check_id,
            category_id=category_id,
            title_ko=check.title_ko,
            severity=str(check.severity),
        )
        for check_id, (category_id, check) in before_checks.items()
        if check_id not in after_checks
    )
    severity_changes = tuple(
        SeverityChange(
            check_id=check_id,
            title_ko=check.title_ko,
            before=str(before_checks[check_id][1].severity),
            after=str(check.severity),
        )
        for check_id, (_, check) in after_checks.items()
        if check_id in before_checks
        and before_checks[check_id][1].severity is not check.severity
    )

    before_caps = _caps_of(baseline)
    after_caps = _caps_of(candidate)
    caps_added = tuple(
        CapChange(cap_id=cap_id, before_max=0.0, after_max=cap.max_overall_score)
        for cap_id, cap in after_caps.items()
        if cap_id not in before_caps
    )
    caps_removed = tuple(
        CapChange(cap_id=cap_id, before_max=cap.max_overall_score, after_max=0.0)
        for cap_id, cap in before_caps.items()
        if cap_id not in after_caps
    )
    cap_changes = tuple(
        CapChange(
            cap_id=cap_id,
            before_max=before_caps[cap_id].max_overall_score,
            after_max=cap.max_overall_score,
        )
        for cap_id, cap in after_caps.items()
        if cap_id in before_caps
        and abs(before_caps[cap_id].max_overall_score - cap.max_overall_score)
        > WEIGHT_TOLERANCE
    )

    before_gates = {gate.id for gate in baseline.gates}
    after_gates = {gate.id for gate in candidate.gates}

    return SpecDiff(
        baseline_version=baseline.version,
        baseline_checksum=baseline.checksum,
        candidate_version=candidate.version,
        candidate_checksum=candidate.checksum,
        categories_added=tuple(sorted(set(after_categories) - set(before_categories))),
        categories_removed=tuple(sorted(set(before_categories) - set(after_categories))),
        weight_changes=weight_changes,
        checks_added=checks_added,
        checks_removed=checks_removed,
        severity_changes=severity_changes,
        caps_added=caps_added,
        caps_removed=caps_removed,
        cap_changes=cap_changes,
        gates_added=tuple(sorted(after_gates - before_gates)),
        gates_removed=tuple(sorted(before_gates - after_gates)),
    )


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    errors_ko: tuple[str, ...] = ()
    warnings_ko: tuple[str, ...] = ()
    category_weight_total: float = 0.0
    spec: ScoringSpec | None = None
    diff: SpecDiff | None = field(default=None)

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors_ko": list(self.errors_ko),
            "warnings_ko": list(self.warnings_ko),
            "category_weight_total": self.category_weight_total,
        }


def build_candidate(document: Mapping[str, Any]) -> ScoringSpec:
    """Freeze a candidate document, or raise with a Korean reason."""
    try:
        return build_spec(dict(document))
    except ScoringSpecError as exc:
        raise SpecificationRejectedError(
            f"명세 문서를 해석하지 못했습니다: {exc}", reasons_ko=(str(exc),)
        ) from exc


def validate_candidate(
    document: Mapping[str, Any], *, baseline: ScoringSpec | None = None
) -> ValidationReport:
    """Collect every problem with ``document``, then describe it against ``baseline``."""
    errors: list[str] = []
    warnings: list[str] = []

    spec: ScoringSpec | None = None
    try:
        spec = build_spec(dict(document))
    except ScoringSpecError as exc:
        errors.append(f"명세 검증에 실패했습니다: {exc}")
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        errors.append(f"명세 문서를 읽을 수 없습니다: {exc}")

    weight_total = _weight_total(document)
    errors.extend(_structural_errors(document, weight_total))
    warnings.extend(_structural_warnings(document, baseline, spec))

    deduped = _dedupe(errors)
    diff = diff_specs(baseline, spec) if spec is not None else None

    return ValidationReport(
        ok=not deduped,
        errors_ko=deduped,
        warnings_ko=_dedupe(warnings),
        category_weight_total=weight_total,
        spec=spec,
        diff=diff,
    )


def _dedupe(lines: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            ordered.append(line)
    return tuple(ordered)


def _categories(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = document.get("categories")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _weight_total(document: Mapping[str, Any]) -> float:
    total = 0.0
    for category in _categories(document):
        weight = category.get("weight")
        if isinstance(weight, (int, float)) and not isinstance(weight, bool):
            total += float(weight)
    return total


def _declared_check_ids(document: Mapping[str, Any]) -> list[str]:
    found: list[str] = []
    for category in _categories(document):
        checks = category.get("checks")
        if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)):
            continue
        for check in checks:
            if isinstance(check, Mapping) and isinstance(check.get("id"), str):
                found.append(str(check["id"]))
    return found


def _trigger_check_ids(document: Mapping[str, Any], key: str) -> list[tuple[str, str]]:
    """``(owner_id, check_id)`` for every condition under ``caps`` or ``gates``."""
    pairs: list[tuple[str, str]] = []
    raw = document.get(key)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return pairs
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        owner = str(item.get("id", "?"))
        trigger = item.get("trigger")
        if not isinstance(trigger, Mapping):
            continue
        conditions = trigger.get("any_of")
        if not isinstance(conditions, Sequence) or isinstance(conditions, (str, bytes)):
            continue
        for condition in conditions:
            if isinstance(condition, Mapping) and isinstance(condition.get("check_id"), str):
                pairs.append((owner, str(condition["check_id"])))
    return pairs


def _structural_errors(document: Mapping[str, Any], weight_total: float) -> list[str]:
    errors: list[str] = []

    declared = _declared_check_ids(document)
    seen: set[str] = set()
    for check_id in declared:
        if check_id in seen:
            errors.append(
                f"검사 id '{check_id}'가 두 번 이상 정의되어 있습니다. "
                "한 검사는 한 카테고리에만 속해야 합니다."
            )
        seen.add(check_id)

    if not _categories(document):
        errors.append("카테고리가 하나도 없습니다. 점수 명세에는 카테고리가 최소 하나 필요합니다.")
    elif abs(weight_total - CATEGORY_WEIGHT_TOTAL) > WEIGHT_TOLERANCE:
        errors.append(
            f"카테고리 가중치 합계는 {_num(CATEGORY_WEIGHT_TOTAL)}이어야 합니다. "
            f"현재 합계는 {_num(weight_total)}입니다."
        )

    for category in _categories(document):
        weight = category.get("weight")
        if isinstance(weight, (int, float)) and not isinstance(weight, bool) and weight <= 0:
            errors.append(
                f"카테고리 '{category.get('id', '?')}'의 가중치가 {_num(float(weight))}입니다. "
                "가중치는 0보다 커야 합니다."
            )

    for label, key in (("상한", "caps"), ("게이트", "gates")):
        for owner, check_id in _trigger_check_ids(document, key):
            if check_id not in seen:
                errors.append(
                    f"{label} '{owner}'가 이 명세에 없는 검사 '{check_id}'를 참조합니다."
                )

    return errors


def _structural_warnings(
    document: Mapping[str, Any],
    baseline: ScoringSpec | None,
    spec: ScoringSpec | None,
) -> list[str]:
    warnings: list[str] = []

    if spec is not None:
        version = spec.version
        if not any(entry.version == version for entry in spec.changelog):
            warnings.append(
                f"changelog에 {version} 항목이 없습니다. 무엇이 왜 바뀌었는지 문서에 남겨 두면 "
                "이후 재계산 결과를 설명하기 쉽습니다."
            )
        if not spec.compatible_collector_versions:
            warnings.append(
                "compatible_collector_versions가 비어 있습니다. 어떤 수집기 버전과 함께 "
                "쓰이는 명세인지 명시하는 편이 안전합니다."
            )
        if not _bands_cover_full_range(spec):
            warnings.append(
                "구간(bands)이 0점부터 100점까지를 모두 덮지 않습니다. 덮이지 않는 점수는 "
                "구간 없이 표시됩니다."
            )

    if baseline is not None and spec is not None:
        diff = diff_specs(baseline, spec)
        if diff.caps_removed:
            removed = ", ".join(cap.cap_id for cap in diff.caps_removed)
            warnings.append(
                f"상한이 삭제되었습니다: {removed}. 치명적 결함이 평균에 묻히지 않도록 하는 "
                "장치가 사라집니다."
            )
        if diff.checks_removed:
            removed = ", ".join(change.check_id for change in diff.checks_removed)
            warnings.append(
                f"검사가 삭제되었습니다: {removed}. 이전 버전으로 매긴 점수와는 직접 "
                "비교할 수 없습니다."
            )

    return warnings


def _bands_cover_full_range(spec: ScoringSpec) -> bool:
    covered = sorted((band.min, band.max) for band in spec.bands)
    if not covered or covered[0][0] > 0.0:
        return False
    reach = covered[0][1]
    for low, high in covered[1:]:
        if low > reach + 1e-6:
            return False
        reach = max(reach, high)
    return reach >= 100.0 - 1e-6
