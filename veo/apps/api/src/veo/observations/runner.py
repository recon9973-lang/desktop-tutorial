"""Executing a prompt set against real engines, without ever overstating the result.

A run of this module produces :class:`~veo.observations.runs.ObservationRun` objects and
nothing else. Everything here exists to keep one sentence true: **a run may claim a
mention only if the answer that produced it is in storage.** There are four ways that
could quietly stop being true, and each has a mechanism —

* **The call never happened.** No credential, a timeout, a circuit-open provider: all of
  them produce an error-coded run. Never a "not mentioned", which would look identical in
  the data and would understate visibility every time the network was poor.
* **The answer could not be stored.** If :class:`RecordedAnswerStore.put` fails the run
  becomes error-coded too, even though the text is sitting in memory. A mention with no
  evidence is an assertion, and nobody can check it later.
* **The pass was cut short.** The budget ceiling stops the run and returns *what was not
  executed*, item by item. A silent cap reads as "we measured everything".
* **The sample was too thin.** Fewer than :data:`MIN_REPETITIONS` runs per prompt and
  engine is refused outright, or — if the caller insists — carried on the report as a
  standing caveat that travels with it.

Repetition count is the caller's business. The floor is not.
"""

from __future__ import annotations

import dataclasses
import hashlib
import logging
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol, runtime_checkable

from veo.contracts.enums import ErrorCode, ProviderState
from veo.observations.prompts import Prompt, PromptSet
from veo.observations.providers.base import ProviderAnswer
from veo.observations.providers.registry import ProviderRegistry
from veo.observations.providers.storage import (
    AnswerRecordKey,
    RecordedAnswer,
    RecordedAnswerStore,
    StoredAnswer,
)
from veo.observations.runs import ObservationRun, RunConditions, RunKind
from veo.observations.sampling import MIN_RUNS_FOR_EXPLORATION, MIN_SPREAD_BETWEEN_REPETITIONS

__all__ = [
    "MIN_REPETITIONS",
    "BrandSighting",
    "BrandTarget",
    "MentionDetector",
    "MentionVerdict",
    "ObservationRunner",
    "RepetitionFloorError",
    "RunReport",
    "SkippedWork",
    "StopReason",
]

LOGGER = logging.getLogger("veo.observations.runner")

#: The exploration minimum from the VEO-LAB sampling methodology. Below it a rate is not
#: reportable, so a runner asked for fewer refuses unless told explicitly to proceed.
MIN_REPETITIONS = MIN_RUNS_FOR_EXPLORATION


class RepetitionFloorError(ValueError):
    """The caller asked for fewer runs than the methodology can support."""


class StopReason(StrEnum):
    """Why a pass ended before it had executed everything it planned."""

    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    #: A ceiling was set but the engine's cost cannot be measured, so the ceiling cannot
    #: be honoured. Stopping is the only honest option: continuing would spend an
    #: unknown amount under a limit that was explicitly requested.
    COST_UNMEASURABLE = "COST_UNMEASURABLE"


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class BrandTarget:
    """The brand being looked for, by name and by the domains it owns."""

    names: tuple[str, ...]
    domains: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not any(name.strip() for name in self.names):
            raise ValueError("적어도 하나의 브랜드 이름이 필요합니다")


@dataclass(frozen=True, slots=True)
class BrandSighting:
    """한 답변에서 **한 브랜드**에 대해 확인된 것. 우리 것과 경쟁사 것이 같은 모양이다.

    같은 모양인 것이 요점이다. 점유율은 비율이고, 우리 쪽만 풍부하게 기록하고 경쟁사는
    이름만 남기면 나중에 비교를 만들 때 두 쪽이 다른 근거 위에 서게 된다.
    """

    entity_key: str
    is_own_brand: bool
    competitor_id: str | None
    mentioned: bool
    cited: bool
    needs_review: bool
    confidence: float | None
    evidence_ko: tuple[str, ...]
    first_position: int | None
    evidence_quote: str
    raw_occurrence_count: int

    def __post_init__(self) -> None:
        if self.mentioned and self.needs_review:
            raise ValueError(
                f"{self.entity_key}: 확정과 보류를 동시에 주장할 수 없습니다"
            )
        if self.cited and not self.mentioned:
            raise ValueError(f"{self.entity_key}: 인용은 언급을 포함합니다")


