"""One observation run, and the rules for pooling several into a rate.

Asking GPT-5 with browsing enabled is a different measurement from asking the same model
with browsing off: different sources reach the answer, and often a different conclusion.
Pooling the two into one "AI 노출률" is the same failure as comparing a four-page crawl
against a two-hundred-page one — the arithmetic is correct and the number means nothing.

Hence:

* A run records exactly what produced it: engine, model, model version, search mode,
  account state, locale. Any of those differing makes it a different measurement.
* :func:`aggregate_rate` **refuses** to pool runs whose conditions differ. Mixing can be
  requested, and then the resulting rate says so in its own caption.
* A failed run leaves the denominator. A provider timeout is an absence of measurement,
  not an observation that the brand was missing — counting it as the latter quietly
  understates visibility every time the network is poor.
* A claimed mention requires a stored answer. Without the raw text there is no evidence,
  only an assertion, and nobody can check it later.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from veo.observations.sampling import ObservedRate


class SearchMode(StrEnum):
    """Whether the engine could retrieve at answer time."""

    BROWSING = "BROWSING"
    NO_BROWSING = "NO_BROWSING"
    UNKNOWN = "UNKNOWN"


class AccountState(StrEnum):
    """Personalisation changes answers, so it is part of the measurement."""

    ANONYMOUS = "ANONYMOUS"
    SIGNED_IN = "SIGNED_IN"
    UNKNOWN = "UNKNOWN"


class RunKind(StrEnum):
    """왜 이 측정이 일어났는가. 조건이 같아도 이것이 다르면 합칠 수 없다.

    ``SCHEDULED`` 는 발행된 질문 집합을 정해진 주기로 돌린 것이다. 무엇을 언제 묻는지가
    사람 손을 떠나 있어 추이의 점이 될 수 있다.

    ``MANUAL`` 은 사람이 그 순간 고른 검색어 하나를 잰 것이다. 조건(엔진·모델·검색모드)이
    정기 측정과 똑같아도 **고른 사람이 다르게 만든다** — 이것이 ADR 0015 가 막는 바로
    그 자리다:

        "경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. **질문만 고르면 된다.**"
        (docs/adr/0015-prompt-sets-are-audited-artefacts.md:8)

    수동 측정은 그 자체로 쓸모가 있다 — "지금 이 검색어로 우리가 나오나" 는 정당한
    질문이다. 다만 그 답을 추이에 섞으면, 잘 나오는 검색어를 골라 재는 것만으로 그래프가
    올라간다. 그래서 섞이지 않게 하는 것이 코드의 일이다(:func:`aggregate_rate`).
    """

    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class MixedConditionsError(ValueError):
    """Runs from different setups were about to be pooled into one rate."""


class MixedRunKindsError(ValueError):
    """정기 측정과 수동 측정이 하나의 비율로 합쳐지려던 참이었다."""


@dataclass(frozen=True, slots=True)
class RunConditions:
    """The setup an answer came from. Two runs are comparable only if these match."""

    engine: str
    model: str
    model_version: str
    search_mode: SearchMode
    account_state: AccountState
    locale: str = "ko-KR"

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "engine": self.engine,
                "model": self.model,
                "model_version": self.model_version,
                "search_mode": str(self.search_mode),
                "account_state": str(self.account_state),
                "locale": self.locale,
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    @property
    def slot(self) -> str:
        """실행 계획에서 이 조건이 차지하는 칸의 이름.

        엔진 이름만으로는 부족하다. **검색 켬과 끔은 서로 다른 조건이고**, 같은 엔진을
        두 모드로 돌리는 것이 이 관측의 목적이다 — 검색을 켜야 인용이 나오고, 끄면 모델이
        학습으로 아는 것만 나온다. 둘을 엔진 이름 하나로 묶으면 나중에 넣은 쪽이 앞의 것을
        덮어 **한 모드만 실행되고도 두 모드를 쟀다고 읽힌다.**

        모델도 칸을 가른다. 모델마다 인용을 돌려주는지가 다르므로(실측: `gpt-5`·`gpt-4o`
        는 돌려주고 `gpt-4.1`·`gpt-4o-mini` 는 돌려주지 않는다) 두 모델을 한 칸으로
        묶으면 "인용 0건" 이 모델 탓인지 검색 탓인지 갈라낼 수 없다.

        저장 쪽은 이미 셋을 구분한다 — `ai_engines` 는 (제공자, 모델, 검색모드) 로
        유일하다(ADR 0010). 여기가 그 셋과 같은 축이다. 나뉘지 않던 곳은 실행 계획의
        표뿐이었다.
        """
        return f"{self.engine.upper()}:{self.model}:{self.search_mode}"

    @property
    def label_ko(self) -> str:
        mode = {
            SearchMode.BROWSING: "검색 사용",
            SearchMode.NO_BROWSING: "검색 미사용",
            SearchMode.UNKNOWN: "검색 여부 불명",
        }[self.search_mode]
        return f"{self.engine} {self.model}@{self.model_version} ({mode}, {self.locale})"

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "model": self.model,
            "model_version": self.model_version,
            "search_mode": str(self.search_mode),
            "account_state": str(self.account_state),
            "locale": self.locale,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ObservationRun:
    """One question, asked once, under stated conditions.

    ``raw_answer_ref`` points at object storage rather than carrying the text. Raw AI
    answers are large, sensitive, and belong behind the evidence permission — the run
    keeps a pointer and a hash so the claim stays checkable without the row itself
    becoming the disclosure risk.
    """

    run_id: str
    prompt_id: str
    conditions: RunConditions
    executed_at: datetime
    #: 정기 측정인가, 사람이 그 자리에서 고른 수동 측정인가. 기본값이 ``SCHEDULED`` 인
    #: 것은 이 필드가 생기기 전의 모든 실행이 정기 측정이었기 때문이다.
    kind: RunKind = field(default=RunKind.SCHEDULED, kw_only=True)
    raw_answer_ref: str | None
    raw_answer_hash: str | None
    brand_mentioned: bool
    brand_cited: bool
    latency_ms: int | None = None
    cost_usd: float | None = None
    #: 비용을 못 냈다면 **왜** 못 냈는지. 다섯 가지고, 처방이 각각 다르다.
    #:
    #: 이 값은 제공자 어댑터가 계산해 놓고 여기까지 오지 못했다. 그래서 저장된 실행을
    #: 두고 "이번 달 얼마 썼나" 를 물으면 "모른다" 까지는 답할 수 있어도 "가격표에
    #: 모델이 없어서" 인지 "호출이 실패해서" 인지는 답할 수 없었다 — 고쳐야 할 것이
    #: 완전히 다른데도.
    cost_basis: str | None = None
    #: 실제로 오간 토큰. 가격표가 비어 있어도 **이건 잴 수 있다.**
    #:
    #: 가격이 없다고 사용량까지 모르는 것은 아니다. 토큰 수는 지금 유일하게 확실한
    #: 지출 신호이고, 제공자 응답에서 이미 읽고 있었다.
    input_tokens: int | None = None
    output_tokens: int | None = None
    error_code: str | None = None
    citations: tuple[str, ...] = field(default=())
    mentioned_entities: tuple[str, ...] = field(default=())
    mention_pending_review: bool = False
    """이름은 나왔는데 **이 고객인지 갈리지 않았다.**

    `brand_mentioned=False` 와 같은 칸에 두면 안 된다. "안 나왔다" 와 "누구인지
    모르겠다" 는 다른 사실이고, 후자는 사람이 보면 풀리는 것이라 큐로 간다.
    노출률의 분자로 세지 않으므로 그 비율은 **확정 하한**이 되며, 얼마나 하한인지는
    :func:`aggregate_rate` 가 보류 건수로 함께 말한다.
    """
    mention_confidence: float | None = None
    """귀속 확신도. `None` 은 이름 자체가 안 나왔다는 뜻이다 — 0.0 과 다른 사실이다."""
    mention_evidence_ko: tuple[str, ...] = field(default=())
    mention_first_position: int | None = None
    mention_quote: str = ""
    sightings: tuple[Any, ...] = field(default=())
    """선언된 브랜드 전부에 대한 결과 — 우리 것과 경쟁사 것.

    점유율(SOV)이 여기서 나온다. 우리 것만 남기면 나중에 비교를 만들 때 경쟁사
    숫자를 **사람이 손으로 넣게** 되고, 손으로 넣은 값은 잰 값처럼 보이지만 아니다.

    타입이 `Any` 인 것은 순환 참조 때문이다. `BrandSighting` 은 `runner` 에 있고
    그 모듈이 이 모듈을 가져간다 — `citation_support` 가 문자열인 것과 같은 이유다.
    """
    mention_raw_occurrences: int = 0
    citation_support: str | None = None
    """이 응답에서 **인용을 볼 수 있었는가**. `STRUCTURED` 이거나 아니거나.

    인용률의 분모가 여기 걸려 있다. 인용을 볼 수 없었던 응답을 분모에 넣으면 인용률이
    낮게 나오고, 그 낮은 값은 **사이트 탓처럼 읽힌다.** 실제로는 그 모델이 출처를
    알려주지 않은 것이다 — 검색을 껐거나, 켰어도 인용을 돌려주지 않는 모델이거나.

    `None` 은 기록되지 않았다는 뜻이고, 그때도 인용률 분모에 넣으면 안 된다.

    타입이 문자열인 것은 순환 참조 때문이다. `CitationSupport` 는
    `providers.base` 에 있고 그 모듈이 이 모듈을 가져간다.
    """

    def __post_init__(self) -> None:
        if self.brand_cited and not self.brand_mentioned:
            raise ValueError(
                f"{self.run_id}: 인용이 있는데 언급이 없습니다. 인용은 언급을 포함합니다"
            )
        if self.brand_mentioned and self.raw_answer_ref is None:
            raise ValueError(
                f"{self.run_id}: 언급을 주장하려면 원문 답변이 보관되어야 합니다. "
                "원문 없는 언급은 근거가 아니라 주장입니다"
            )
        if self.error_code and self.brand_mentioned:
            raise ValueError(f"{self.run_id}: 실패한 실행은 언급을 주장할 수 없습니다")
        if self.brand_mentioned and self.mention_pending_review:
            raise ValueError(
                f"{self.run_id}: 확정된 언급이 동시에 검수 대기일 수 없습니다. "
                "보류는 아직 언급이 아닙니다"
            )
        if self.mention_pending_review and self.raw_answer_ref is None:
            raise ValueError(
                f"{self.run_id}: 검수로 넘기려면 원문 답변이 보관되어야 합니다. "
                "볼 수 없는 답변에 대해서는 사람도 판단할 수 없습니다"
            )

    @property
    def is_valid_execution(self) -> bool:
        """Whether this run measured anything at all."""
        return self.error_code is None and self.raw_answer_ref is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "prompt_id": self.prompt_id,
            "citation_support": self.citation_support,
            "conditions": self.conditions.as_dict(),
            "kind": str(self.kind),
            "executed_at": self.executed_at.isoformat(),
            "raw_answer_ref": self.raw_answer_ref,
            "raw_answer_hash": self.raw_answer_hash,
            "brand_mentioned": self.brand_mentioned,
            "brand_cited": self.brand_cited,
            "mention_pending_review": self.mention_pending_review,
            "mention_confidence": self.mention_confidence,
            "mention_evidence_ko": list(self.mention_evidence_ko),
            "citations": list(self.citations),
            "mentioned_entities": list(self.mentioned_entities),
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "cost_basis": self.cost_basis,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "error_code": self.error_code,
            "is_valid_execution": self.is_valid_execution,
        }


def group_by_conditions(
    runs: Sequence[ObservationRun],
) -> dict[str, list[ObservationRun]]:
    """Split runs into the groups that may legitimately be pooled."""
    groups: dict[str, list[ObservationRun]] = {}
    for item in runs:
        groups.setdefault(item.conditions.fingerprint, []).append(item)
    return groups


def aggregate_rate(
    runs: Sequence[ObservationRun],
    *,
    label_ko: str,
    metric: str = "mention",
    allow_mixed_conditions: bool = False,
) -> ObservedRate:
    """Turn runs into a rate, refusing to pool measurements that are not comparable.

    Only valid executions count. A provider failure is not evidence that the brand was
    absent — treating it as such would make VEO's numbers quietly worse whenever the
    network was.
    """
    valid = [item for item in runs if item.is_valid_execution]

    # 조건보다 먼저 본다. 정기와 수동은 조건이 완전히 같아도 서로 다른 측정이고,
    # 이쪽은 `allow_mixed_conditions` 같은 예외 통로를 두지 않는다 — 예외를 두면
    # 부르는 쪽이 켤 것이고, 켜는 순간 사람이 고른 검색어가 추이에 들어간다.
    kinds = {item.kind for item in valid}
    if len(kinds) > 1:
        raise MixedRunKindsError(
            "정기 측정과 수동 측정을 하나의 비율로 합칠 수 없습니다. 수동 측정은 사람이 "
            "그 순간 고른 검색어라, 섞으면 검색어를 고르는 것만으로 비율이 움직입니다 "
            "(ADR 0015). 따로 세십시오."
        )

    groups = group_by_conditions(valid)
    if len(groups) > 1 and not allow_mixed_conditions:
        labels = sorted({item.conditions.label_ko for item in valid})
        raise MixedConditionsError(
            "측정 조건이 다른 실행을 하나의 비율로 합칠 수 없습니다. "
            "엔진·모델·검색 모드가 다르면 서로 다른 측정입니다 — " + " / ".join(labels)
        )

    if metric == "citation":
        successes = sum(1 for item in valid if item.brand_cited)
    else:
        successes = sum(1 for item in valid if item.brand_mentioned)

    rate = ObservedRate.build(successes=successes, trials=len(valid), label_ko=label_ko)

    notes: list[str] = []

    # 수동 측정만 모은 비율도 값 자체는 옳다. 다만 **추이의 점으로 쓰이면 안 된다**는
    # 사실이 비율과 같이 다녀야 한다 — 숫자만 떼어 가면 구별할 방법이 없어진다.
    if kinds == {RunKind.MANUAL}:
        notes.append(
            "사람이 그 자리에서 고른 검색어를 잰 수동 측정입니다. 이 값은 그 검색어에 "
            "대해서만 참이며, 추이에 올리거나 정기 측정과 비교할 수 없습니다."
        )

    if len(groups) > 1:
        # The caller asked for a mixed rate. It is still allowed to exist, but it is not
        # allowed to look like a single clean measurement.
        labels = sorted({item.conditions.label_ko for item in valid})
        notes.append(
            f"측정 조건이 서로 다른 실행 {len(groups)}종을 합친 값입니다 "
            f"({', '.join(labels)}). 엔진·모델별로 답이 달라 이 비율 하나로 "
            "특정 엔진에서의 노출을 말할 수 없습니다."
        )

    # 보류를 분자에서 뺐다는 사실은 비율과 **같이** 나가야 한다. 빼 놓고 말하지 않으면
    # 이 값이 확정 하한이라는 것을 읽는 사람이 알 방법이 없고, 하한을 실측값으로
    # 읽으면 우리가 고객의 노출을 실제보다 낮게 보고한 것이 된다.
    pending = sum(1 for item in valid if item.mention_pending_review)
    if pending:
        ceiling = (successes + pending) / len(valid) if valid else 0.0
        notes.append(
            f"같은 이름의 다른 업체와 갈리지 않아 판정을 보류한 실행이 {pending}건 "
            f"있습니다. 이 값은 확정된 것만 센 하한이며, 보류가 모두 이 고객으로 "
            f"확인되면 {ceiling * 100:.1f}% 까지 올라갑니다. 검수 대기 목록에서 "
            "확인할 수 있습니다."
        )

    if notes:
        return dataclasses.replace(rate, extra_qualifier_ko=" ".join(notes))

    return rate
