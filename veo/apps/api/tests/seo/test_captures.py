"""잰 것을 남긴다 (0-K).

venomad.com 진단이 15~27점으로 나왔는데 "무엇을 받았길래 그 점수인가" 에 답할 방법이
없었다. 남은 것은 sha256 해시 64자와 수집기가 고른 2,000자 발췌뿐이었고, 둘 다 사람이
열어 볼 수 있는 것이 아니었다. 감사관 넷과 하루를 쓰고도 확정하지 못했다.

아무 AI에게 주소를 주면 페이지를 열어 보고 답한다. 측정기라면서 측정한 것을 안 갖고
있었던 것이 뿌리였다.

여기서 지키는 것:
1. **못 읽은 응답을 먼저** 담는다 — 잘 읽은 페이지는 점수가 설명하지만, 못 읽은
   응답은 아무것도 말해 주지 않는다.
2. 잘린 것을 **전부인 척하지 않는다.**
3. 쿠키·인증 헤더는 애초에 담지 않는다.
4. 보관이 실패해도 **진단은 죽지 않는다.**
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import FetchedDocument
from veo.scoring import ScoringSpec
from veo.seo.captures import KEPT_HEADERS, MAX_CAPTURE_BYTES, MAX_CAPTURES_PER_RUN, _row


def document(url: str, body: bytes, *, headers: dict[str, str] | None = None) -> FetchedDocument:
    return FetchedDocument(
        requested_url=url,
        final_url=url,
        status=200,
        headers=headers or {"content-type": "text/html"},
        body=body,
        content_hash="0" * 64,
        content_type="text/html",
        charset="utf-8",
        hops=(),
        resolved_ips=(),
        fetched_at=datetime.now(UTC),
        elapsed_ms=10,
        truncated=False,
        user_agent="VEO-Bot/1.0",
        request_headers={"user-agent": "VEO-Bot/1.0"},
        tls_expires_at=None,
    )


def capture(doc: FetchedDocument, reason: str | None = None):
    return _row(
        organization_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        document=doc,
        reason_ko=reason,
    )


class TestWeKeepWhatWeReceived:
    def test_the_body_is_kept_as_received(self) -> None:
        row = capture(document("https://x.example/", b"<html><title>x</title></html>"))

        assert bytes(row.body) == b"<html><title>x</title></html>"

    def test_a_large_body_is_cut_and_says_so(self) -> None:
        """잘린 것을 전부인 척하지 않는다."""
        big = b"a" * (MAX_CAPTURE_BYTES + 5_000)

        row = capture(document("https://x.example/", big))

        assert len(row.body) == MAX_CAPTURE_BYTES
        assert row.truncated is True
        # 원본이 얼마였는지는 남는다 — 그래야 얼마나 잘렸는지 안다.
        assert row.byte_size == len(big)

    def test_a_small_body_is_not_marked_truncated(self) -> None:
        row = capture(document("https://x.example/", b"<html></html>"))

        assert row.truncated is False

    def test_the_hash_is_of_the_whole_body_not_the_kept_part(self) -> None:
        """해시는 **받은 전부**의 것이어야 한다. 잘린 조각의 해시를 남기면, 나중에
        원본과 대조할 수 없다."""
        import hashlib

        big = b"b" * (MAX_CAPTURE_BYTES + 100)

        row = capture(document("https://x.example/", big))

        assert row.content_hash == hashlib.sha256(big).hexdigest()


class TestTheReasonTravelsWithIt:
    def test_an_unread_response_carries_why(self) -> None:
        row = capture(document("https://x.example/", b"<html></html>"), "봇 차단으로 보입니다.")

        assert row.read_failure_ko == "봇 차단으로 보입니다."

    def test_a_read_response_has_no_reason(self) -> None:
        assert capture(document("https://x.example/", b"<html></html>")).read_failure_ko is None


class TestSecretsAreNotKept:
    def test_cookies_never_reach_storage(self) -> None:
        """받은 헤더에 쿠키가 있어도 담지 않는다. 담을 헤더는 목록으로 정해 두고,
        목록에 없으면 버린다 — 새 헤더가 생겨도 자동으로 새어 나가지 않는다."""
        row = capture(
            document(
                "https://x.example/",
                b"<html></html>",
                headers={
                    "content-type": "text/html",
                    "set-cookie": "SESSION=secret-value",
                    "authorization": "Bearer secret",
                },
            )
        )

        assert "set-cookie" not in row.headers
        assert "authorization" not in row.headers
        assert row.headers["content-type"] == "text/html"
        assert "secret" not in str(row.headers)

    def test_the_kept_list_holds_no_credential_header(self) -> None:
        for name in KEPT_HEADERS:
            assert "cookie" not in name
            assert "auth" not in name


class TestOrdering:
    def test_unread_responses_come_first(self) -> None:
        """상한에 걸려도 **문제를 보여 주는 쪽**이 남아야 한다."""
        from veo.seo.captures import save_captures

        readable = {
            f"https://x.example/{i}": document(f"https://x.example/{i}", b"<html>ok</html>")
            for i in range(MAX_CAPTURES_PER_RUN + 5)
        }
        blocked = document("https://x.example/blocked", b"<html></html>")
        context = CollectionContext(
            target_url="https://x.example/",
            spec=ScoringSpec.model_construct(),
            documents=readable,
            primary_document=None,
            locale="ko-KR",
            collected_at=datetime.now(UTC),
            unread_documents=((blocked, "봇 차단으로 보입니다."),),
        )

        saved: list[object] = []

        class _Db:
            def execute(self, *_a: object, **_k: object) -> None: ...
            def add_all(self, rows: list[object]) -> None:
                saved.extend(rows)

            def flush(self) -> None: ...

        count = save_captures(
            _Db(),  # type: ignore[arg-type]
            organization_id=uuid.uuid4(),
            scan_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            context=context,
        )

        assert count == MAX_CAPTURES_PER_RUN
        assert saved[0].read_failure_ko == "봇 차단으로 보입니다."  # type: ignore[attr-defined]
