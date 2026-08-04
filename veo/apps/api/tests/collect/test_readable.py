"""응답을 우리가 실제로 읽었는가 (0-K).

2026-08-04, venomad.com 진단이 15~27점으로 나왔다. 운영 서버는 HTTP 200 을 받았고
`status_ok` 는 통과했는데, 본문에 title·h1·viewport·canonical 이 하나도 없었다. 엔진은
그것을 수집 실패로 보고하지 않고 **11개 항목을 FAIL 로 채점**해 고객에게 보냈다.
같은 주소를 다른 곳에서 받으면 그 값들이 전부 멀쩡히 있었다.

여기서 지키는 것 둘:
1. 못 받은 응답으로는 **어떤 "없음" 도 확정하지 않는다.**
2. 진짜로 부실한 페이지는 **걸러지지 않고 채점된다** — 그것이 이 제품이 파는 값이다.

두 번째가 없으면 이 관문은 "나쁜 사이트를 못 재는 도구" 를 만든다. 그래서 문턱을
일부러 낮게 잡았고, 아래 시험 절반이 그 낮은 문턱을 지킨다.
"""

from __future__ import annotations

from veo.collect.readable import MIN_DOCUMENT_BYTES, read_failure


def judge(**overrides: object) -> object:
    """읽힌 정상 문서를 기본값으로 두고, 시험이 한 가지씩 무너뜨린다."""
    values: dict[str, object] = {
        "url": "https://ok.example/",
        "status": 200,
        "body_length": 5_000,
        "has_html_root": True,
        "has_any_head_signal": True,
        "body_text_length": 800,
    }
    values.update(overrides)
    return read_failure(**values)  # type: ignore[arg-type]


class TestWhatWeCouldNotRead:
    """알맹이가 **하나도 없을 때만** 못 읽은 것으로 본다.

    처음에는 크기를 앞세워 걸렀는데, 그것이 제목·h1·lang 을 갖춘 80바이트짜리 정상
    문서를 버렸다(GEO 시험이 잡았다). 그래서 아래 시험들은 크기뿐 아니라 **알맹이가
    없다는 것까지** 명시한다 — 크기만 작다는 이유로는 더 이상 걸리지 않는다.
    """

    def test_a_blocked_shell_is_not_a_site_without_a_title(self) -> None:
        """봇 차단 페이지: 200 이고 HTML 구조도 있지만 알맹이가 없다."""
        failure = judge(has_any_head_signal=False, body_text_length=0)

        assert failure is not None
        assert "받지 못한" in failure.reason_ko  # type: ignore[union-attr]

    def test_an_empty_body_is_a_collection_failure(self) -> None:
        failure = judge(body_length=0, has_any_head_signal=False, body_text_length=0)

        assert failure is not None
        assert "0바이트" in failure.reason_ko  # type: ignore[union-attr]

    def test_a_non_2xx_body_is_not_that_page(self) -> None:
        """오류 페이지의 본문은 그 주소의 내용이 아니다. `status_ok` 와는 다른 판단이다 —
        저것은 사이트의 사실이고, 이것은 '이 바이트로 채점해도 되는가' 다."""
        assert judge(status=503) is not None

    def test_something_that_is_not_html_is_not_a_document(self) -> None:
        assert (
            judge(has_html_root=False, has_any_head_signal=False, body_text_length=0)
            is not None
        )

    def test_the_reason_blames_the_collection_not_the_site(self) -> None:
        """사유 문장이 사이트 탓으로 읽히면 안 된다(0-J)."""
        failure = judge(body_length=10, has_any_head_signal=False, body_text_length=0)

        assert failure is not None
        assert "서버가 응답은 했지만" in failure.reason_ko  # type: ignore[union-attr]


class TestWhatMustStillBeScored:
    """진짜로 부실한 페이지를 수집 실패로 오인하면, 이 관문이 제품을 망가뜨린다."""

    def test_a_page_with_only_a_title_is_still_scored(self) -> None:
        # 제목만 있고 본문이 비어 있는 페이지 — 실제로 얇은 페이지다. 채점되어야 한다.
        assert judge(has_any_head_signal=True, body_text_length=0) is None

    def test_a_page_with_only_body_text_is_still_scored(self) -> None:
        # head 가 전부 비었지만 본문은 있다 — 제목 없는 진짜 결함이다. 채점되어야 한다.
        assert judge(has_any_head_signal=False, body_text_length=400) is None

    def test_a_small_but_real_document_is_scored(self) -> None:
        assert judge(body_length=MIN_DOCUMENT_BYTES) is None

    def test_a_tiny_document_with_real_content_is_scored(self) -> None:
        """80바이트짜리 정상 문서를 버렸던 결함.

        `<html lang='ko'><head><title>클리닉</title></head><body><h1>소개</h1></body></html>`
        — 제목도 h1 도 lang 도 있는 진짜 문서인데, 처음 만든 관문이 크기를 앞세워
        걸렀다. GEO 시험이 잡았다. 크기는 알맹이의 대리 지표일 뿐이고, 알맹이를 직접
        볼 수 있는 자리에서 대리 지표로 판단할 이유가 없다.
        """
        assert judge(body_length=80, has_any_head_signal=True, body_text_length=2) is None

    def test_size_never_overrides_real_content(self) -> None:
        """본문 글자만 있어도(제목이 없어도) 읽은 것이다."""
        assert judge(body_length=50, has_any_head_signal=False, body_text_length=10) is None

    def test_a_normal_page_passes(self) -> None:
        assert judge() is None
