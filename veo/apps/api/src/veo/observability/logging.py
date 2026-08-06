"""Structured logging, and the processor that makes a log line safe to keep.

A log line is a place customer data leaks. It is written at every severity, kept longer
than anyone intends, shipped to a third-party aggregator, and read by people who never
saw the code that produced it. So this module treats the emitted line — not the call
site — as the boundary that has to hold.

Two defences, borrowed rather than invented:

* **An allowlist of field names.** :data:`ALLOWED_EVENT_KEYS` names every field VEO logs.
  A field nobody has reviewed is dropped, and its *name* is reported under
  ``dropped_fields`` so a careless call site is findable. This is the shape
  :mod:`veo.auth.audit` already uses for the audit trail; a second, looser policy for
  logs would make the audit trail's guarantees meaningless, since the same values pass
  through both.
* **A value scrubber.** Every string — including the message itself, including a
  rendered traceback — goes through :func:`veo.credentials.redaction.redact`, which is
  the codebase's credential scrubber, plus the personal-data shapes below. Nothing is
  exempt by level: DEBUG output leaks exactly as thoroughly as ERROR output.

What must be correlated is hashed, never logged raw: see :func:`hash_identifier`, whose
digest is a prefix of the one :mod:`veo.auth.hashing` writes to the audit trail, so a log
line and an audit row can still be joined.

The renderer is JSON in production and human-readable locally. Both run the same
processor chain — a redaction that only applies to one renderer is a redaction that will
be bypassed by whichever one the incident happens in.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
import uuid
from collections.abc import Collection, Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any, Final, TextIO, cast

import structlog
from structlog.typing import EventDict, FilteringBoundLogger, Processor, WrappedLogger

from veo.credentials.redaction import REDACTED, redact

__all__ = [
    "ALLOWED_EVENT_KEYS",
    "DROPPED_FIELDS_KEY",
    "LOG_DIGEST_LENGTH",
    "REDACTED",
    "bind_log_context",
    "build_processors",
    "clear_log_context",
    "configure_logging",
    "get_logger",
    "hash_identifier",
    "log_request_completed",
    "redact_processor",
    "scrub_fields",
    "scrub_text",
]

#: Where the names of refused fields are reported. A name is developer-authored; a value
#: is not, which is why one survives and the other does not.
DROPPED_FIELDS_KEY: Final = "dropped_fields"

#: Hex characters in a log digest. Deliberately shorter than the 32-hex run that the
#: credential scrubber treats as key material — otherwise VEO's own hashes would be
#: redacted as though they were secrets it had leaked.
LOG_DIGEST_LENGTH: Final = 24

#: Every field VEO logs. Anything else is dropped rather than scrubbed, because a key
#: nobody has reviewed is a key nobody has reasoned about the contents of.
#:
#: Two deliberate absences. There is no ``url`` — a full URL carries query parameters and
#: a customer's page structure, so log ``url_host`` and the path template instead. There
#: is no ``answer_text``, ``prompt_text`` or ``snippet``: a raw AI answer is customer
#: content and belongs in the database row it was stored under, addressed here by id.
ALLOWED_EVENT_KEYS: Final = frozenset(
    {
        # Emitted by the processor chain itself.
        "event",
        "level",
        "timestamp",
        "logger",
        "exception",
        "stack",
        # Correlation.
        "correlation_id",
        "request_id",
        "trace_id",
        "span_id",
        "parent_span_id",
        "organization_id",
        "actor_user_id",
        "identifier_hash",
        "client_ip_hash",
        "user_agent_hash",
        "organization_hash",
        # Domain objects, by id.
        "project_id",
        "site_id",
        "scan_id",
        "run_id",
        "job_id",
        "task_id",
        "report_id",
        # HTTP.
        "route",
        "method",
        "status_code",
        "status_class",
        "latency_ms",
        "outcome",
        "error_code",
        # Queue and worker.
        "queue",
        "depth",
        "wait_ms",
        "attempt",
        "retries",
        "retryable",
        "dead_lettered",
        # Crawling.
        "url_host",
        "pages",
        "bytes",
        "robots_allowed",
        # Providers.
        "provider",
        "provider_state",
        "circuit_state",
        "cache_hit",
        "engine",
        "model",
        "model_version",
        "retry_after_seconds",
        # Cost.
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "cost_basis",
        "budget_status",
        "spent_usd",
        "unmeasurable_calls",
        "month",
        # Reports and scoring.
        "report_kind",
        "generation_ms",
        "spec_id",
        "spec_version",
        "spec_checksum",
        "coverage",
        "confidence",
    }
)

#: Keys whose value must be a UUID or nothing. An organization is identified by its id,
#: never by its name — a clinic's name in a shared log stream is a customer relationship
#: disclosed to whoever operates the aggregator.
UUID_ONLY_KEYS: Final = frozenset({"organization_id", "actor_user_id"})

#: Keys the processor chain produces and the scrubber must leave alone. A timestamp is
#: full of colons and would otherwise be mistaken for an IPv6 address.
_GENERATED_KEYS: Final = frozenset({"timestamp", "level", "logger", DROPPED_FIELDS_KEY})

#: Shapes that are personal data wherever they appear. The credential scrubber does not
#: look for these — it is aimed at secrets — so they are checked separately.
_PERSONAL_DATA: Final[tuple[re.Pattern[str], ...]] = (
    # Email addresses.
    re.compile(r"[^\s@,;<>()\[\]]+@[^\s@,;<>()\[\]]+\.[A-Za-z]{2,}"),
    # IPv4.
    re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    # IPv6, in any of its compressed forms. Three colon-separated groups minimum, so an
    # ISO timestamp's ``12:00:00`` is not mistaken for an address.
    re.compile(r"(?:[0-9a-fA-F]{0,4}:){3,}[0-9a-fA-F]{0,4}"),
    # Korean telephone numbers, mobile and landline.
    re.compile(r"\b0\d{1,2}-?\d{3,4}-?\d{4}\b"),
)

_LEVELS: Final[Mapping[str, int]] = {
    "CRITICAL": 50,
    "ERROR": 40,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10,
}

#: Set to ``json`` or ``console`` to override renderer selection.
LOG_FORMAT_ENV: Final = "VEO_LOG_FORMAT"


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #


def hash_identifier(value: str, *, namespace: str = "") -> str:
    """A digest for something that must be correlated but never read.

    With no ``namespace`` the result is a **prefix of the digest**
    :func:`veo.auth.hashing.identifier_hash` writes to the audit trail — same
    normalisation, same SHA-256, truncated — so a log line and an audit row for the same
    address still join. A ``namespace`` separates counters that must not be comparable:
    an IP and an email that happen to share text must not collapse into one series.

    The normalisation is repeated here rather than imported because ``veo.auth.hashing``
    is not importable on its own — ``veo/auth/__init__.py`` pulls in the FastAPI app and
    the import cycles. A worker that only needs to hash a string must not have to import
    the HTTP layer to do it. ``INTEGRATION_REQUEST.md`` item 1 asks for that import to be
    made safe so this copy can be deleted;
    ``test_logging.py::test_the_log_digest_is_a_prefix_of_the_audit_digest`` fails if the
    two ever drift.

    This is deliberately not a helper that hashes whatever a logger is handed: the caller
    hashes on purpose, at the point where it still knows what the value is. A sink that
    quietly hashed everything would be a sink nobody ever checked.
    """
    if not value or not value.strip():
        raise ValueError("identifier must not be empty")
    normalized = value.strip().casefold()
    material = f"{namespace}\x1f{normalized}" if namespace else normalized
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return digest[:LOG_DIGEST_LENGTH]


# --------------------------------------------------------------------------- #
# Scrubbing
# --------------------------------------------------------------------------- #


def scrub_text(value: str) -> str:
    """Remove secrets and personal data from one string.

    Scanned line by line. A rendered traceback is a single value tens of kilobytes long,
    and :func:`veo.credentials.redaction.redact` truncates its input at 4 KiB to bound
    regex work — which would silently discard the innermost frames, the ones an operator
    actually needs. Per line, the bound still holds and the frames survive.
    """
    if not value:
        return value
    scrubbed_lines = []
    for line in value.splitlines():
        cleaned = redact(line)
        for pattern in _PERSONAL_DATA:
            cleaned = pattern.sub(REDACTED, cleaned)
        scrubbed_lines.append(cleaned)
    return "\n".join(scrubbed_lines)


def _scrub_scalar(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return _scrub_scalar(value.value)
    if isinstance(value, uuid.UUID | datetime | date):
        return str(value)
    if isinstance(value, str):
        return scrub_text(value)
    return scrub_text(str(value))


def _scrub_value(key: str, value: Any) -> Any:
    """Scrub one field, or raise :class:`_Refused` if it may not be logged at all."""
    if key in UUID_ONLY_KEYS:
        return _as_uuid_text(value)
    if isinstance(value, Mapping):
        # A nested mapping carries keys nobody allowlisted. Flatten it at the call site
        # rather than granting a second, unreviewed namespace inside every event.
        raise _Refused
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_scrub_scalar(item) for item in value]
    if isinstance(value, bytes):
        raise _Refused
    return _scrub_scalar(value)


def _as_uuid_text(value: Any) -> str:
    if isinstance(value, uuid.UUID):
        return str(value)
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return REDACTED


class _Refused(Exception):
    """Internal signal: this field is dropped rather than scrubbed."""


def scrub_fields(
    fields: Mapping[str, Any], *, passthrough: Collection[str] = ()
) -> tuple[dict[str, Any], list[str]]:
    """Split fields into what may be emitted and the names of what may not.

    Shared by the log processor and by span attributes, which are log surface by another
    name: a span exported to a tracing backend is read by the same people, kept for the
    same length of time, and just as capable of carrying a password.
    """
    kept: dict[str, Any] = {}
    dropped: list[str] = []

    for key, value in fields.items():
        if key not in ALLOWED_EVENT_KEYS:
            dropped.append(key)
            continue
        if key in passthrough:
            kept[key] = value
            continue
        try:
            kept[key] = _scrub_value(key, value)
        except _Refused:
            dropped.append(key)

    return kept, sorted(dropped)


def redact_processor(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Reduce an event to allowlisted fields holding demonstrably safe values.

    Runs immediately before the renderer, so it sees the traceback that
    ``format_exc_info`` produced and every field bound anywhere upstream — a processor
    placed earlier would let a later one reintroduce what it removed.
    """
    kept, dropped = scrub_fields(event_dict, passthrough=_GENERATED_KEYS)
    if dropped:
        kept[DROPPED_FIELDS_KEY] = dropped
    return cast(EventDict, kept)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def build_processors(*, json_output: bool) -> list[Processor]:
    """The one processor chain, in the one order that is safe.

    ``redact_processor`` is last before the renderer. Everything that adds a field —
    context variables, the level, the timestamp, the formatted exception — runs ahead of
    it, so there is no path by which a field reaches the renderer unscrubbed.
    """
    renderer: Processor = (
        structlog.processors.JSONRenderer(ensure_ascii=False)
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_processor,
        renderer,
    ]