@dataclass(frozen=True, slots=True)
class MentionVerdict:
    """What was found in one answer, and what can be evidenced about it.

    Three outcomes, not two. ``mentioned`` and ``needs_review`` are mutually exclusive:
    a name that appeared but could not be pinned to *this* customer is held, never
    counted. Guessing at it is wrong in one direction only — upwards — and the customer
    has no way to see it.
    """

    mentioned: bool
    cited: bool
    matched_entities: tuple[str, ...] = ()
    needs_review: bool = False
    confidence: float | None = None
    """How sure the attribution was. ``None`` means the name did not appear at all —
    which is a different fact from "appeared, confidence zero" and must not share a cell
    with it."""
    evidence_ko: tuple[str, ...] = ()
    """The reasons, in the words a reviewer will read. A held finding with no reason
    reads as a malfunction rather than as a question."""
    first_position: int | None = None
    """The offset of the first hit in the answer text. Also the start of the span a
    reviewer will be shown, which is why ``evidence_quote`` must be the text at exactly
    this offset."""
    evidence_quote: str = ""
    """The exact characters at ``first_position`` — not a paraphrase, not a window.

    A reviewer deciding whether ``백세온담한의원`` is this customer needs the string the
    machine actually matched. Widening or trimming it here breaks the offset invariant
    that lets the finding be checked against the stored answer later.
    """
    raw_occurrence_count: int = 0
    sightings: tuple[BrandSighting, ...] = ()
    """선언된 브랜드 **전부** — 우리 것과 경쟁사 것.

    위의 낱개 필드들은 우리 브랜드의 값을 그대로 되풀이한다. 실행기와 저장 경로가
    이미 그 모양에 기대고 있어서 남겨 두었고, 점유율은 이 목록에서 나온다.
    """

    def __post_init__(self) -> None:
        if self.cited and not self.mentioned:
            raise ValueError("인용은 언급을 포함합니다")
        if self.mentioned and self.needs_review:
            raise ValueError(
                "확정과 보류를 동시에 주장할 수 없습니다. 보류는 아직 언급이 아닙니다"
            )


@runtime_checkable
class MentionDetector(Protocol):
    """Decides whether one stored answer mentions or cites the brand."""

    def judge(self, record: RecordedAnswer) -> MentionVerdict: ...


# --------------------------------------------------------------------------- #
# The report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SkippedWork:
    """One unit of planned work that was not executed, and why.

    엔진 이름만으로는 무엇을 못 했는지 알 수 없다. 같은 엔진을 검색 켬·끔 두 번 돌리므로,
    모드가 빠지면 "OPENAI 30건 건너뜀" 이 두 모드에서 15건씩인지 한 모드가 통째로
    빠진 것인지 구분되지 않는다. 뒤쪽이면 그 모드의 노출률은 아예 없는 것이다.
    """

    prompt_id: str
    engine: str
    attempt: int
    reason: StopReason
    reason_ko: str
    search_mode: str = ""


