"""A log line is a place customer data leaks, so these tests read the emitted bytes.

Every assertion below inspects what was actually *written to the stream*, never the
dictionary that was handed to the logger. A redaction test that checks its own input is a
test that passes while the secret sails out through a renderer nobody instrumented.
"""

from __future__ import annotations

import importlib.util
import io
import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from veo.observability.logging import (
    REDACTED,
    bind_log_context,
    clear_log_context,
    configure_logging,
    get_logger,
    hash_identifier,
    log_request_completed,
)

# Fixtures that look exactly like the real thing, because the patterns match on shape.
BEARER = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ2ZW5vbSJ9.Zm9vYmFyYmF6cXV4"
PROVIDER_KEY = "sk-live-9f3a2b7c1d8e4f6a0b5c7d9e1f3a5b7c"
CUSTOMER_EMAIL = "jane.doe@ondam-clinic.example.com"
CUSTOMER_IP = "203.0.113.42"
PASSWORD = "correct-horse-battery-staple"


def emit(
    event: str = "test.event",
    *,
    level: str = "info",
    json_output: bool = True,
    min_level: str = "DEBUG",
    **fields: Any,
) -> tuple[str, dict[str, Any] | None]:
    """Log one line through the real production chain and return the raw text.

    The parsed record is returned alongside it only as a convenience for structural
    assertions; the secret assertions always run against the raw string.
    """
    stream = io.StringIO()
    configure_logging(json_output=json_output, level=min_level, stream=stream)
    logger = get_logger("veo.test")
    getattr(logger, level)(event, **fields)
    raw = stream.getvalue()
    parsed = json.loads(raw) if json_output and raw.strip() else None
    return raw, parsed


# --------------------------------------------------------------------------- #
# Credentials
# --------------------------------------------------------------------------- #


def test_a_password_never_reaches_the_emitted_line() -> None:
    raw, record = emit("auth.login.failed", password=PASSWORD)

    assert PASSWORD not in raw
    assert record is not None
    assert "password" not in record
    # The operator still learns that *something* was refused, which is how a careless
    # call site gets found and fixed.
    assert "password" in record["dropped_fields"]


def test_a_bearer_token_in_the_message_is_scrubbed() -> None:
    raw, record = emit(f"provider rejected us: Authorization: {BEARER}")

    assert "eyJhbGciOiJIUzI1NiJ9" not in raw
    assert "Zm9vYmFyYmF6cXV4" not in raw
    assert record is not None
    assert REDACTED in record["event"]


def test_a_provider_key_is_scrubbed_wherever_it_appears() -> None:
    raw, _ = emit(f"naver call failed with api_key={PROVIDER_KEY}")
    assert PROVIDER_KEY not in raw
    assert "9f3a2b7c1d8e4f6a0b5c7d9e1f3a5b7c" not in raw


def test_a_quoted_credential_is_scrubbed() -> None:
    """Python reprs quote their strings, so the log boundary must survive that shape.

    ``veo.credentials.redaction`` once matched ``password=value`` but not
    ``password='value'`` — its value pattern could not start on a single quote — which
    left every traceback rendering a local and every ``!r`` format field leaking. That is
    fixed upstream and the scrubbing here is entirely its work; this test stays because
    the guarantee is owed at *this* boundary, and a future change to the processor chain
    that stopped applying ``redact`` to a field would show up here rather than in
    production.
    """
    raw, _ = emit(f"login refused with password='{PASSWORD}'")
    assert PASSWORD not in raw

    raw, _ = emit("provider config was {'api_key': 'naver-customer-1234567'}")
    assert "naver-customer-1234567" not in raw

    raw, _ = emit('provider config was {"api_key": "naver-customer-7654321"}')
    assert "naver-customer-7654321" not in raw


def test_an_ordinary_looking_credential_in_a_traceback_repr_is_scrubbed() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, level="DEBUG", stream=stream)
    logger = get_logger("veo.test")
    credential = "naver-customer-1234567"

    try:
        raise RuntimeError(f"provider rejected api_key={credential!r}")
    except RuntimeError:
        logger.error("provider.call.failed", exc_info=True)

    assert credential not in stream.getvalue()


def test_a_credential_in_a_traceback_is_scrubbed() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, level="DEBUG", stream=stream)
    logger = get_logger("veo.test")

    try:
        raise RuntimeError(f"provider refused Authorization: {BEARER}")
    except RuntimeError:
        logger.error("provider.call.failed", exc_info=True)

    raw = stream.getvalue()
    assert "eyJhbGciOiJIUzI1NiJ9" not in raw
    assert "Zm9vYmFyYmF6cXV4" not in raw
    # The diagnosis survives even though the secret does not.
    assert "RuntimeError" in raw