def _install_stdlib_bridge(*, json_output: bool, threshold: int, target: TextIO) -> None:
    """Route the standard library's ``logging`` through this module's chain too.

    ## Why this exists

    :func:`configure_logging` used to configure structlog and nothing else. But almost
    nothing in VEO logs *through* structlog — measured 2026-08-06: **22 modules call
    ``logging.getLogger``, one calls :func:`get_logger`.** Those 22 fell through to
    Python's ``lastResort`` handler, and that handler has two properties that matter:

    * It emits **WARNING and above only.** Every ``logger.info`` in the codebase was
      invisible in production. The line ``job %s queued on %s`` — added specifically so
      an operator could tell whether work reached the worker — never printed once.
    * It writes the record **raw**. No allowlist, no scrubber. So the half that did
      print was the half most likely to carry a secret: ``logger.exception`` in
      :mod:`veo.jobs.execution` renders a provider traceback, and the modules that talk
      to providers (:mod:`veo.common.security.egress_kr`,
      :mod:`veo.common.security.retry_via_kr`, :mod:`veo.notify.webhook`) are all on
      this path.

    The module docstring says the emitted line is the boundary that has to hold. It held
    for one caller out of twenty-three.

    ## Where redaction sits

    :func:`redact_processor` runs **after** ``remove_processors_meta`` and immediately
    before the renderer — the same position it holds in :func:`build_processors`. It has
    to be after the meta step because ``ProcessorFormatter`` carries ``_record`` and
    ``_from_structlog`` through the chain, and the allowlist would drop them.
    """
    formatter = structlog.stdlib.ProcessorFormatter(
        # Runs on records that came from the standard library rather than structlog.
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            # Turns ``exc_info`` into the rendered traceback string that the scrubber
            # below then goes through. Without it the traceback reaches the renderer
            # unscrubbed.
            structlog.processors.format_exc_info,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            redact_processor,
            structlog.processors.JSONRenderer(ensure_ascii=False)
            if json_output
            else structlog.dev.ConsoleRenderer(colors=False),
        ],
    )

    handler = logging.StreamHandler(target)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Replace rather than append. Configuring twice must not double every line, and a
    # bootstrap handler installed before this call is a handler without the scrubber.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(threshold)


