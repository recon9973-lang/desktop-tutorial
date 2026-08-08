"""What an AI answer engine adapter is, and the four things it must never do.

VEO asks ChatGPT, Perplexity and Claude the same questions a customer would, and reports
how often a brand appears. Every number in that report is only as honest as this layer,
so the protocol is written around the four ways it could quietly stop being honest:

* **Answering without asking.** With no credential a provider is
  :attr:`~veo.contracts.enums.ProviderState.DISABLED_NO_CREDENTIAL` and opens *no
  connection* — the check happens before the request is built. A run that never happened
  is an error-coded run, never an observation that the brand was missing.
* **Assuming the model.** ``model_version`` is read off the response. Providers roll
  models silently, and a run stored as ``gpt-5`` without the dated build cannot be
  compared with one from last month; the comparison would look fine and mean nothing.
* **Calling prose a citation.** Where the API exposes citation objects they are taken
  structurally. Where it does not, :class:`CitationSupport` says so. Running a URL regex
  over an answer and calling the hits "citations" manufactures evidence.
* **Losing the price.** Cost and latency are recorded on *every* call, success or
  failure, because VEO-LAB has to know what a comparison costs before authorising a
  500-run study. VEO never invents a price: the shipped :data:`DEFAULT_PRICE_TABLE` is
  empty, and an unpriced model yields ``cost_usd = None`` with a stated reason rather
  than a plausible-looking zero.

The retry, circuit-breaking and degradation machinery is
:mod:`veo.providers.naver.errors` — the established pattern in this codebase — reused
rather than reimplemented. :class:`AnswerProviderError` therefore subclasses
``NaverProviderError``, which is the type :class:`~veo.providers.naver.errors.ResilientCaller`
dispatches on. The base class is misnamed for this use and the customer-facing Korean
text here never mentions Naver; ``INTEGRATION_REQUEST.md`` asks for the base to be moved
to a provider-neutral module. Forking a second resilience pattern to avoid the awkward
name would have been the worse trade.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, Final, Protocol, Self, runtime_checkable

import httpx
from pydantic import SecretStr

from veo.common.http import read_capped
from veo.contracts.enums import ErrorCode, ProviderState
from veo.core.settings import ProviderCredentials, get_provider_credentials
from veo.observations.runs import RunConditions, SearchMode
from veo.providers.errors import ProviderError
from veo.providers.naver.errors import (
    UNKNOWN,
    CallOutcome,
    CircuitBreaker,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
)

__all__ = [
    "DEFAULT_MAX_RESPONSE_BYTES",
    "DEFAULT_PRICE_TABLE",
    "DEFAULT_TIMEOUT_SECONDS",
    "AnswerCredentialInvalidError",
    "AnswerCredentialMissingError",
    "AnswerForbiddenError",
    "AnswerProvider",
    "AnswerProviderError",
    "AnswerRateLimitedError",
    "AnswerResponseTooLargeError",
    "AnswerSchemaError",
    "AnswerServerError",
    "AnswerTimeoutError",
    "AnswerTransportError",
    "AnswerUnauthorizedError",
    "CitationSupport",
    "CostBasis",
    "HttpAnswerProvider",
    "MeteredOutcome",
    "ModelPrice",
    "PriceTable",
    "ProviderAnswer",
    "classify_answer_status",
    "classify_answer_transport_exception",
    "credential_state",
]

DEFAULT_TIMEOUT_SECONDS: Final = 60.0
DEFAULT_MAX_RESPONSE_BYTES: Final = 4 * 1024 * 1024

#: Strings that fill a credential slot without being a credential.
#:
#: ``core/settings.py`` owns the authoritative table and applies it to every credential
#: field, but its classifier is private and that file is not this module's to edit. This
#: copy exists only for the direct-construction path — a provider handed a ``SecretStr``
#: rather than built from settings — so that a placeholder is caught on both routes.
#: ``INTEGRATION_REQUEST.md`` item 2 asks for a public helper so this copy can go.
_PLACEHOLDER_VALUES: Final = frozenset(
    {
        "[sensitive]",
        "sensitive",
        "[redacted]",
        "redacted",
        "***",
        "****",
        "xxxx",
        "xxxxxxxx",
        "changeme",
        "change-me",
        "your-api-key-here",
        "your_api_key_here",
        "<your key>",
        "<your-key>",
        "todo",
        "tbd",
        "-",
        "null",
        "none",
        "undefined",
        "placeholder",
    }
)


# --------------------------------------------------------------------------- #
# Typed failures
# --------------------------------------------------------------------------- #


class AnswerProviderError(ProviderError):
    """A call to an AI answer engine that did not produce a usable answer.

    Subclasses ``NaverProviderError`` only because that is the exception type
    :class:`~veo.providers.naver.errors.ResilientCaller` catches. Nothing about the
    customer-facing text is inherited: every ``message_ko`` below is written for AI
    engines and none of them names Naver.
    """

    message_ko: ClassVar[str] = "AI 엔진 응답을 받지 못해 이 실행은 '측정 불가'입니다."


class AnswerCredentialMissingError(AnswerProviderError):
    """No credential is configured. A state, reported as one — not a failed call."""

    provider_state: ClassVar[ProviderState] = ProviderState.DISABLED_NO_CREDENTIAL
    message_ko: ClassVar[str] = (
        "이 AI 엔진의 자격증명이 없어 제공자가 비활성 상태입니다. 호출을 시도하지 않았으므로 "
        "이 실행은 '측정 불가'이며, 브랜드가 언급되지 않았다는 뜻이 아닙니다."
    )


class AnswerCredentialInvalidError(AnswerProviderError):
    """The slot is filled with a placeholder, which can only ever produce 401s."""

    provider_state: ClassVar[ProviderState] = ProviderState.DISABLED_INVALID_CREDENTIAL
    message_ko: ClassVar[str] = (
        "이 AI 엔진의 자격증명 자리에 실제 키가 아닌 자리표시자가 들어 있습니다. "
        "호출을 시도하지 않았으며 이 실행은 '측정 불가'입니다."
    )


class AnswerUnauthorizedError(AnswerProviderError):
    message_ko: ClassVar[str] = (
        "AI 엔진이 자격증명을 거부했습니다(401). 저장된 키를 확인해 주세요. "
        "이 실행은 '측정 불가'입니다."
    )


class AnswerForbiddenError(AnswerProviderError):
    message_ko: ClassVar[str] = (
        "AI 엔진에서 권한이 거부되었습니다(403). 계정 권한을 확인해 주세요. "
        "이 실행은 '측정 불가'입니다."
    )


class AnswerRateLimitedError(AnswerProviderError):
    """429 — the one failure the provider tells us how to fix."""

    error_code: ClassVar[ErrorCode] = ErrorCode.PROVIDER_RATE_LIMITED
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "AI 엔진 호출 한도를 초과했습니다(429). 잠시 후 다시 시도합니다. "
        "지금은 '측정 불가'입니다."
    )


class AnswerServerError(AnswerProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "AI 엔진 서버가 응답하지 못했습니다. 이 실행은 '측정 불가'입니다."
    )


class AnswerTimeoutError(AnswerProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "AI 엔진 응답이 제한 시간을 초과했습니다. 이 실행은 '측정 불가'이며, "
        "브랜드가 언급되지 않았다는 뜻이 아닙니다."
    )


class AnswerTransportError(AnswerProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "AI 엔진에 연결하지 못했습니다. 이 실행은 '측정 불가'입니다."
    )


class AnswerSchemaError(AnswerProviderError):
    """The answer arrived in a shape VEO does not know how to read.

    Never partially salvaged. Guessing which field replaced which is how a run ends up
    recording an answer the engine did not give.
    """

    message_ko: ClassVar[str] = (
        "AI 엔진 응답 형식이 VEO가 아는 형식과 다릅니다. 잘못 해석한 결과를 기록하지 않기 위해 "
        "이 실행은 '측정 불가'입니다."
    )


class AnswerResponseTooLargeError(AnswerProviderError):
    message_ko: ClassVar[str] = (
        "AI 엔진 응답이 허용 한도를 초과했습니다. 이 실행은 '측정 불가'입니다."
    )


def classify_answer_status(
    status_code: int, *, retry_after: str | None = None
) -> AnswerProviderError:
    """Turn an HTTP status into exactly one typed error."""
    if status_code == 401:
        return AnswerUnauthorizedError(f"status={status_code}")
    if status_code == 403:
        return AnswerForbiddenError(f"status={status_code}")
    if status_code == 429:
        return AnswerRateLimitedError(
            f"status={status_code}", retry_after_seconds=_parse_retry_after(retry_after)
        )
    if 500 <= status_code <= 599:
        return AnswerServerError(f"status={status_code}")
    return AnswerSchemaError(f"unexpected status={status_code}")


def classify_answer_transport_exception(exc: Exception) -> AnswerProviderError:
    """Turn a transport exception into a typed error without importing its text."""
    if "Timeout" in type(exc).__name__:
        return AnswerTimeoutError(type(exc).__name__)
    return AnswerTransportError(type(exc).__name__)


def _parse_retry_after(value: str | None) -> int | None:
    """Seconds from a ``Retry-After`` header, or ``None``.

    Only the delta-seconds form is honoured. Defaulting to *some* number when the header
    is unparseable would invent a delay the provider never asked for.
    """
    if value is None:
        return None
    try:
        seconds = int(value.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


# --------------------------------------------------------------------------- #
# Credentials
# --------------------------------------------------------------------------- #


def credential_state(credential: SecretStr | None) -> ProviderState:
    """``ENABLED``, ``DISABLED_NO_CREDENTIAL`` or ``DISABLED_INVALID_CREDENTIAL``.

    A filled-in placeholder is a different problem from an empty slot — one needs a key,
    the other needs the fake one removed — so the two states stay apart.
    """
    if credential is None:
        return ProviderState.DISABLED_NO_CREDENTIAL
    raw = credential.get_secret_value().strip()
    if not raw:
        return ProviderState.DISABLED_NO_CREDENTIAL
    if raw.lower() in _PLACEHOLDER_VALUES:
        return ProviderState.DISABLED_INVALID_CREDENTIAL
    return ProviderState.ENABLED


# --------------------------------------------------------------------------- #
# Cost
# --------------------------------------------------------------------------- #


class CostBasis(StrEnum):
    """Where a cost figure came from, or why there is none.

    ``None`` cost with a basis is the honest shape. A zero would read as "this call was
    free", which is a claim VEO is in no position to make.
    """

    #: Tokens reported by the provider, priced with a table VEO was given.
    CALCULATED_FROM_USAGE = "CALCULATED_FROM_USAGE"
    #: Tokens were reported but nobody has told VEO what this model costs.
    NO_PRICE_CONFIGURED = "NO_PRICE_CONFIGURED"
    #: The provider reported no token usage — typically because the call failed.
    NO_USAGE_REPORTED = "NO_USAGE_REPORTED"
    #: A price table exists but is past its expiry. Its numbers are no longer evidence
    #: of anything, so no figure is produced — see :mod:`veo.observations.pricing`.
    PRICE_TABLE_STALE = "PRICE_TABLE_STALE"
    #: 이 모델은 검색에 호출당 요금을 따로 받는데, 이 호출에서 검색이 몇 번 돌았는지를
    #: 어댑터가 알려주지 않았다. 토큰만으로 더하면 **청구서보다 싸게 나온다.**
    SEARCH_USAGE_UNKNOWN = "SEARCH_USAGE_UNKNOWN"
    #: 이 모델은 검색으로 딸려온 토큰을 공짜로 처리하는데, 제공자가 주는 `input_tokens`
    #: 는 프롬프트와 검색 결과를 **합쳐서** 준다. 둘을 가를 수 없으므로 정확한 금액을
    #: 만들 수 없다. 전부 과금으로 치면 과대, 전부 공짜로 치면 과소다.
    SEARCH_CONTENT_NOT_SEPARABLE = "SEARCH_CONTENT_NOT_SEPARABLE"


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """한 모델의 단가.

    토큰 단가만으로는 청구서가 맞지 않는다. 실측 2026-08-08 기준으로 주요 제공자
    다섯 곳 중 넷이 **웹 검색에 호출당 요금을 따로** 받는다:

        OpenAI      추론 $10 / 1k호출 · 비추론 $25 / 1k호출
        Anthropic   $10 / 1k
        Gemini      $14 / 1k (월 5,000회 무료)
        Perplexity  $5~14 / 1k (모델·컨텍스트별)
        xAI         공식 문서에 없음

    토큰만 세면 검색을 돌린 호출마다 그만큼 적게 잡히고, 예산 상한이 실제보다 늦게
    걸린다. 예산은 늦게 걸리면 없는 것과 같다.
    """

    input_usd_per_million: float
    output_usd_per_million: float
    #: 웹 검색 1,000회당 요금. 검색을 안 쓰는 모델은 0.
    search_usd_per_1k_calls: float = 0.0
    #: 검색으로 딸려온 토큰을 제공자가 공짜로 처리하는가.
    #:
    #: 참이면 이 모델의 **검색 호출은 금액을 낼 수 없다.** 제공자가 주는 입력 토큰
    #: 수에 프롬프트와 검색 결과가 섞여 있고 가를 방법이 없기 때문이다. 지어낸 값을
    #: 내는 대신 :attr:`CostBasis.SEARCH_CONTENT_NOT_SEPARABLE` 로 남긴다.
    search_content_tokens_free: bool = False

    def __post_init__(self) -> None:
        if self.input_usd_per_million < 0 or self.output_usd_per_million < 0:
            raise ValueError("a price must not be negative")
        if self.search_usd_per_1k_calls < 0:
            raise ValueError("a search fee must not be negative")


@runtime_checkable
class SupportsPricing(Protocol):
    """한 번의 호출에 든 비용, 또는 그 값이 없는 이유.

    어댑터가 가격표에 요구하는 것은 이 하나뿐이다. 구상 클래스로 묶어 두면 날짜가 붙은
    가격표(:mod:`veo.observations.pricing`)를 그대로 넘길 수 없고, 실제로 그것 때문에
    가격표가 연결되지 않은 채 모든 호출이 '가격 미설정' 으로 기록되고 있었다.
    """

    def cost(
        self,
        *,
        model: str,
        model_version: str,
        input_tokens: int | None,
        output_tokens: int | None,
        search_calls: int | None = None,
    ) -> tuple[float | None, CostBasis]: ...


@dataclass(frozen=True, slots=True)
class PriceTable:
    """Model prices, keyed by dated version first and model family second.

    Deliberately empty by default. A hard-coded price list goes stale the week after it
    is written, and a stale price presented as a cost is exactly the kind of plausible
    fabrication this product must not produce. VEO-LAB supplies the table it wants a
    study costed with.
    """

    prices: Mapping[str, ModelPrice] = field(default_factory=dict)

    def cost(
        self,
        *,
        model: str,
        model_version: str,
        input_tokens: int | None,
        output_tokens: int | None,
        search_calls: int | None = None,
    ) -> tuple[float | None, CostBasis]:
        if input_tokens is None and output_tokens is None:
            return None, CostBasis.NO_USAGE_REPORTED
        price = self.prices.get(model_version) or self.prices.get(model)
        if price is None:
            return None, CostBasis.NO_PRICE_CONFIGURED
        return priced_call(price, input_tokens, output_tokens, search_calls)


def priced_call(
    price: ModelPrice,
    input_tokens: int | None,
    output_tokens: int | None,
    search_calls: int | None,
) -> tuple[float | None, CostBasis]:
    """토큰 단가와 검색 요금을 합친 한 호출의 금액, 또는 못 내는 이유.

    **두 가격표가 이 함수를 함께 쓴다** — :class:`PriceTable` 과 날짜가 붙은
    :class:`~veo.observations.pricing.DatedPriceTable`. 산식이 두 벌이 되면 언젠가
    한쪽만 고쳐지고, 화면과 예산이 서로 다른 금액을 말하게 된다(0-D).

    금액을 안 내는 두 경우가 있고, 둘 다 **0원이 아니라 '모른다'** 다:

    * 검색 요금을 받는 모델인데 검색 횟수를 모를 때 — 더하면 청구서보다 싸다.
    * 검색 토큰이 공짜인 모델의 검색 호출 — 제공자가 프롬프트와 검색 결과를 합친
      입력 토큰 하나로 주므로, 어느 쪽이 얼마인지 가를 수 없다.
    """
    charges_for_search = price.search_usd_per_1k_calls > 0 or price.search_content_tokens_free
    if charges_for_search and search_calls is None:
        return None, CostBasis.SEARCH_USAGE_UNKNOWN
    if price.search_content_tokens_free and (search_calls or 0) > 0:
        return None, CostBasis.SEARCH_CONTENT_NOT_SEPARABLE

    total = (input_tokens or 0) / 1_000_000 * price.input_usd_per_million
    total += (output_tokens or 0) / 1_000_000 * price.output_usd_per_million
    total += (search_calls or 0) / 1_000 * price.search_usd_per_1k_calls
    return total, CostBasis.CALCULATED_FROM_USAGE


#: The shipped table. Empty on purpose — see :class:`PriceTable`.
DEFAULT_PRICE_TABLE: Final = PriceTable()


# --------------------------------------------------------------------------- #
# The answer
# --------------------------------------------------------------------------- #


class CitationSupport(StrEnum):
    """Whether this call could evidence a citation at all."""

    #: The API returned citation objects and they were read structurally.
    STRUCTURED = "STRUCTURED"
    #: The API exposes no citation objects for this call. Not "zero citations" — the
    #: question of which sources were used simply cannot be answered from this response.
    NOT_EXPOSED_BY_PROVIDER = "NOT_EXPOSED_BY_PROVIDER"


@dataclass(frozen=True, slots=True)
class ProviderAnswer:
    """One answer, exactly as the engine gave it.

    ``text`` is the raw answer and does **not** belong in an
    :class:`~veo.observations.runs.ObservationRun`. It goes to
    :mod:`veo.observations.providers.storage`, and the run keeps the pointer and hash.
    """

    text: str
    model: str
    model_version: str
    citations: tuple[str, ...]
    citation_support: CitationSupport
    input_tokens: int | None
    output_tokens: int | None
    #: 이 호출에서 웹 검색이 **몇 번** 돌았는가. ``None`` 은 "이 어댑터가 아직 세지
    #: 않는다" 이지 0이 아니다.
    #:
    #: 검색에 호출당 요금을 받는 모델(대부분이 그렇다)은 이 값이 없으면 금액을 낼 수
    #: 없다 — 토큰만 더하면 청구서보다 싸게 나온다. 0으로 두면 그 사실이 조용히
    #: 사라지므로 기본값은 ``None`` 이다.
    search_calls: int | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("빈 문자열은 답변이 아닙니다")
        if self.search_calls is not None and self.search_calls < 0:
            raise ValueError("검색 횟수는 음수일 수 없습니다")
        if not self.model_version.strip():
            raise ValueError("모델 버전은 응답에서 읽어야 하며 비워둘 수 없습니다")
        if self.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER and self.citations:
            raise ValueError(
                "제공자가 인용을 노출하지 않았다고 해놓고 인용을 담을 수 없습니다"
            )


@dataclass(frozen=True, slots=True)
class MeteredOutcome[T](CallOutcome[T]):
    """A :class:`~veo.providers.naver.errors.CallOutcome` that always carries the meter.

    Every field below is populated on failure too. A failed call still consumed wall time
    and may still have been billed; recording nothing would let a 500-run study be
    authorised on the cost of the runs that happened to succeed.
    """

    latency_ms: int = 0
    cost_usd: float | None = None
    cost_basis: CostBasis = CostBasis.NO_USAGE_REPORTED
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class AnswerProvider(Protocol):
    """One AI answer engine, as VEO uses it."""

    @property
    def engine(self) -> str:
        """The engine name used in :class:`~veo.observations.runs.RunConditions`."""

    @property
    def state(self) -> ProviderState:
        """Whether this engine can answer right now, and if not, why not."""

    def ask(
        self, prompt_text: str, *, conditions: RunConditions
    ) -> MeteredOutcome[ProviderAnswer]:
        """Ask one question. Never raises for a provider problem.

        The outcome carries either a :class:`ProviderAnswer` or ``UNKNOWN`` with a stated
        reason, and in both cases the cost and latency of the attempt.
        """


# --------------------------------------------------------------------------- #
# The shared HTTP adapter
# --------------------------------------------------------------------------- #


class HttpAnswerProvider:
    """Request, retry, meter, degrade — everything the three adapters share.

    Subclasses supply the wire format only: :meth:`_build_request` and :meth:`_parse`.
    """

    engine: ClassVar[str] = ""
    base_url: ClassVar[str] = ""

    #: The ``ProviderCredentials`` attribute holding this engine's key. Every adapter
    #: names one, so :meth:`from_settings` is the single construction path and a new
    #: engine cannot quietly arrive without a credential slot.
    settings_field: ClassVar[str] = ""

    #: 이 엔진에 **검색을 끄고** 물어볼 수 있는가.
    #:
    #: 끌 수 없는 엔진에 끔을 요청하면 엔진은 평소대로 검색해 답하고, VEO 는 그 답을
    #: "검색 끔" 으로 기록한다. 그러면 "검색 없이도 우리가 나온다" 라는, 재지 않은 문장이
    #: 만들어진다 — 거래처에 그대로 보이는 자리다. 어댑터마다 스스로 밝히게 해서, 화면이
    #: 고를 수 있는 것과 엔진이 할 수 있는 것을 같은 곳에서 읽게 한다.
    supports_search_off: ClassVar[bool] = True

    @classmethod
    def from_settings(
        cls, credentials: ProviderCredentials | None = None, **kwargs: Any
    ) -> Self:
        """Build from ``ProviderCredentials``, which owns every provider key.

        An absent key is a state, not an error: the provider is constructed, reports
        ``DISABLED_NO_CREDENTIAL`` and opens no connection.
        """
        if not cls.settings_field:
            raise NotImplementedError(f"{cls.__name__} does not name a settings field")
        resolved = credentials if credentials is not None else get_provider_credentials()
        credential: SecretStr | None = getattr(resolved, cls.settings_field)
        return cls(credential=credential, **kwargs)

    def __init__(
        self,
        *,
        credential: SecretStr | None,
        transport: httpx.BaseTransport | None = None,
        base_url: str | None = None,
        price_table: SupportsPricing | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        policy: RetryPolicy | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._credential = credential
        self._credential_state = credential_state(credential)
        self._transport = transport
        self._base_url = (base_url or self.base_url).rstrip("/")
        self._prices = price_table if price_table is not None else DEFAULT_PRICE_TABLE
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._monotonic = monotonic
        self._now = now
        self._caller = ResilientCaller(
            policy=policy or RetryPolicy(),
            breaker=breaker or CircuitBreaker(),
            sleep=sleep,
            now=now,
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} engine={self.engine} state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credential_state is not ProviderState.ENABLED:
            return self._credential_state
        return self._caller.breaker.provider_state()

    # ----------------------------------------------------------------- ask

    def ask(
        self, prompt_text: str, *, conditions: RunConditions
    ) -> MeteredOutcome[ProviderAnswer]:
        if not prompt_text.strip():
            raise ValueError("빈 질문은 보낼 수 없습니다")
        if conditions.search_mode is SearchMode.UNKNOWN:
            # Recording an answer under "검색 여부 불명" when VEO itself chose the mode
            # would put an unresolvable condition into a comparison. This is a caller
            # bug, not a provider failure, so it raises rather than degrading.
            raise ValueError(
                "검색 사용 여부를 UNKNOWN 으로 두고 호출할 수 없습니다. "
                "BROWSING 또는 NO_BROWSING 중 하나를 지정하세요"
            )
        if conditions.search_mode is SearchMode.NO_BROWSING and not self.supports_search_off:
            # 끌 수 없는 엔진은 평소대로 검색해 답한다. 그 답을 "검색 끔" 으로 저장하면
            # 재지 않은 조건의 숫자가 생긴다. 같은 이유로 UNKNOWN 과 나란히 거절한다.
            raise ValueError(
                f"{self.engine} 은 검색을 끌 수 없는 엔진입니다. 끔으로 요청한 답변을 "
                "'검색 끔' 으로 기록하면 재지 않은 조건의 숫자가 됩니다"
            )

        started = self._monotonic()

        credential = self._credential
        if credential is None or self._credential_state is not ProviderState.ENABLED:
            # Before the request is built. A misconfigured deployment must not produce a
            # stream of 401s against a provider, and must not look like a measurement.
            return self._disabled(started)

        def operation() -> ProviderAnswer:
            body = self._request(credential, prompt_text, conditions)
            return self._parse(_decode_json(body), conditions=conditions)

        outcome = self._caller.call(operation)
        latency_ms = self._elapsed_ms(started)

        answer = outcome.value
        if not isinstance(answer, ProviderAnswer):
            return MeteredOutcome(
                value=UNKNOWN,
                failure=outcome.failure,
                attempts=outcome.attempts,
                latency_ms=latency_ms,
                cost_usd=None,
                cost_basis=CostBasis.NO_USAGE_REPORTED,
            )

        cost, basis = self._prices.cost(
            model=answer.model,
            model_version=answer.model_version,
            input_tokens=answer.input_tokens,
            output_tokens=answer.output_tokens,
            search_calls=answer.search_calls,
        )
        return MeteredOutcome(
            value=answer,
            failure=None,
            attempts=outcome.attempts,
            latency_ms=latency_ms,
            cost_usd=cost,
            cost_basis=basis,
            input_tokens=answer.input_tokens,
            output_tokens=answer.output_tokens,
        )

    # ----------------------------------------------------------- subclasses

    def _build_request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> tuple[str, Mapping[str, str], Mapping[str, Any]]:
        """``(url, headers, json_body)`` for one question."""
        raise NotImplementedError

    def _parse(
        self, payload: Mapping[str, Any], *, conditions: RunConditions
    ) -> ProviderAnswer:
        """Map a response body into a :class:`ProviderAnswer`, or raise a schema error."""
        raise NotImplementedError

    # ------------------------------------------------------------ internals

    def _disabled(self, started: float) -> MeteredOutcome[ProviderAnswer]:
        error: AnswerProviderError = (
            AnswerCredentialInvalidError(f"{self.engine}: placeholder credential")
            if self._credential_state is ProviderState.DISABLED_INVALID_CREDENTIAL
            else AnswerCredentialMissingError(f"{self.engine}: no credential")
        )
        return MeteredOutcome(
            value=UNKNOWN,
            failure=ProviderFailure.from_error(error, occurred_at=self._now()),
            attempts=0,
            latency_ms=self._elapsed_ms(started),
            cost_usd=None,
            cost_basis=CostBasis.NO_USAGE_REPORTED,
        )

    def _elapsed_ms(self, started: float) -> int:
        """Wall time VEO spent on this question, retries and backoff included."""
        return max(0, round((self._monotonic() - started) * 1000))

    def _request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> bytes:
        url, headers, body = self._build_request(credential, prompt_text, conditions)
        with httpx.Client(
            transport=self._transport,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=False,
            cookies=None,
        ) as client:
            request = client.build_request("POST", url, headers=dict(headers), json=dict(body))
            try:
                response = client.send(request, stream=True)
            except httpx.HTTPError as exc:
                raise classify_answer_transport_exception(exc) from None
            try:
                if response.status_code != 200:
                    raise classify_answer_status(
                        response.status_code, retry_after=response.headers.get("retry-after")
                    )
                return read_capped(response, self._max_response_bytes, AnswerResponseTooLargeError)
            except httpx.HTTPError as exc:
                raise classify_answer_transport_exception(exc) from None
            finally:
                response.close()



def _decode_json(body: bytes) -> Mapping[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AnswerSchemaError(f"body is not JSON: {type(exc).__name__}") from None
    if not isinstance(payload, dict):
        raise AnswerSchemaError("body is not a JSON object")
    return payload


def require_model_version(payload: Mapping[str, Any], *keys: str) -> str:
    """The dated model build, read off the response.

    Missing is a schema error, not a fallback to the requested model name. Providers roll
    builds silently; a run that records the family alone cannot be compared with an
    earlier one, and would look perfectly comparable while not being so.

    ``keys`` names the response fields to try, in order — providers disagree about
    whether it is ``model`` or ``modelVersion``.
    """
    for key in keys or ("model",):
        version = payload.get(key)
        if isinstance(version, str) and version.strip():
            return version.strip()
    raise AnswerSchemaError("response does not report the model it answered with")


def read_token_count(usage: Any, *keys: str) -> int | None:
    """One token count from a usage block, or ``None`` when it was not reported."""
    if not isinstance(usage, dict):
        return None
    for key in keys:
        raw = usage.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            return raw
    return None


def collect_urls(values: Sequence[Any]) -> tuple[str, ...]:
    """URLs exactly as the provider gave them, with non-strings dropped."""
    return tuple(value.strip() for value in values if isinstance(value, str) and value.strip())
