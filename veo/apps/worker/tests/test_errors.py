from __future__ import annotations

import pytest
from veo.contracts import RETRYABLE_ERROR_CODES, ApiError, ErrorCode

from veo_worker.runtime.cancellation import JobCancelledError
from veo_worker.runtime.errors import (
    SAFE_MESSAGES_KO,
    ProviderRateLimited,
    ProviderUnavailable,
    TargetUrlRejected,
    redact,
    to_api_error,
    to_safe_error,
)
from veo_worker.runtime.idempotency import IdempotencyConflictError
from veo_worker.runtime.state import IllegalTransitionError

SECRET = "sk-live-51H8xQqRTOKEN"
COOKIE = "SESSIONID=8f2b1c9d0e; NID_AUT=abcdef"


class LeakyProviderError(RuntimeError):
    """Stand-in for a provider client that stuffs the request into the exception."""

    def __init__(self) -> None:
        super().__init__(
            f"POST https://api.naver.com/keywords failed 401 "
            f"headers={{'Authorization': 'Bearer {SECRET}', 'Cookie': '{COOKIE}'}} "
            f"body={{'password': 'hunter2', 'customer_id': 1234567}}"
        )
        self.api_key = SECRET
        self.raw_payload = {"Authorization": f"Bearer {SECRET}"}


class TestSafeMessages:
    def test_secret_never_reaches_the_safe_message(self) -> None:
        safe = to_safe_error(LeakyProviderError())
        assert SECRET not in safe.message
        assert COOKIE not in safe.message
        assert "hunter2" not in safe.message
        assert "Authorization" not in safe.message
        assert "Bearer" not in safe.message

    def test_safe_message_comes_from_the_static_table_only(self) -> None:
        safe = to_safe_error(LeakyProviderError())
        assert safe.message == SAFE_MESSAGES_KO[safe.code]

    def test_every_error_code_has_a_safe_message(self) -> None:
        assert set(SAFE_MESSAGES_KO) == set(ErrorCode)
        assert all(msg.strip() for msg in SAFE_MESSAGES_KO.values())

    def test_internal_error_ref_is_present_and_unique(self) -> None:
        a = to_safe_error(LeakyProviderError())
        b = to_safe_error(LeakyProviderError())
        assert a.internal_error_ref
        assert a.internal_error_ref != b.internal_error_ref
        assert SECRET not in a.internal_error_ref

    def test_supplied_error_ref_is_honoured(self) -> None:
        safe = to_safe_error(RuntimeError("boom"), internal_error_ref="veo-err-fixed")
        assert safe.internal_error_ref == "veo-err-fixed"

    def test_api_error_never_carries_the_secret(self) -> None:
        error = to_api_error(LeakyProviderError())
        assert isinstance(error, ApiError)
        blob = error.model_dump_json()
        assert SECRET not in blob
        assert COOKIE not in blob
        assert "hunter2" not in blob


class TestClassification:
    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            (JobCancelledError(job_id="j", stage_key="fetch"), ErrorCode.JOB_CANCELLED),
            (
                IdempotencyConflictError(
                    job_type="SEO_SCAN",
                    idempotency_key="k",
                    existing_job_id="job-a",
                    existing_input_hash="a" * 64,
                    submitted_input_hash="b" * 64,
                ),
                ErrorCode.CONFLICT,
            ),
            (ProviderUnavailable("naver"), ErrorCode.PROVIDER_UNAVAILABLE),
            (ProviderRateLimited("naver"), ErrorCode.PROVIDER_RATE_LIMITED),
            (TargetUrlRejected("http://127.0.0.1/"), ErrorCode.TARGET_URL_REJECTED),
            (TimeoutError("read timed out"), ErrorCode.PROVIDER_UNAVAILABLE),
            (ConnectionError("dns failure"), ErrorCode.PROVIDER_UNAVAILABLE),
            (ValueError("bad depth"), ErrorCode.VALIDATION_FAILED),
            (NotImplementedError("SEO collector lands in Phase 2"), ErrorCode.INTERNAL_ERROR),
            (RuntimeError("who knows"), ErrorCode.INTERNAL_ERROR),
        ],
    )
    def test_exceptions_map_to_the_expected_code(
        self, exc: BaseException, expected: ErrorCode
    ) -> None:
        assert to_safe_error(exc).code is expected

    def test_illegal_transition_is_an_internal_error(self) -> None:
        from veo.contracts import JobStatus

        exc = IllegalTransitionError(JobStatus.SUCCEEDED, JobStatus.RUNNING)
        assert to_safe_error(exc).code is ErrorCode.INTERNAL_ERROR

    def test_retryable_flag_follows_the_shared_contract(self) -> None:
        for code in ErrorCode:
            safe = to_safe_error(RuntimeError("x"), code=code)
            assert safe.retryable is (code in RETRYABLE_ERROR_CODES)

    def test_not_implemented_is_never_retried(self) -> None:
        safe = to_safe_error(NotImplementedError("SEO collector lands in Phase 2"))
        assert safe.code is ErrorCode.INTERNAL_ERROR
        assert safe.retryable is False, "retrying a missing implementation only burns quota"

    def test_cancellation_is_never_retried(self) -> None:
        safe = to_safe_error(JobCancelledError(job_id="j", stage_key="fetch"))
        assert safe.retryable is False


class TestRedaction:
    @pytest.mark.parametrize(
        "text",
        [
            f"Authorization: Bearer {SECRET}",
            f"api_key={SECRET}",
            f'{{"password": "hunter2", "token": "{SECRET}"}}',
            f"Cookie: {COOKIE}",
            f"X-Naver-Client-Secret: {SECRET}",
            f"?client_secret={SECRET}&scope=all",
        ],
    )
    def test_redact_removes_credential_material(self, text: str) -> None:
        cleaned = redact(text)
        assert SECRET not in cleaned
        assert "hunter2" not in cleaned
        assert "NID_AUT=abcdef" not in cleaned
        assert "[REDACTED]" in cleaned

    def test_redact_keeps_the_shape_of_the_message_useful(self) -> None:
        cleaned = redact(f"POST https://api.naver.com/keywords failed 401 api_key={SECRET}")
        assert "https://api.naver.com/keywords" in cleaned
        assert "401" in cleaned

    def test_redacted_detail_of_an_exception_is_safe_to_log(self) -> None:
        from veo_worker.runtime.errors import redacted_detail

        detail = redacted_detail(LeakyProviderError())
        assert "LeakyProviderError" in detail
        assert SECRET not in detail
        assert COOKIE not in detail
        assert "hunter2" not in detail