def configure_logging(
    *,
    json_output: bool | None = None,
    level: str = "INFO",
    stream: TextIO | None = None,
) -> None:
    """Install the VEO logging configuration.

    ``json_output`` defaults to the ``VEO_LOG_FORMAT`` environment variable and, failing
    that, to whether the stream is a terminal: JSON where a machine will read it,
    human-readable where a person will.

    Configures **both** logging paths — structlog and the standard library — through the
    same processors, because the codebase uses both. See :func:`_install_stdlib_bridge`.
    """
    target = stream if stream is not None else sys.stderr
    if json_output is None:
        json_output = _json_output_default(target)

    threshold = _LEVELS.get(level.upper())
    if threshold is None:
        raise ValueError(f"unknown log level: {level!r}; expected one of {sorted(_LEVELS)}")

    structlog.configure(
        processors=build_processors(json_output=json_output),
        wrapper_class=structlog.make_filtering_bound_logger(threshold),
        logger_factory=structlog.WriteLoggerFactory(file=target),
        # Reconfiguration has to take effect — otherwise a process that configures
        # logging after something has already logged keeps the bootstrap chain, which is
        # the chain without the redaction processor in it.
        cache_logger_on_first_use=False,
    )
    _install_stdlib_bridge(json_output=json_output, threshold=threshold, target=target)