@dataclass(frozen=True, slots=True)
class RunReport:
    """Everything one pass produced, including what it did not do.

    ``runs`` alone would be a complete-looking set of measurements. ``skipped`` and
    ``stopped_reason`` are what stop it from being read as one.
    """

    runs: tuple[ObservationRun, ...]
    skipped: tuple[SkippedWork, ...]
    repetitions: int
    prompt_count: int
    engine_states: Mapping[str, ProviderState]
    total_cost_usd: float
    budget_spent_usd: float
    unpriced_calls: int
    below_repetition_floor: bool
    stopped_reason: StopReason | None = None

    @property
    def is_complete(self) -> bool:
        """Whether this pass may be read as the measurement it set out to make."""
        return (
            not self.skipped
            and self.stopped_reason is None
            and not self.below_repetition_floor
        )

    @property
    def summary_ko(self) -> str:
        parts = [
            f"실행 {len(self.runs)}회 "
            f"(프롬프트 {self.prompt_count}개, 반복 {self.repetitions}회)"
        ]
        if self.below_repetition_floor:
            parts.append(
                f"반복이 {self.repetitions}회로 탐색 최소 {MIN_REPETITIONS}회에 못 미칩니다. "
                "이 결과로 노출률을 말하지 마세요."
            )
        if self.stopped_reason is StopReason.BUDGET_EXCEEDED:
            parts.append(
                f"예산 상한에 도달해 {len(self.skipped)}건을 실행하지 않았습니다. "
                "이 집합은 계획한 측정의 일부입니다."
            )
        if self.stopped_reason is StopReason.COST_UNMEASURABLE:
            parts.append(
                f"이 엔진의 비용을 측정할 수 없어 예산 상한을 지킬 수 없으므로 "
                f"{len(self.skipped)}건을 실행하지 않았습니다."
            )
        if self.unpriced_calls:
            parts.append(
                f"{self.unpriced_calls}건은 비용을 알 수 없습니다"
                "(가격표 미설정 또는 사용량 미보고). 0원이라는 뜻이 아닙니다."
            )
        return " ".join(parts)

    def as_dict(self) -> dict[str, object]:
        return {
            "runs": [run.as_dict() for run in self.runs],
            "skipped": [dataclasses.asdict(item) for item in self.skipped],
            "repetitions": self.repetitions,
            "prompt_count": self.prompt_count,
            "engine_states": {name: str(state) for name, state in self.engine_states.items()},
            "total_cost_usd": self.total_cost_usd,
            "budget_spent_usd": self.budget_spent_usd,
            "unpriced_calls": self.unpriced_calls,
            "below_repetition_floor": self.below_repetition_floor,
            "stopped_reason": str(self.stopped_reason) if self.stopped_reason else None,
            "is_complete": self.is_complete,
            "summary_ko": self.summary_ko,
        }


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _Unit:
    """One question, one engine, one attempt — the atom of idempotence."""

    prompt: Prompt
    engine: str
    attempt: int
    requested: RunConditions

    @property
    def key(self) -> AnswerRecordKey:
        return AnswerRecordKey(
            prompt_id=self.prompt.prompt_id,
            conditions_fingerprint=self.requested.fingerprint,
            attempt=self.attempt,
        )

    @property
    def repetition_group(self) -> str:
        """같은 질문·같은 조건의 반복끼리 묶는 축. 간격은 이 축 안에서만 뜻이 있다.

        다른 질문끼리 붙어 나가는 것은 문제가 아니다. 문제는 **같은 질문**을 같은 순간에
        여러 번 묻는 것이다.
        """
        return f"{self.prompt.prompt_id}|{self.requested.fingerprint}"

    @property
    def run_id(self) -> str:
        """Deterministic in ``(prompt_id, requested conditions, attempt)``.

        The *requested* conditions, not the observed ones: the identity of a unit of work
        has to be knowable before the call, or a retry would land under a new id and the
        pass would stop being idempotent.
        """
        payload = f"{self.prompt.prompt_id}|{self.requested.fingerprint}|{self.attempt}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class _UnitResult:
    unit: _Unit
    record: RecordedAnswer | None
    stored: StoredAnswer | None
    error_code: str | None
    latency_ms: int
    cost_usd: float | None
    called_provider: bool
    #: 값을 못 낸 이유. 실패한 호출에도 붙는다 — 실패도 과금될 수 있다.
    cost_basis: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


# --------------------------------------------------------------------------- #
# The runner
# --------------------------------------------------------------------------- #


