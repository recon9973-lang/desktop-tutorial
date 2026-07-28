"""Latency and error accounting, with the honesty built into the reporting.

Two things this module refuses to do:

* **Report a percentile the sample size cannot support.** A p99 computed from 40 samples
  is the maximum wearing a more authoritative name. Every percentile here declares the
  sample count it needs, and prints ``n/a`` with the reason when it does not have it.
* **Average away the failures.** Errors are counted and reported separately, and the
  latency of a failed request is kept out of the success percentiles — a run that got
  fast 500s would otherwise look better than a run that got slow 200s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = ["Outcome", "Report", "Samples", "percentile"]


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Nearest-rank percentile over an already-sorted list.

    Nearest-rank rather than interpolated: an interpolated p99 reports a latency that no
    request actually experienced, which is a strange thing to put in a capacity argument.
    """
    if not sorted_values:
        raise ValueError("no samples")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    rank = math.ceil(fraction * len(sorted_values))
    return sorted_values[rank - 1]


@dataclass(frozen=True, slots=True)
class Outcome:
    """One request. ``ok`` is the caller's judgement, not merely "no exception"."""

    latency_ms: float
    ok: bool
    label: str


@dataclass
class Samples:
    """Everything observed for one scenario."""

    name: str
    outcomes: list[Outcome] = field(default_factory=list)
    wall_seconds: float = 0.0
    concurrency: int = 0

    def record(self, latency_ms: float, *, ok: bool, label: str) -> None:
        self.outcomes.append(Outcome(latency_ms=latency_ms, ok=ok, label=label))

    def report(self) -> Report:
        successes = sorted(o.latency_ms for o in self.outcomes if o.ok)
        failures = [o for o in self.outcomes if not o.ok]
        labels: dict[str, int] = {}
        for outcome in self.outcomes:
            labels[outcome.label] = labels.get(outcome.label, 0) + 1
        return Report(
            name=self.name,
            concurrency=self.concurrency,
            total=len(self.outcomes),
            failed=len(failures),
            wall_seconds=self.wall_seconds,
            success_latencies_ms=successes,
            label_counts=labels,
        )


#: How many samples a percentile needs before it means anything. The rule of thumb is
#: that the percentile must be supported by at least 5 observations in its tail.
_MINIMUM_SAMPLES = {0.50: 20, 0.90: 50, 0.95: 100, 0.99: 500}


@dataclass(frozen=True, slots=True)
class Report:
    name: str
    concurrency: int
    total: int
    failed: int
    wall_seconds: float
    success_latencies_ms: list[float]
    label_counts: dict[str, int]

    @property
    def error_rate(self) -> float:
        return self.failed / self.total if self.total else 0.0

    @property
    def throughput_rps(self) -> float:
        return self.total / self.wall_seconds if self.wall_seconds > 0 else 0.0

    def percentile_text(self, fraction: float) -> str:
        needed = _MINIMUM_SAMPLES[fraction]
        have = len(self.success_latencies_ms)
        if have < needed:
            return f"n/a (needs >={needed} ok samples, had {have})"
        return f"{percentile(self.success_latencies_ms, fraction):8.2f} ms"

    def render(self) -> str:
        lines = [
            f"  scenario     : {self.name}",
            f"  concurrency  : {self.concurrency}",
            (
                f"  requests     : {self.total} in {self.wall_seconds:.2f}s "
                f"({self.throughput_rps:.1f}/s)"
            ),
            f"  errors       : {self.failed} ({self.error_rate * 100:.2f}%)",
        ]
        if self.success_latencies_ms:
            lines += [
                f"  latency min  : {self.success_latencies_ms[0]:8.2f} ms",
                f"  latency p50  : {self.percentile_text(0.50)}",
                f"  latency p90  : {self.percentile_text(0.90)}",
                f"  latency p95  : {self.percentile_text(0.95)}",
                f"  latency p99  : {self.percentile_text(0.99)}",
                f"  latency max  : {self.success_latencies_ms[-1]:8.2f} ms",
            ]
        else:
            lines.append("  latency      : no successful request to measure")
        detail = ", ".join(f"{label}={count}" for label, count in sorted(self.label_counts.items()))
        lines.append(f"  outcomes     : {detail}")
        return "\n".join(lines)