def _json_output_default(stream: TextIO) -> bool:
    configured = os.environ.get(LOG_FORMAT_ENV, "").strip().lower()
    if configured == "json":
        return True
    if configured in {"console", "human", "text"}:
        return False
    try:
        return not stream.isatty()
    except (AttributeError, ValueError):
        return True


def get_logger(name: str = "veo") -> FilteringBoundLogger:
    """A logger tagged with the module it speaks for."""
    return cast(FilteringBoundLogger, structlog.get_logger().bind(logger=name))


def bind_log_context(**fields: Any) -> None:
    """Bind fields onto every event emitted by this task or request.

    Values are not scrubbed here — they are scrubbed on the way out, like everything
    else, so a value bound once and emitted a hundred times is checked a hundred times
    rather than trusted after the first.
    """
    structlog.contextvars.bind_contextvars(**fields)


def clear_log_context() -> None:
    """Drop the ambient fields. Call at the end of a request or a task."""
    structlog.contextvars.clear_contextvars()


# --------------------------------------------------------------------------- #
# The one event this module emits on anybody's behalf
# --------------------------------------------------------------------------- #


def log_request_completed(
    logger: FilteringBoundLogger,
    *,
    correlation_id: str,
    route: str,
    method: str,
    status_code: int,
    latency_ms: int,
    outcome: str,
    organization_id: uuid.UUID | str | None = None,
    error_code: str | None = None,
) -> None:
    """Emit the single line that closes out a request.

    ``route`` should be the *template* — ``/api/v1/sites/{site_id}`` — not the resolved
    path. A resolved path puts a customer's identifiers into a field that gets grouped
    and counted, which is both a cardinality problem and a disclosure one.

    Severity follows the status: a 5xx is an error, a 4xx is a warning, everything else
    is informational. An operator filtering on ``level`` should see outages, not traffic.
    """
    fields: dict[str, Any] = {
        "correlation_id": correlation_id,
        "route": route,
        "method": method,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "outcome": outcome,
    }
    if organization_id is not None:
        fields["organization_id"] = organization_id
    if error_code is not None:
        fields["error_code"] = error_code

    if status_code >= 500:
        logger.error("http.request.completed", **fields)
    elif status_code >= 400:
        logger.warning("http.request.completed", **fields)
    else:
        logger.info("http.request.completed", **fields)
