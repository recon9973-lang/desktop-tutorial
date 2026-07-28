"""Exception → (ErrorCode, safe message, internal_error_ref).

The rule this module enforces: **a user-facing message is never derived from an
exception**. Provider clients routinely stuff the failing request into the exception
text — Authorization headers, cookies, API keys, request bodies. So the safe message is
looked up from a static table keyed by :class:`~veo.contracts.ErrorCode` and nothing
else. The detail stays server-side, reachable only through ``internal_error_ref``.

:func:`redact` exists for the server-side log line, because "we only log it internally"
is not a reason to write a credential to disk.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from veo.contracts import RETRYABLE_ERROR_CODES, ApiError, ErrorCode

__all__ = [
    "SAFE_MESSAGES_KO",
    "ProviderRateLimited",
    "ProviderUnavailable",
    "SafeError",
    "TargetUrlRejected",
    "VeoWorkerError",
    "redact",
    "redacted_detail",
    "to_api_error",
    "to_safe_error",
]


# --------------------------------------------------------------------------------------
# Worker-level typed exceptions
# --------------------------------------------------------------------------------------


class VeoWorkerError(Exception):
    """Base for exceptions that already know their contract error code."""

    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    #: ``None`` means "use the shared contract's default for this code".
    retryable_override: bool | None = None


class ProviderUnavailable(VeoWorkerError):
    error_code = ErrorCode.PROVIDER_UNAVAILABLE


class ProviderRateLimited(VeoWorkerError):
    error_code = ErrorCode.PROVIDER_RATE_LIMITED


class TargetUrlRejected(VeoWorkerError):
    error_code = ErrorCode.TARGET_URL_REJECTED


class QuotaExceeded(VeoWorkerError):
    error_code = ErrorCode.QUOTA_EXCEEDED


# --------------------------------------------------------------------------------------
# Safe messages — the only source of user-facing error text
# --------------------------------------------------------------------------------------

SAFE_MESSAGES_KO: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_FAILED: "입력값이 올바르지 않습니다. 요청 내용을 확인해 주세요.",
    ErrorCode.UNAUTHENTICATED: "인증이 필요합니다. 다시 로그인해 주세요.",
    ErrorCode.PERMISSION_DENIED: "이 작업을 수행할 권한이 없습니다.",
    ErrorCode.NOT_FOUND: "요청한 대상을 찾을 수 없습니다.",
    ErrorCode.CONFLICT: "동일한 요청이 이미 처리 중이거나 다른 내용으로 등록되어 있습니다.",
    ErrorCode.RATE_LIMITED: "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.",
    ErrorCode.QUOTA_EXCEEDED: "이번 기간의 사용 한도를 모두 사용했습니다.",
    ErrorCode.TARGET_URL_REJECTED: "분석할 수 없는 주소입니다. 공개된 웹 주소인지 확인해 주세요.",
    ErrorCode.PROVIDER_UNAVAILABLE: (
        "외부 데이터 제공처에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
    ),
    ErrorCode.PROVIDER_RATE_LIMITED: (
        "외부 데이터 제공처의 호출 한도에 걸렸습니다. 잠시 후 다시 시도해 주세요."
    ),
    ErrorCode.JOB_CANCELLED: "요청하신 작업이 취소되었습니다.",
    ErrorCode.JOB_EXPIRED: "작업 유효 기간이 지나 결과를 사용할 수 없습니다.",
    ErrorCode.SCORING_SPEC_INVALID: (
        "점수 산정 기준을 불러오지 못했습니다. 관리자에게 문의해 주세요."
    ),
    ErrorCode.INTERNAL_ERROR: (
        "처리 중 오류가 발생했습니다. 문제가 계속되면 지원팀에 문의해 주세요."
    ),
}

# A missing message would silently fall back to something unreviewed, so fail at import.
_MISSING = sorted(c.value for c in set(ErrorCode) - set(SAFE_MESSAGES_KO))
if _MISSING:  # pragma: no cover - guards a developer mistake at import time
    raise RuntimeError(f"SAFE_MESSAGES_KO is missing entries for: {_MISSING}")


# --------------------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------------------

_REDACTED = "[REDACTED]"

_SENSITIVE_KEY = (
    r"pass(?:word|wd|phrase)?|pwd|secret|token|api[_-]?key|apikey|"
    r"client[_-]?secret|access[_-]?token|refresh[_-]?token|"
    r"authorization|auth[_-]?token|session[_-]?id|sessionid|credential|"
    r"private[_-]?key|signature|x-api-key"
)

_REDACTION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    # Authorization scheme + credential, e.g. "Bearer eyJhbGciOi..."
    (re.compile(r"(?i)\b(bearer|basic|token)\s+[A-Za-z0-9._\-+/=]{6,}"), rf"\1 {_REDACTED}"),
    # Whole cookie values, which are credentials in their own right.
    (
        re.compile(r"""(?i)\b(set-)?cookie["']?\s*[:=]\s*["']?[^\n"']*"""),
        f"Cookie: {_REDACTED}",
    ),
    # key=value / "key": "value" for anything credential-shaped.
    (
        re.compile(rf"""(?i)\b({_SENSITIVE_KEY})\b["']?\s*[:=]\s*["']?([^"'\s,;&}}\)\]]+)"""),
        rf"\1={_REDACTED}",
    ),
    # Long opaque blobs that look like keys even without a label.
    (re.compile(r"\b(?:sk|pk|rk)[-_](?:live|test|prod)[-_][A-Za-z0-9]{6,}\b"), _REDACTED),
)


def redact(text: str) -> str:
    """Strip credential material from text destined for a log.

    Deliberately conservative about *what it keeps*: it aims to leave the URL, status
    code and exception type intact so the line still helps an on-call engineer.
    """
    for pattern, replacement in _REDACTION_RULES:
        text = pattern.sub(replacement, text)
    return text


def redacted_detail(exc: BaseException) -> str:
    """A one-line, redacted description of ``exc``, safe to write to the server log."""
    return redact(f"{type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------------------
# Mapping
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SafeError:
    """What the caller is allowed to see, plus the handle to what they are not."""

    code: ErrorCode
    message: str
    internal_error_ref: str
    retryable: bool


def _classify(exc: BaseException) -> tuple[ErrorCode, bool | None]:
    """Return ``(code, retryable_override)`` for ``exc``."""
    # Imported here to keep the module import graph acyclic.
    from veo_worker.runtime.cancellation import JobCancelledError
    from veo_worker.runtime.idempotency import IdempotencyConflictError
    from veo_worker.runtime.state import IllegalTransitionError

    if isinstance(exc, VeoWorkerError):
        return exc.error_code, exc.retryable_override
    if isinstance(exc, JobCancelledError):
        return ErrorCode.JOB_CANCELLED, False
    if isinstance(exc, IdempotencyConflictError):
        return ErrorCode.CONFLICT, False
    if isinstance(exc, IllegalTransitionError):
        # A bug in our own transition logic. Retrying will reproduce it.
        return ErrorCode.INTERNAL_ERROR, False
    if isinstance(exc, NotImplementedError):
        # No amount of retrying will make missing code appear.
        return ErrorCode.INTERNAL_ERROR, False
    if isinstance(exc, TimeoutError):
        return ErrorCode.PROVIDER_UNAVAILABLE, None
    if isinstance(exc, (ConnectionError, OSError)):
        return ErrorCode.PROVIDER_UNAVAILABLE, None
    # Note: OSError above already covers PermissionError. An OS-level permission problem
    # is an infrastructure fault, not the caller's PERMISSION_DENIED, and must not be
    # reported to them as one.
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return ErrorCode.VALIDATION_FAILED, False
    return ErrorCode.INTERNAL_ERROR, None


def new_internal_error_ref() -> str:
    """A correlation handle. Random, so it can never echo anything from the input."""
    return f"veo-err-{uuid.uuid4().hex}"


def to_safe_error(
    exc: BaseException,
    *,
    code: ErrorCode | None = None,
    internal_error_ref: str | None = None,
) -> SafeError:
    """Map ``exc`` to a customer-safe error.

    ``exc``'s own text is never used. If the mapping is wrong for a new exception type,
    the fix is to extend :func:`_classify`, not to pass the raw message through.
    """
    if code is None:
        resolved_code, override = _classify(exc)
    else:
        resolved_code, override = code, None

    retryable = (resolved_code in RETRYABLE_ERROR_CODES) if override is None else override
    return SafeError(
        code=resolved_code,
        message=SAFE_MESSAGES_KO[resolved_code],
        internal_error_ref=internal_error_ref or new_internal_error_ref(),
        retryable=retryable,
    )


def to_api_error(
    exc: BaseException,
    *,
    code: ErrorCode | None = None,
    internal_error_ref: str | None = None,
    retry_after_seconds: int | None = None,
) -> ApiError:
    """Build the shared :class:`~veo.contracts.ApiError` envelope from ``exc``."""
    safe = to_safe_error(exc, code=code, internal_error_ref=internal_error_ref)
    return ApiError(
        code=safe.code,
        message=safe.message,
        retryable=safe.retryable,
        retry_after_seconds=retry_after_seconds,
        internal_error_ref=safe.internal_error_ref,
    )
