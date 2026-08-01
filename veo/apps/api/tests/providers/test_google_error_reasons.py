"""구글이 400 하나에 담아 보내는 서로 반대인 두 사건을 가른다.

```
키가 잘못됐다          → 우리가 고칠 일.    고객은 할 수 있는 것이 없다.
대상 사이트를 못 열었다  → 고객에게 알릴 정보. 우리 설정은 멀쩡하다.
```

둘 다 400 이고, 가르지 않으면 둘 다 "Google 응답 형식이 VEO가 아는 형식과 다릅니다" 로
나간다. 그 문장을 읽은 사람은 **구글이 스키마를 바꿨다고 믿고** 구글 변경 이력을 뒤지는
동안, 우리 키는 죽어 있고 진단은 계속 돈다.

이 파일이 지키는 성질 셋:

1. 두 원인이 서로 다른 문장으로 나간다.
2. **구글의 오류 문장은 한 글자도 고객에게 가지 않는다** — 구글은 거부된 키를 오류
   메시지에 그대로 되돌려 준다. 우리가 본문에서 꺼내는 것은 원인 토큰 하나뿐이다.
3. 열리지 않는 페이지를 다시 열어 보지 않는다. 재시도는 **모든 조직이 함께 쓰는**
   하루 한도를 태운다.
"""

from __future__ import annotations

import httpx
import pytest
from google_fixtures import SITE_URL
from pydantic import SecretStr

from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.errors import (
    UNKNOWN,
    GoogleKeyRejectedError,
    GoogleRequestRejectedError,
    GoogleSchemaError,
    GoogleServerError,
    GoogleTargetUnreachableError,
    classify_status,
    reason_from_error_body,
)
from veo.providers.google.pagespeed import PageSpeedClient

CREDENTIALS = PageSpeedCredentials(api_key=SecretStr("synthetic-pagespeed-key"))

#: 거부된 키를 그대로 되돌려 주는 구글의 실제 문장 형태. **밖으로 나가면 안 되는 것.**
LEAKED_KEY_TEXT = "API key not valid. Please pass a valid API key. key=AIzaSyD-synthetic"


def error_body(reason: str, *, message: str = LEAKED_KEY_TEXT) -> dict:
    """구글 오류 본문의 모양. 원인은 `details` 에, 사람이 읽는 문장은 `message` 에."""
    return {
        "error": {
            "code": 400,
            "message": message,
            "status": "INVALID_ARGUMENT",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": reason,
                    "domain": "googleapis.com",
                }
            ],
        }
    }