class ObservationRunner:
    """Runs a prompt set against a set of engines, repeatedly, under a budget."""

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        store: RecordedAnswerStore,
        detector: MentionDetector,
        max_concurrency: int = 4,
        budget_usd: float | None = None,
        #: 이 실행이 정기 측정인가 수동 측정인가. 실행기가 만드는 모든 `ObservationRun`
        #: 에 그대로 찍힌다 — 나중에 비율을 낼 때 섞이는 것을 거부할 수 있게.
        kind: RunKind = RunKind.SCHEDULED,
        repetition_interval: timedelta = MIN_SPREAD_BETWEEN_REPETITIONS,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        on_progress: Callable[[int, int], None] | None = None,
        logger: logging.Logger = LOGGER,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if budget_usd is not None and budget_usd <= 0:
            raise ValueError("budget_usd must be positive when set")
        if repetition_interval < timedelta(0):
            raise ValueError("repetition_interval cannot be negative")
        self._registry = registry
        self._store = store
        self._detector = detector
        self._max_concurrency = max_concurrency
        self._budget = budget_usd
        self._kind = kind
        #: 같은 질문의 다음 반복까지 최소로 기다리는 시간. 0 이면 예전처럼 연달아
        #: 던진다 — 그때 비율에 붙는 경고문이 달라진다(`RepetitionSpread`).
        self._repetition_interval = repetition_interval
        self._clock = clock
        self._sleep = sleep
        #: 오래 기다리는 동안 밖에서 "아직 살아 있다" 를 알 수 있게 한다. 이것이 없으면
        #: 간격을 벌린 실행이 작업 목록에서 **멈춘 것으로** 보인다.
        self._on_progress = on_progress
        self._logger = logger

    def execute(
        self,
        prompt_set: PromptSet,
        *,
        conditions: Sequence[RunConditions],
        repetitions: int,
        allow_below_floor: bool = False,
    ) -> RunReport:
        """Ask every prompt under every condition ``repetitions`` times.

        조건은 **목록**이지 엔진 이름을 열쇠로 하는 표가 아니다. 표였을 때는 같은 엔진의
        검색 켬·끔이 한 열쇠로 겹쳐 뒤엣것만 남았고, 겹쳤다는 사실이 아무 데도 남지
        않았다 — 반쪽만 돌고 두 모드를 다 잰 것처럼 읽혔다. 목록에는 겹칠 열쇠가 없다.

        Raises :class:`RepetitionFloorError` below the exploration minimum unless
        ``allow_below_floor`` is set, in which case the shortfall is carried on the
        report rather than forgotten.
        """
        if not conditions:
            raise ValueError("적어도 하나의 엔진 조건이 필요합니다")
        if repetitions < 1:
            raise RepetitionFloorError("반복 횟수는 1회 이상이어야 합니다")
        if repetitions < MIN_REPETITIONS and not allow_below_floor:
            raise RepetitionFloorError(
                f"프롬프트·엔진당 최소 {MIN_REPETITIONS}회 실행이 필요합니다 "
                f"(요청 {repetitions}회). 그 아래에서는 노출률을 말할 수 없습니다. "
                "그래도 실행하려면 allow_below_floor 를 명시하세요."
            )

        seen: set[str] = set()
        for condition in conditions:
            self._registry.resolve(condition.engine)
            if condition.slot in seen:
                # 조용히 합치면 요청한 것보다 적게 돌고도 다 돈 것으로 보인다. 반복은
                # `repetitions` 로 늘리는 것이지 같은 조건을 두 번 적어서 늘리지 않는다.
                raise ValueError(f"같은 조건이 두 번 들어왔습니다: {condition.label_ko}")
            seen.add(condition.slot)

        units = _plan(prompt_set, conditions, repetitions)
        results, skipped, stopped, spent = self._run_units(units)

        runs = tuple(
            sorted(
                (self._build_run(result) for result in results),
                key=lambda run: (run.prompt_id, run.conditions.engine, run.run_id),
            )
        )
        if skipped:
            self._logger.warning(
                "관측 실행이 중단되었습니다: 계획한 작업 중 %d건을 실행하지 않았습니다 (사유=%s). "
                "이 결과 집합은 계획한 측정의 일부입니다.",
                len(skipped),
                stopped.value if stopped else "UNKNOWN",
            )

        return RunReport(
            runs=runs,
            skipped=tuple(skipped),
            repetitions=repetitions,
            prompt_count=len(prompt_set.prompts),
            engine_states=self._registry.states(),
            total_cost_usd=sum(
                result.cost_usd for result in results if result.cost_usd is not None
            ),
            budget_spent_usd=spent,
            unpriced_calls=sum(1 for result in results if result.cost_usd is None),
            below_repetition_floor=repetitions < MIN_REPETITIONS,
            stopped_reason=stopped,
        )

    # ------------------------------------------------------------- execution

    def _run_units(
        self, units: Sequence[_Unit]
    ) -> tuple[list[_UnitResult], list[SkippedWork], StopReason | None, float]:
        """Dispatch under the concurrency limit, stopping rather than truncating."""
        results: list[_UnitResult] = []
        stopped: StopReason | None = None
        spent = 0.0
        spend_lock = threading.Lock()
        index = 0

        # 같은 질문·같은 조건의 반복을 언제부터 다시 던져도 되는가.
        #
        # 계획이 반복-우선 순서라(`_plan`) 1회차 전체가 먼저 나가고 2회차가 뒤따른다.
        # 따라서 여기서 기다리는 시간은 질문 수만큼 곱해지지 않고, 회차 사이에 한 번씩만
        # 든다 — 질문이 여섯이든 스물이든 늘어나는 총 시간은 같다.
        eligible_at: dict[str, datetime] = {}

        with ThreadPoolExecutor(max_workers=self._max_concurrency) as pool:
            pending: dict[Future[_UnitResult], _Unit] = {}

            def fill() -> None:
                """지금 던져도 되는 것만 던진다. 아직 이른 것은 순서를 지킨 채 남긴다."""
                nonlocal index
                while (
                    stopped is None
                    and index < len(units)
                    and len(pending) < self._max_concurrency
                ):
                    unit = units[index]
                    ready = eligible_at.get(unit.repetition_group)
                    if ready is not None and self._clock() < ready:
                        # 뒤의 단위를 앞질러 보내지 않는다. 반복-우선 순서를 흐트러뜨리면
                        # 예산으로 잘렸을 때 **회차가 아니라 질문이** 잘려 나간다.
                        return
                    index += 1
                    pending[pool.submit(self._execute_unit, unit)] = unit

            def wait_until_something_is_eligible() -> None:
                """던질 것도 기다릴 것도 없을 때, 다음 반복이 익을 때까지 잔다.

                이 대기가 없으면 위 `fill()` 이 아무것도 못 던진 채 루프가 끝나고, 남은
                회차가 조용히 `skipped` 로 넘어간다 — **간격을 두려다 측정을 잃는다.**
                """
                if stopped is not None or index >= len(units):
                    return
                ready = eligible_at.get(units[index].repetition_group)
                if ready is None:
                    return
                remaining = (ready - self._clock()).total_seconds()
                if remaining <= 0:
                    return
                if self._on_progress is not None:
                    self._on_progress(len(results), len(units))
                self._logger.info(
                    "반복 간격 대기 %.0f초 (%d/%d 완료)", remaining, len(results), len(units)
                )
                self._sleep(remaining)

            fill()
            while pending or index < len(units):
                if not pending:
                    wait_until_something_is_eligible()
                    fill()
                    if not pending:
                        # 잤는데도 못 던졌다면 시계나 sleep 이 우리가 아는 대로 움직이지
                        # 않는 것이다. 조용히 도는 대신 멈춘다.
                        break
                    continue
                done, _ = wait(set(pending), return_when=FIRST_COMPLETED)
                for future in done:
                    unit = pending.pop(future)
                    result = future.result()
                    results.append(result)
                    # 이 질문의 다음 반복은 여기서부터 잰다. **호출이 끝난 시각**을
                    # 기준으로 삼는 이유는, 응답이 느린 엔진에서 시작 시각을 쓰면 실제
                    # 간격이 우리가 요구한 것보다 짧아지기 때문이다.
                    if self._repetition_interval:
                        eligible_at[unit.repetition_group] = (
                            self._clock() + self._repetition_interval
                        )
                    if stopped is not None or self._budget is None:
                        continue
                    with spend_lock:
                        if result.called_provider and result.record is not None:
                            if result.cost_usd is None:
                                stopped = StopReason.COST_UNMEASURABLE
                                continue
                            spent += result.cost_usd
                        if spent >= self._budget:
                            stopped = StopReason.BUDGET_EXCEEDED
                # In-flight work is always drained: it has already been paid for, and
                # discarding it would throw away a measurement VEO was billed for.
                fill()

        skipped = [
            SkippedWork(
                prompt_id=unit.prompt.prompt_id,
                engine=unit.engine,
                search_mode=str(unit.requested.search_mode),
                attempt=unit.attempt,
                reason=stopped or StopReason.BUDGET_EXCEEDED,
                reason_ko=_SKIP_REASONS_KO[stopped or StopReason.BUDGET_EXCEEDED],
            )
            for unit in units[index:]
        ]
        return results, skipped, stopped, spent

    def _execute_unit(self, unit: _Unit) -> _UnitResult:
        existing = self._store.find(unit.key)
        if existing is not None:
            # Already measured under this exact key. Re-asking would spend money to
            # produce a second answer to a question that already has a stored one.
            record = self._store.read(existing.ref)
            return _UnitResult(
                unit=unit,
                record=record,
                stored=existing,
                error_code=None,
                latency_ms=record.latency_ms,
                cost_usd=record.cost_usd,
                called_provider=False,
                cost_basis=str(record.cost_basis),
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
            )

        provider = self._registry.resolve(unit.engine)
        outcome = provider.ask(unit.prompt.text, conditions=unit.requested)
        answer = outcome.value
        if not isinstance(answer, ProviderAnswer):
            code = (
                outcome.failure.error_code
                if outcome.failure is not None
                else ErrorCode.PROVIDER_UNAVAILABLE
            )
            return _UnitResult(
                unit=unit,
                record=None,
                stored=None,
                error_code=str(code),
                latency_ms=outcome.latency_ms,
                cost_usd=outcome.cost_usd,
                called_provider=True,
                # 실패한 호출도 시간을 썼고 과금됐을 수 있다. 아무것도 안 남기면
                # 성공한 호출의 비용만으로 다음 실행이 승인된다.
                cost_basis=str(outcome.cost_basis),
                input_tokens=outcome.input_tokens,
                output_tokens=outcome.output_tokens,
            )

        record = RecordedAnswer(
            engine=provider.engine,
            model=answer.model,
            model_version=answer.model_version,
            text=answer.text,
            citations=answer.citations,
            citation_support=answer.citation_support,
            latency_ms=outcome.latency_ms,
            cost_usd=outcome.cost_usd,
            cost_basis=outcome.cost_basis,
            input_tokens=answer.input_tokens,
            output_tokens=answer.output_tokens,
            executed_at=self._clock(),
        )
        try:
            stored = self._store.put(unit.key, record)
        except Exception:
            # The answer exists but nothing can be shown to a customer who disputes the
            # claim later. Without evidence there is no mention — only an assertion.
            self._logger.exception(
                "원문 답변을 보관하지 못해 실행을 오류로 기록합니다 "
                "(prompt=%s, engine=%s, attempt=%d)",
                unit.prompt.prompt_id,
                unit.engine,
                unit.attempt,
            )
            return _UnitResult(
                unit=unit,
                record=None,
                stored=None,
                error_code=str(ErrorCode.INTERNAL_ERROR),
                latency_ms=outcome.latency_ms,
                cost_usd=outcome.cost_usd,
                called_provider=True,
            )

        return _UnitResult(
            unit=unit,
            record=record,
            stored=stored,
            error_code=None,
            latency_ms=outcome.latency_ms,
            cost_usd=outcome.cost_usd,
            called_provider=True,
        )

    # ----------------------------------------------------------------- rows

    def _build_run(self, result: _UnitResult) -> ObservationRun:
        unit = result.unit
        record, stored = result.record, result.stored
        if record is None or stored is None:
            # No answer in storage: an error-coded run, and explicitly not an observation
            # that the brand was absent.
            return ObservationRun(
                run_id=unit.run_id,
                prompt_id=unit.prompt.prompt_id,
                conditions=unit.requested,
                executed_at=self._clock(),
                kind=self._kind,
                raw_answer_ref=None,
                raw_answer_hash=None,
                brand_mentioned=False,
                brand_cited=False,
                latency_ms=result.latency_ms,
                cost_usd=result.cost_usd,
                cost_basis=result.cost_basis,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                error_code=result.error_code,
            )

        verdict = self._detector.judge(record)
        return ObservationRun(
            run_id=unit.run_id,
            prompt_id=unit.prompt.prompt_id,
            # The model version is what actually answered, not what was asked for.
            conditions=dataclasses.replace(
                unit.requested, model_version=record.model_version
            ),
            executed_at=record.executed_at,
            kind=self._kind,
            raw_answer_ref=stored.ref,
            raw_answer_hash=stored.sha256,
            brand_mentioned=verdict.mentioned,
            brand_cited=verdict.cited,
            # 인용을 볼 수 있었는지는 응답의 성질이다. 여기서 흘리면 인용률의 분모를
            # 정직하게 만들 수 없다.
            citation_support=str(record.citation_support),
            latency_ms=record.latency_ms,
            cost_usd=record.cost_usd,
            cost_basis=str(record.cost_basis),
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            error_code=None,
            citations=record.citations,
            mentioned_entities=verdict.matched_entities,
            mention_pending_review=verdict.needs_review,
            mention_confidence=verdict.confidence,
            mention_evidence_ko=verdict.evidence_ko,
            mention_first_position=verdict.first_position,
            mention_quote=verdict.evidence_quote,
            mention_raw_occurrences=verdict.raw_occurrence_count,
            sightings=verdict.sightings,
        )


