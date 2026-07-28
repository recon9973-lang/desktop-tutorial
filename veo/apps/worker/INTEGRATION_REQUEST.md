# Integration requests from `apps/worker` (Phase 0)

Requests for the integration maintainer who owns `apps/api/src/veo/contracts/`.
Nothing here is blocking — the Phase 0 runtime is complete and green without any of it.
Each item is worked around locally today; the workaround is stated so you can judge
whether the contract should absorb it.

---

## 1. `veo-api` has no `py.typed` marker (low effort, real payoff)

**Problem.** `apps/api/pyproject.toml` ships `src/veo` without a `py.typed` file, so mypy
treats every contract type as `Any` in any consumer. The worker imports `JobStatus`,
`JobDescriptor`, `ErrorCode` constantly; none of it is actually type-checked, which
defeats the point of a shared contract package.

**Workaround in place.** `apps/worker/pyproject.toml` adds
`ignore_missing_imports = true` for `veo.*`, with a comment to remove it once fixed.

**Request.** Add an empty `src/veo/py.typed` and include it in the hatch wheel targets.

---

## 2. `JobDescriptor` cannot carry partial-success counts

**Problem.** `PARTIAL_SUCCESS` is a first-class status, and the contract's own docstring
says a scan that collected 80% is "more useful — and more honest — than one reported as a
flat failure". But `JobDescriptor` only exposes `partial_result_available: bool`. There is
nowhere to put *80 of 100*. A caller can see that the run was partial but not how partial,
which is the one thing that decides whether the result is usable.

`JobStage.items_done` / `items_total` are per-stage progress counters, not a job-level
collection verdict, and they are reset/advanced by the progress tracker — overloading them
for this would conflate "how far along" with "how much did we actually get".

**Workaround in place.** `veo_worker.runtime.partial.PartialOutcome` holds
`collected` / `attempted` / `planned` / `skipped` / `coverage_ratio` / `failures_by_code`
internally, but the runtime cannot publish them on the descriptor, so the API cannot read
them.

**Request.** Either add an optional field to `JobDescriptor`:

```python
collected_units: int | None = None
attempted_units: int | None = None
planned_units: int | None = None
```

or an optional nested model (`partial_summary: PartialSummary | None`). Naming is yours;
the requirement is that the numbers reach the API without a side channel.

---

## 3. No `ErrorCode` distinguishes "not implemented yet" from a real internal error

**Problem.** `ErrorCode.INTERNAL_ERROR` is in `RETRYABLE_ERROR_CODES`. A Phase 0 stub
raising `NotImplementedError` maps to `INTERNAL_ERROR` and would therefore be retried
three times before failing — three times the queue time and three times the log noise for
something no retry can fix.

**Workaround in place.** `veo_worker.runtime.errors` returns an explicit
`retryable=False` override alongside the code, and `JobStateMachine.record_failure`
accepts that override. This is arguably the right design regardless — retryability is a
property of the *occurrence*, not only of the code — but it means the wire-level
`ApiError.retryable` and the code's membership in `RETRYABLE_ERROR_CODES` can disagree.

**Request.** Confirm that per-occurrence retryability overriding the code default is
acceptable. If not, consider `ErrorCode.NOT_IMPLEMENTED` (non-retryable). No change is
needed if you are happy with the override.

---

## 4. Cancellation carries no reason field

**Problem.** `CANCELLED` jobs differ in kind: cancelled by the user, cancelled by a quota
guard, cancelled by an admin. `JobDescriptor` has `safe_error_message`, which the runtime
fills from the static safe-message table, so the reason is lost.

**Workaround in place.** `CancellationToken.reason` is captured and logged, but not
published.

**Request.** Consider `cancellation_reason: str | None` on `JobDescriptor`, or confirm
that the generic message is intentional. Note that any such field is user-visible and must
be constrained to a safe enum rather than free text — a free-text reason forwarded from a
provider is exactly how credentials leak into a customer-facing surface.

---

## 5. Provisional phase numbers in the task stubs

Only "SEO collector lands in Phase 2" is fixed by the Phase 0 brief. The other seven
entries in `PHASE_NOTES` (`veo_worker/runtime/tasks/__init__.py`) are this package's
reading of the roadmap and are flagged as provisional in a comment. Please correct them if
the real plan differs — they appear in `NotImplementedError` messages that developers will
read.
