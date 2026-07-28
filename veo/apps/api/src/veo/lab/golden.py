"""Running the golden fixtures against a candidate specification.

``packages/scoring-specs/golden`` holds outcome sets whose expected numbers a human
worked out from the methodology. This module replays them against a candidate and records
pass/fail per fixture, because publishing is blocked until that has happened and passed.

Two consequences worth being explicit about.

*A methodology change fails these on purpose.* Move a weight and the fixtures stop
matching. That is the gate doing its job: the new numbers have to be worked out and
written into the fixtures deliberately, by someone, rather than appearing because the
evaluator was asked nicely.

*A recorded run is bound to a checksum.* :func:`assert_golden_ready` refuses a record
whose ``spec_checksum`` is not the checksum being published, so "validate, then edit, then
publish" cannot slip through.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from veo.lab.errors import GoldenFixtureError
from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    ScoreResult,
    ScoringSpec,
    ScoringSpecError,
    evaluate,
    find_specs_root,
)

#: The same tolerance ``tests/scoring/test_golden.py`` uses. A published score is rounded
#: to six places, so anything tighter would compare noise.
GOLDEN_TOLERANCE = 1e-6

#: Top-level fields compared on every fixture, with the Korean label a reviewer reads.
_SCALAR_FIELDS: tuple[tuple[str, str], ...] = (
    ("overall_score", "종합 점수"),
    ("overall_score_before_caps", "상한 적용 전 점수"),
    ("coverage", "측정 범위(coverage)"),
    ("confidence", "신뢰도(confidence)"),
    ("effective_weight_total", "유효 가중치 합계"),
)


def golden_directory() -> Path:
    return find_specs_root() / "golden"


def _render(value: Any) -> str:
    if value is None:
        return "없음"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text or "0"
    return str(value)


def _close(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return abs(float(left) - float(right)) <= GOLDEN_TOLERANCE


@dataclass(frozen=True)
class FixtureResult:
    name: str
    fixture_spec_id: str
    fixture_spec_version: str
    passed: bool
    failures_ko: tuple[str, ...]
    observed: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fixture_spec_version": self.fixture_spec_version,
            "passed": self.passed,
            "failures_ko": list(self.failures_ko),
            "observed": self.observed,
        }


@dataclass(frozen=True)
class GoldenRun:
    spec_id: str
    spec_version: str
    spec_checksum: str
    ran_at: datetime
    fixtures: tuple[FixtureResult, ...]

    @property
    def total(self) -> int:
        return len(self.fixtures)

    @property
    def passed_count(self) -> int:
        return sum(1 for fixture in self.fixtures if fixture.passed)

    @property
    def failed_count(self) -> int:
        return self.total - self.passed_count

    @property
    def all_passed(self) -> bool:
        """Zero fixtures is not success. A version nobody validated is not validated."""
        return self.total > 0 and self.failed_count == 0

    @property
    def failed_names(self) -> tuple[str, ...]:
        return tuple(fixture.name for fixture in self.fixtures if not fixture.passed)

    def summary_ko(self) -> str:
        if self.total == 0:
            return (
                f"{self.spec_id} 계열에 대한 골든 픽스처가 없습니다. 검증할 기준이 없으므로 "
                "발행할 수 없습니다."
            )
        if self.all_passed:
            return (
                f"골든 픽스처 {self.total}건이 모두 통과했습니다 "
                f"({self.spec_id}@{self.spec_version})."
            )
        return (
            f"골든 픽스처 {self.total}건 중 {self.failed_count}건이 실패했습니다: "
            f"{', '.join(self.failed_names)}. 방법론을 바꿨다면 기대값도 함께 갱신해야 합니다."
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "spec_version": self.spec_version,
            "spec_checksum": self.spec_checksum,
            "ran_at": self.ran_at.isoformat(),
            "total": self.total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "all_passed": self.all_passed,
            "failed_names": list(self.failed_names),
            "summary_ko": self.summary_ko(),
            "fixtures": [fixture.to_record() for fixture in self.fixtures],
        }


def load_fixtures(spec_id: str, *, directory: Path | None = None) -> list[dict[str, Any]]:
    """Every fixture authored for ``spec_id``, by file name order."""
    root = directory or golden_directory()
    if not root.is_dir():
        return []
    found: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and document.get("spec_id") == spec_id:
            document.setdefault("name", path.stem)
            found.append(document)
    return found


def run_golden_fixtures(spec: ScoringSpec, *, directory: Path | None = None) -> GoldenRun:
    """Replay every fixture for ``spec.spec_id`` against ``spec``."""
    results = [
        _run_one(spec, fixture)
        for fixture in load_fixtures(spec.spec_id, directory=directory)
    ]
    return GoldenRun(
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
        ran_at=datetime.now(UTC),
        fixtures=tuple(results),
    )


def assert_golden_ready(record: Mapping[str, Any] | None, *, spec_checksum: str) -> None:
    """Raise unless ``record`` is a passing run of the golden fixtures for these bytes."""
    if not record:
        raise GoldenFixtureError(
            "이 버전에 대한 골든 픽스처 검증 기록이 없습니다. 발행하기 전에 골든 픽스처를 "
            "실행해 결과를 남겨야 합니다."
        )

    recorded_checksum = str(record.get("spec_checksum", ""))
    if recorded_checksum != spec_checksum:
        raise GoldenFixtureError(
            "기록된 골든 픽스처 결과가 지금 발행하려는 명세와 다른 내용에 대해 실행되었습니다 "
            f"(기록 {recorded_checksum[:12] or '없음'}…, 현재 {spec_checksum[:12]}…). "
            "명세를 수정했다면 골든 픽스처를 다시 실행하세요."
        )

    if not record.get("all_passed"):
        failed = record.get("failed_names") or []
        names = ", ".join(str(name) for name in failed) if failed else "실패 항목 없음"
        total = record.get("total", 0)
        if not total:
            raise GoldenFixtureError(
                "골든 픽스처가 한 건도 실행되지 않았습니다. 검증하지 않은 버전은 발행할 수 "
                "없습니다."
            )
        raise GoldenFixtureError(
            f"골든 픽스처가 통과하지 못했습니다: {names}. 실패한 기준이 있는 명세는 발행할 수 "
            "없습니다."
        )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _run_one(spec: ScoringSpec, fixture: Mapping[str, Any]) -> FixtureResult:
    name = str(fixture.get("name", "이름 없는 픽스처"))
    fixture_version = str(fixture.get("spec_version", "?"))

    try:
        outcomes = _outcomes(spec, fixture)
    except GoldenFixtureError as exc:
        return FixtureResult(
            name=name,
            fixture_spec_id=str(fixture.get("spec_id", spec.spec_id)),
            fixture_spec_version=fixture_version,
            passed=False,
            failures_ko=(exc.message_ko,),
            observed={},
        )

    try:
        result = evaluate(spec, outcomes)
    except ScoringSpecError as exc:
        return FixtureResult(
            name=name,
            fixture_spec_id=str(fixture.get("spec_id", spec.spec_id)),
            fixture_spec_version=fixture_version,
            passed=False,
            failures_ko=(f"채점에 실패했습니다: {exc}",),
            observed={},
        )

    expected = fixture.get("expected")
    if not isinstance(expected, Mapping):
        return FixtureResult(
            name=name,
            fixture_spec_id=str(fixture.get("spec_id", spec.spec_id)),
            fixture_spec_version=fixture_version,
            passed=False,
            failures_ko=("픽스처에 expected 블록이 없습니다.",),
            observed=_observed(result),
        )

    failures = _compare(result, expected)
    return FixtureResult(
        name=name,
        fixture_spec_id=str(fixture.get("spec_id", spec.spec_id)),
        fixture_spec_version=fixture_version,
        passed=not failures,
        failures_ko=tuple(failures),
        observed=_observed(result),
    )


def _outcomes(spec: ScoringSpec, fixture: Mapping[str, Any]) -> list[CheckOutcome]:
    default = fixture.get("default")
    if not isinstance(default, Mapping):
        raise GoldenFixtureError(f"픽스처 '{fixture.get('name')}'에 default 블록이 없습니다.")

    raw_overrides = fixture.get("overrides") or []
    if not isinstance(raw_overrides, Sequence) or isinstance(raw_overrides, (str, bytes)):
        raise GoldenFixtureError(
            f"픽스처 '{fixture.get('name')}'의 overrides 형식이 잘못되었습니다."
        )

    overrides: dict[str, Mapping[str, Any]] = {}
    for item in raw_overrides:
        if isinstance(item, Mapping) and isinstance(item.get("check_id"), str):
            overrides[str(item["check_id"])] = item

    known = set(spec.check_ids)
    stranded = sorted(set(overrides) - known)
    if stranded:
        raise GoldenFixtureError(
            f"픽스처가 이 명세에 없는 검사를 참조합니다: {', '.join(stranded)}. "
            "검사를 삭제했다면 픽스처도 함께 갱신해야 합니다."
        )

    outcomes: list[CheckOutcome] = []
    for check_id in spec.check_ids:
        item = overrides.get(check_id, default)
        outcomes.append(
            CheckOutcome(
                check_id=check_id,
                status=CheckStatus(str(item.get("status", default.get("status", "UNKNOWN")))),
                confidence=float(item.get("confidence", default.get("confidence", 0.0))),
                affected_weight=float(item.get("affected_weight", 1.0)),
                evaluated_weight=float(item.get("evaluated_weight", 1.0)),
                evidence_ids=(f"golden::{fixture.get('name')}::{check_id}",),
            )
        )
    return outcomes


def _observed(result: ScoreResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "overall_score": result.overall_score,
        "overall_score_before_caps": result.overall_score_before_caps,
        "band_id": result.band_id,
        "coverage": result.coverage,
        "confidence": result.confidence,
        "effective_weight_total": result.effective_weight_total,
        "applied_cap_ids": [cap.cap_id for cap in result.applied_caps],
        "gate_status_codes": sorted({gate.status_code for gate in result.gates}),
    }


def _compare(result: ScoreResult, expected: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []

    if "status" in expected and result.status != expected["status"]:
        failures.append(
            f"상태: 기대 {_render(expected['status'])}, 실제 {_render(result.status)}"
        )

    for name, label in _SCALAR_FIELDS:
        if name not in expected:
            continue
        observed = getattr(result, name)
        if not _close(expected[name], observed):
            failures.append(
                f"{label}: 기대 {_render(expected[name])}, 실제 {_render(observed)}"
            )

    if "band_id" in expected and result.band_id != expected["band_id"]:
        failures.append(
            f"구간(band): 기대 {_render(expected['band_id'])}, 실제 {_render(result.band_id)}"
        )

    if "applied_cap_ids" in expected:
        observed_caps = [cap.cap_id for cap in result.applied_caps]
        if list(expected["applied_cap_ids"]) != observed_caps:
            failures.append(
                f"적용된 상한: 기대 {expected['applied_cap_ids']}, 실제 {observed_caps}"
            )

    if "gate_status_codes" in expected:
        observed_gates = sorted({gate.status_code for gate in result.gates})
        if sorted(set(expected["gate_status_codes"])) != observed_gates:
            failures.append(
                f"게이트: 기대 {sorted(set(expected['gate_status_codes']))}, "
                f"실제 {observed_gates}"
            )

    failures.extend(_compare_categories(result, expected.get("categories")))
    return failures


def _compare_categories(result: ScoreResult, expected: Any) -> list[str]:
    if not isinstance(expected, Mapping):
        return []
    failures: list[str] = []
    for category_id, wanted in expected.items():
        if not isinstance(wanted, Mapping):
            continue
        try:
            observed_category = result.category(str(category_id))
        except KeyError:
            failures.append(f"카테고리 '{category_id}'가 이 명세에 없습니다.")
            continue
        for name, want in wanted.items():
            got = getattr(observed_category, name, None)
            if isinstance(want, (int, float)) and not isinstance(want, bool):
                matched = _close(want, got)
            else:
                matched = want == got
            if not matched:
                failures.append(
                    f"카테고리 {category_id}.{name}: 기대 {_render(want)}, 실제 {_render(got)}"
                )
    return failures