def test_a_credential_in_a_chained_cause_is_scrubbed() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, level="DEBUG", stream=stream)
    logger = get_logger("veo.test")

    try:
        try:
            raise ValueError(f"key={PROVIDER_KEY}")
        except ValueError as cause:
            raise RuntimeError("upstream failed") from cause
    except RuntimeError:
        logger.error("provider.call.failed", exc_info=True)

    raw = stream.getvalue()
    assert PROVIDER_KEY not in raw
    assert "ValueError" in raw


# --------------------------------------------------------------------------- #
# Personal data
# --------------------------------------------------------------------------- #


def test_a_raw_email_is_scrubbed_even_under_an_allowed_key() -> None:
    raw, record = emit("customer.notified", identifier_hash=CUSTOMER_EMAIL)

    assert CUSTOMER_EMAIL not in raw
    assert "jane.doe" not in raw
    assert record is not None
    assert record["identifier_hash"] == REDACTED


def test_a_raw_ip_is_scrubbed_even_under_a_key_that_promises_a_hash() -> None:
    raw, record = emit("http.request.completed", client_ip_hash=CUSTOMER_IP)

    assert CUSTOMER_IP not in raw
    assert record is not None
    assert record["client_ip_hash"] == REDACTED


def test_an_ipv6_address_is_scrubbed() -> None:
    raw, _ = emit("http.request.completed", client_ip_hash="2001:0db8:85a3::8a2e:0370:7334")
    assert "2001:0db8" not in raw


def test_a_raw_ai_answer_is_dropped_rather_than_logged() -> None:
    answer = "온담의원은 강남구에서 추천되는 병원입니다. 전화 010-1234-5678."
    raw, record = emit("observation.recorded", answer_text=answer)

    assert "온담의원은 강남구에서" not in raw
    assert record is not None
    assert "answer_text" in record["dropped_fields"]


# --------------------------------------------------------------------------- #
# Organization identity
# --------------------------------------------------------------------------- #


def test_an_organization_id_that_is_a_name_is_refused() -> None:
    raw, record = emit("scan.started", organization_id="온담의원")

    assert "온담의원" not in raw
    assert record is not None
    assert record["organization_id"] == REDACTED


def test_an_organization_id_that_is_a_uuid_survives() -> None:
    org_id = str(uuid.uuid4())
    _, record = emit("scan.started", organization_id=org_id)

    assert record is not None
    assert record["organization_id"] == org_id


# --------------------------------------------------------------------------- #
# Levels and renderers
# --------------------------------------------------------------------------- #


def test_debug_level_is_redacted_too() -> None:
    raw, _ = emit("auth.debug", level="debug", min_level="DEBUG", password=PASSWORD)
    assert PASSWORD not in raw
    assert raw.strip(), "the debug line should have been emitted at all"


def test_the_human_readable_renderer_is_redacted_too() -> None:
    raw, _ = emit(
        f"provider refused Authorization: {BEARER}",
        json_output=False,
        client_ip_hash=CUSTOMER_IP,
    )
    assert "Zm9vYmFyYmF6cXV4" not in raw
    assert CUSTOMER_IP not in raw
    assert "provider refused" in raw


# --------------------------------------------------------------------------- #
# The operational fields the module exists to produce
# --------------------------------------------------------------------------- #


def test_a_completed_request_records_correlation_route_latency_and_outcome() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, level="INFO", stream=stream)
    org_id = uuid.uuid4()

    log_request_completed(
        get_logger("veo.api"),
        correlation_id="0123456789abcdef",
        route="/api/v1/seo/scan",
        method="POST",
        status_code=200,
        latency_ms=142,
        outcome="OK",
        organization_id=org_id,
    )

    record = json.loads(stream.getvalue())
    assert record["correlation_id"] == "0123456789abcdef"
    assert record["route"] == "/api/v1/seo/scan"
    assert record["method"] == "POST"
    assert record["status_code"] == 200
    assert record["latency_ms"] == 142
    assert record["outcome"] == "OK"
    assert record["organization_id"] == str(org_id)


