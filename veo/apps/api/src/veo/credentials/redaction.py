"""Scrub secrets out of anything heading for a log line or an error message.

Provider APIs routinely echo the credential back inside their error bodies, and a stack
trace happily prints whatever local variable it was holding. Neither is allowed to reach
a log file or a response, so every error path in this package runs its text through
:func:`redact` first.

Two layers, because either alone is insufficient:

* **Known values.** The caller passes the exact secrets it is holding. This catches an
  ordinary-looking credential — ``naver-customer-1234`` — that no pattern would flag.
  There is deliberately no global registry of live secrets to consult: a module-level
  cache of every credential in the system is precisely the thing this package exists to
  avoid.
* **Shapes.** Bearer tokens, JWTs, ``key=`` query parameters, URL userinfo and long
  high-entropy runs are removed on sight, which covers secrets nobody thought to pass in.

The result is for humans reading logs. It is not a sanitiser for untrusted output and it
is never applied to a response body — responses carry only state fields that cannot hold
a secret in the first place.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = ["REDACTED", "redact", "redact_exception", "redact_mapping"]

REDACTED = "[REDACTED]"

#: Longer text is truncated before scanning, so a hostile provider cannot turn a log
#: line into a regex denial of service.
MAX_LENGTH = 4_096
_TRUNCATION_NOTE = "…[truncated]"

#: Field labels that introduce a secret. This is a pattern that *finds* such labels;
#: naming it after what it matches would trip the hardcoded-password lint for nothing.
_SENSITIVE_LABEL = (
    r"(?:api[_-]?key|apikey|access[_-]?key|secret[_-]?key|client[_-]?secret|secret|"
    r"token|refresh[_-]?token|access[_-]?token|password|passwd|pwd|authorization|"
    r"auth|credential|private[_-]?key|signature|customer[_-]?id)"
)

_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Authorization: Bearer <token> / Basic <token>
    re.compile(r"(?i)(\b(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]{8,}"),
    # JSON Web Tokens, wherever they appear.
    re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"),
    # header: value, key = value, "key": "value", key='value'
    #
    # Both quote characters are accepted, and single quotes are the case that matters
    # most: Python's ``repr()`` writes strings with them, so a traceback, an ``!r``
    # format field or a dumped config dict all produce ``password='...'``. A pattern
    # that only knew about double quotes scrubbed the JSON and left the traceback —
    # and the traceback is where a credential is likeliest to meet a log.
    re.compile(
        rf"(?i)(['\"]?\b(?:x-)?{_SENSITIVE_LABEL}['\"]?\s*[:=]\s*['\"]?)[^\s\"',;&}}]{{4,}}"
    ),
    # ?token=... & api_key=...
    re.compile(rf"(?i)([?&]{_SENSITIVE_LABEL}=)[^&\s]{{4,}}"),
    # scheme://user:password@host
    re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^/\s:@]+:)[^/\s@]+(@)"),
    # Recognisable vendor key shapes.
    re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{12,}\b"),
    # Anything long enough to be key material: hex, base64, base64url.
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),
    re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}\b"),
)

#: Mapping keys whose value is replaced outright, whatever it looks like.
_SENSITIVE_KEY = re.compile(rf"(?i)\A(?:x-)?{_SENSITIVE_LABEL}\Z")


def redact(value: str | None, *, known_values: Iterable[str | None] = ()) -> str:
    """Return ``value`` with known secrets and secret-shaped runs replaced."""
    if not value:
        return ""

    text = value
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH] + _TRUNCATION_NOTE

    # Longest first, so a secret that contains another secret is removed whole rather
    # than being cut in half and leaving a readable remainder.
    for known in sorted(
        {candidate for candidate in known_values if candidate and candidate.strip()},
        key=len,
        reverse=True,
    ):
        text = text.replace(known, REDACTED)

    for pattern in _PATTERNS:
        text = pattern.sub(_substitute, text)
    return text


def _substitute(match: re.Match[str]) -> str:
    """Keep the label a pattern captured, drop the value.

    A pattern captures nothing (replace the whole match), a leading label such as
    ``api_key=`` (keep it, so the log still says *which* field was scrubbed), or a
    label and a trailing delimiter such as the ``@`` of a URL's userinfo.
    """
    groups = match.groups()
    if not groups:
        return REDACTED
    prefix = groups[0] or ""
    suffix = groups[1] or "" if len(groups) > 1 else ""
    return f"{prefix}{REDACTED}{suffix}"


def redact_exception(
    exc: BaseException, *, known_values: Iterable[str | None] = ()
) -> str:
    """Render an exception and its chain safely.

    The type names survive because they are useful and carry no data; every message is
    scrubbed, including the causes, since that is where a provider's echoed credential
    usually ends up.
    """
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(
            f"{type(current).__name__}: {redact(str(current), known_values=known_values)}"
        )
        current = current.__cause__ or current.__context__
    return " <- ".join(parts)


def redact_mapping(
    payload: Mapping[str, Any], *, known_values: Iterable[str | None] = ()
) -> dict[str, Any]:
    """Scrub a structured log payload by key name and by value."""
    scrubbed: dict[str, Any] = {}
    for key, value in payload.items():
        if _SENSITIVE_KEY.match(key):
            scrubbed[key] = REDACTED
        elif isinstance(value, str):
            scrubbed[key] = redact(value, known_values=known_values)
        elif isinstance(value, Mapping):
            scrubbed[key] = redact_mapping(value, known_values=known_values)
        else:
            scrubbed[key] = value
    return scrubbed
