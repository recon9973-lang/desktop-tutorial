"""알림 통로 한 벌 — 보낸 척하지 않고, 죽어도 본업을 데려가지 않는다."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
from pydantic import SecretStr

from veo.notify import AlertOutcome, send_alert


def settings_with(url: str | None):  # type: ignore[no-untyped-def]
    return SimpleNamespace(alert_webhook_url=None if url is None else SecretStr(url))


class RecordingClient:
    def __init__(self, *, status_code: int = 200, explode: bool = False) -> None:
        self.status_code = status_code
        self.explode = explode
        self.requests: list[tuple[str, dict]] = []  # type: ignore[type-arg]

    def post(self, url, json, timeout):  # type: ignore[no-untyped-def]
        if self.explode:
            raise httpx.ConnectError("연결 실패")
        self.requests.append((url, json))
        request = httpx.Request("POST", url)
        return httpx.Response(self.status_code, request=request)


def test_no_url_means_disabled_not_pretend_sent() -> None:
    outcome = send_alert(
        title_ko="t", body_ko="b", source="test", settings=settings_with(None)
    )
    assert outcome is AlertOutcome.DISABLED


def test_plain_http_is_refused() -> None:
    """웹훅 URL 에는 토큰이 들어 있다 — 평문으로 보내면 토큰이 노출된다."""
    client = RecordingClient()
    outcome = send_alert(
        title_ko="t",
        body_ko="b",
        source="test",
        settings=settings_with("http://hooks.example/x"),
        client=client,
    )
    assert outcome is AlertOutcome.FAILED
    assert client.requests == []


def test_a_sent_alert_carries_title_body_and_source() -> None:
    client = RecordingClient()
    outcome = send_alert(
        title_ko="한도 경보",
        body_ko="자세한 내용",
        source="usage.pagespeed_quota",
        settings=settings_with("https://hooks.example/x"),
        client=client,
    )
    assert outcome is AlertOutcome.SENT
    (url, payload), = client.requests
    assert url == "https://hooks.example/x"
    assert "한도 경보" in payload["text"]
    assert "자세한 내용" in payload["text"]
    assert "usage.pagespeed_quota" in payload["text"]


def test_delivery_failure_is_swallowed_and_reported() -> None:
    outcome = send_alert(
        title_ko="t",
        body_ko="b",
        source="test",
        settings=settings_with("https://hooks.example/x"),
        client=RecordingClient(explode=True),
    )
    assert outcome is AlertOutcome.FAILED


def test_a_non_2xx_response_is_a_failure_not_a_sent() -> None:
    outcome = send_alert(
        title_ko="t",
        body_ko="b",
        source="test",
        settings=settings_with("https://hooks.example/x"),
        client=RecordingClient(status_code=500),
    )
    assert outcome is AlertOutcome.FAILED


def test_the_webhook_url_can_only_come_from_settings() -> None:
    """SSRF 허용 목록(launch blocker B-6)의 반대편 절반 — 이 파일은 요청 객체를
    모른다. 고객이 고른 URL 이 이 통로로 들어올 문이 코드에 없다."""
    import pathlib

    import veo.notify.webhook as webhook

    source = pathlib.Path(webhook.__file__).read_text(encoding="utf-8")
    for forbidden in ("Request", "fastapi", "payload.urls", "target_url"):
        assert forbidden not in source, f"webhook.py 가 {forbidden} 을 만진다"
    assert "alert_webhook_url" in source