def build_client(handler: object, **kwargs: object) -> PageSpeedClient:
    return PageSpeedClient(
        credentials=CREDENTIALS,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        sleep=lambda seconds: None,  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# 본문에서 원인만 꺼낸다
# --------------------------------------------------------------------------- #


class TestOnlyTheReasonTokenComesOut:
    def test_the_new_details_shape_is_read(self) -> None:
        body = httpx.Response(400, json=error_body("API_KEY_INVALID")).content
        assert reason_from_error_body(body) == "API_KEY_INVALID"

    def test_the_older_errors_shape_is_read_too(self) -> None:
        """구글이 같은 뜻을 두 군데에 쓴다. 하나만 보면 조용히 못 가른다."""
        body = httpx.Response(
            400, json={"error": {"errors": [{"reason": "badRequest"}]}}
        ).content
        assert reason_from_error_body(body) == "badRequest"

    def test_prose_is_never_accepted_as_a_reason(self) -> None:
        """**이 시험이 키 유출을 막는다.**

        원인 자리에 문장이 들어와도 통과시키지 않는다. 통과시키면 그 문장이 분류를
        타고 흘러 다니게 되고, 구글의 문장에는 키가 들어 있다.
        """
        body = httpx.Response(
            400, json={"error": {"details": [{"reason": LEAKED_KEY_TEXT}]}}
        ).content
        assert reason_from_error_body(body) is None

    @pytest.mark.parametrize(
        "body",
        [
            b"",
            b"not json at all",
            b"<html>maintenance</html>",
            b"[]",
            b'{"error": "a string, not an object"}',
            b'{"error": {"details": "not a list"}}',
            b'{"error": {"details": [null, 3]}}',
        ],
    )
    def test_an_unreadable_body_is_simply_no_reason(self, body: bytes) -> None:
        """못 읽는 것은 정상이다. 여기서 예외가 나면 400 자체를 잃는다."""
        assert reason_from_error_body(body) is None


# --------------------------------------------------------------------------- #
# 원인이 상태 코드보다 먼저다
# --------------------------------------------------------------------------- #


class TestTheReasonDecidesBeforeTheStatus:
    def test_a_rejected_key_on_400_is_not_a_schema_surprise(self) -> None:
        error = classify_status(400, reason="API_KEY_INVALID")
        assert isinstance(error, GoogleKeyRejectedError)

    def test_an_unreachable_target_on_400_is_its_own_error(self) -> None:
        error = classify_status(400, reason="FAILED_DOCUMENT_REQUEST")
        assert isinstance(error, GoogleTargetUnreachableError)

    def test_an_unreachable_target_on_500_is_not_retried_as_a_server_fault(self) -> None:
        """**한도가 걸려 있는 분기다.**

        상태부터 보면 5xx 는 재시도 가능이고, 그러면 열리지 않는 페이지를 다시 열어
        보느라 모든 조직이 함께 쓰는 하루 한도를 태운다.
        """
        error = classify_status(500, reason="FAILED_DOCUMENT_REQUEST")

        assert isinstance(error, GoogleTargetUnreachableError)
        assert not isinstance(error, GoogleServerError)
        assert error.retryable is False

    def test_a_plain_500_is_still_a_retryable_server_fault(self) -> None:
        """원인이 없을 때의 동작은 달라지지 않는다."""
        error = classify_status(500)
        assert isinstance(error, GoogleServerError)
        assert error.retryable is True

    def test_an_unknown_4xx_is_a_rejected_request_not_a_schema_surprise(self) -> None:
        """우리가 보낸 것이 거절된 것과 응답 형식이 달라진 것은 다른 사건이다."""
        error = classify_status(400)

        assert isinstance(error, GoogleRequestRejectedError)
        assert not isinstance(error, GoogleSchemaError)

    def test_a_status_outside_any_class_is_still_a_schema_surprise(self) -> None:
        assert isinstance(classify_status(399), GoogleSchemaError)

    def test_a_reason_google_never_documented_falls_back_to_the_status(self) -> None:
        """모르는 토큰을 아는 척하지 않는다."""
        assert isinstance(classify_status(400, reason="SOMETHING_NEW"), GoogleRequestRejectedError)


class TestTheTwoCausesReadDifferently:
    def test_the_key_problem_says_it_is_not_the_site(self) -> None:
        """성능이 통째로 빠진 보고서를 받은 고객은 자기 사이트부터 고치려 든다."""
        text = GoogleKeyRejectedError("x").message_ko

        assert "사이트의 문제가 아니" in text

    def test_the_site_problem_says_what_to_look_at(self) -> None:
        text = GoogleTargetUnreachableError("x").message_ko

        assert "열지 못" in text
        assert text != GoogleKeyRejectedError("x").message_ko

    def test_neither_reads_like_a_schema_change(self) -> None:
        """이 문장을 읽고 구글 변경 이력을 뒤지러 가는 사람이 없어야 한다."""
        for error in (GoogleKeyRejectedError("x"), GoogleTargetUnreachableError("x")):
            assert "형식" not in error.message_ko


# --------------------------------------------------------------------------- #
# 실제 호출 경로 — 본문을 읽어야만 갈린다
# --------------------------------------------------------------------------- #


class TestTheAdapterReadsTheErrorBody:
    def test_a_rejected_key_reaches_the_screen_as_our_problem(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json=error_body("API_KEY_INVALID"))

        outcome = build_client(handler).measure(SITE_URL)

        assert outcome.value is UNKNOWN
        assert outcome.failure is not None
        assert "사이트의 문제가 아니" in outcome.failure.reason_ko

    def test_an_unreachable_page_reaches_the_screen_as_the_sites_problem(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json=error_body("FAILED_DOCUMENT_REQUEST"))

        outcome = build_client(handler).measure(SITE_URL)

        assert outcome.failure is not None
        assert "열지 못" in outcome.failure.reason_ko

    def test_googles_own_words_never_reach_the_customer(self) -> None:
        """구글은 거부된 키를 오류 메시지에 그대로 되돌려 준다."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json=error_body("API_KEY_INVALID"))

        outcome = build_client(handler).measure(SITE_URL)

        assert outcome.failure is not None
        assert LEAKED_KEY_TEXT not in outcome.failure.reason_ko
        assert "AIzaSy" not in outcome.failure.reason_ko

    def test_an_unopenable_page_is_asked_for_exactly_once(self) -> None:
        """재시도는 같은 답을 받아 오면서 한도만 태운다."""
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(500, json=error_body("FAILED_DOCUMENT_REQUEST"))

        build_client(handler).measure(SITE_URL)

        assert calls == 1

    def test_a_plain_server_fault_is_still_retried(self) -> None:
        """원인이 없으면 지금까지 하던 대로 재시도한다 — 이 변경의 범위 밖이다."""
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(500, json={"error": {"message": "boom"}})

        build_client(handler).measure(SITE_URL)

        assert calls > 1

    def test_an_error_body_too_large_to_read_still_yields_the_status(self) -> None:
        """본문을 못 읽었다고 400 이 전송 오류로 둔갑하면 안 된다."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, content=b"x" * 4096)

        outcome = build_client(handler, max_error_bytes=64).measure(SITE_URL)

        assert outcome.value is UNKNOWN
        assert outcome.failure is not None
        assert outcome.failure.reason_ko