def test_a_secret_bound_into_the_ambient_context_is_scrubbed_on_the_way_out() -> None:
    """Context variables are merged into every event, so they need scrubbing too.

    Bound once, emitted a hundred times: scrubbing at bind time would check the value
    once and trust it thereafter. It is checked on every emission instead.
    """
    stream = io.StringIO()
    configure_logging(json_output=True, level="INFO", stream=stream)
    bind_log_context(client_ip_hash=CUSTOMER_IP, password=PASSWORD, route="/api/v1/x")
    try:
        get_logger("veo.api").info("scan.started")
        get_logger("veo.api").info("scan.finished")
    finally:
        clear_log_context()

    raw = stream.getvalue()
    assert CUSTOMER_IP not in raw
    assert PASSWORD not in raw
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    assert len(records) == 2
    for record in records:
        assert record["route"] == "/api/v1/x"
        assert record["client_ip_hash"] == REDACTED


def test_the_context_is_gone_once_cleared() -> None:
    bind_log_context(route="/api/v1/x")
    clear_log_context()
    _, record = emit("scan.started")

    assert record is not None
    assert "route" not in record


def test_a_credential_in_captured_stack_info_is_scrubbed() -> None:
    """``stack_info=True`` echoes source lines, and a source line can hold a literal."""
    stream = io.StringIO()
    configure_logging(json_output=True, level="DEBUG", stream=stream)
    log = get_logger("veo.test")

    def deeper() -> None:
        # This very line is what the captured stack prints for this frame.
        log.info("connecting api_key='naver-customer-1234567'", stack_info=True)

    deeper()
    raw = stream.getvalue()
    record = json.loads(raw)

    assert "naver-customer-1234567" not in raw
    # Proves the scrub reached the stack field specifically, not only the message.
    assert record["stack"].count(REDACTED) >= 1


def test_unknown_fields_are_dropped_and_named() -> None:
    _, record = emit("something.happened", surprise_field="whatever", another=1)

    assert record is not None
    assert "surprise_field" not in record
    assert "another" not in record
    assert record["dropped_fields"] == ["another", "surprise_field"]


def test_a_clean_event_carries_no_dropped_fields_marker() -> None:
    _, record = emit("scan.finished", outcome="OK", latency_ms=12)

    assert record is not None
    assert "dropped_fields" not in record


# --------------------------------------------------------------------------- #
# Hashing, for the things that must be correlated but not read
# --------------------------------------------------------------------------- #


def test_hash_identifier_is_stable_and_does_not_contain_its_input() -> None:
    first = hash_identifier(CUSTOMER_EMAIL)
    second = hash_identifier(CUSTOMER_EMAIL)

    assert first == second
    assert CUSTOMER_EMAIL not in first
    assert "jane.doe" not in first
    # Deliberately shorter than the 32-hex run the credential scrubber treats as key
    # material — a hash VEO produced must not be mistaken for a secret VEO leaked.
    assert len(first) == 24
    assert first != hash_identifier(CUSTOMER_IP)


def test_hash_identifier_separates_namespaces() -> None:
    assert hash_identifier(CUSTOMER_IP, namespace="ip") != hash_identifier(
        CUSTOMER_IP, namespace="email"
    )


def test_hash_identifier_refuses_an_empty_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        hash_identifier("")


def load_auth_hashing() -> Any:
    """Load ``veo/auth/hashing.py`` without executing ``veo/auth/__init__.py``.

    ``import veo.auth.hashing`` raises: the package ``__init__`` reaches the FastAPI app,
    which reaches back into ``veo.auth.router`` while it is still initialising. That is
    INTEGRATION_REQUEST item 1. Importing ``veo.api`` first does work around the cycle,
    but pulling the application into this suite's import graph perturbs later suites in a
    full run, so the module is loaded straight off disk instead. It imports nothing but
    ``hashlib``, so loading it in isolation is exact.
    """
    import veo

    path = Path(veo.__file__).resolve().parent / "auth" / "hashing.py"
    spec = importlib.util.spec_from_file_location("veo_auth_hashing_isolated", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_log_digest_is_a_prefix_of_the_audit_digest() -> None:
    """The two digests must stay joinable, so drift has to fail a test."""
    identifier_hash = load_auth_hashing().identifier_hash

    for sample in (CUSTOMER_EMAIL, CUSTOMER_IP, "Analyst@Example.Test"):
        assert identifier_hash(sample).startswith(hash_identifier(sample))


def test_a_hashed_identifier_survives_the_scrubber() -> None:
    digest = hash_identifier(CUSTOMER_IP, namespace="ip")
    _, record = emit("http.request.completed", client_ip_hash=digest)

    assert record is not None
    assert record["client_ip_hash"] == digest