_SKIP_REASONS_KO: Mapping[StopReason, str] = {
    StopReason.BUDGET_EXCEEDED: (
        "예산 상한에 도달해 실행하지 않았습니다. 측정하지 않은 것이며, "
        "브랜드가 언급되지 않았다는 뜻이 아닙니다."
    ),
    StopReason.COST_UNMEASURABLE: (
        "이 엔진의 호출 비용을 알 수 없어 예산 상한을 지킬 수 없으므로 실행하지 않았습니다."
    ),
}


def _plan(
    prompt_set: PromptSet, conditions: Sequence[RunConditions], repetitions: int
) -> tuple[_Unit, ...]:
    """Repetition-major order, so a truncated pass loses whole rounds.

    Prompt-major order would give the first prompts every repetition and the last ones
    none, turning a budget stop into a silently narrowed prompt set — the exact failure
    :mod:`veo.observations.prompts` exists to prevent.

    조건 안에서는 칸 이름 순으로 돈다. 예산이 중간에 끊겨도 같은 회차 안에서 어느 조건이
    먼저였는지가 실행마다 달라지지 않는다.
    """
    ordered = sorted(conditions, key=lambda condition: condition.slot)
    return tuple(
        _Unit(
            prompt=prompt,
            engine=condition.engine,
            attempt=attempt,
            requested=condition,
        )
        for attempt in range(1, repetitions + 1)
        for prompt in prompt_set.prompts
        for condition in ordered
    )
