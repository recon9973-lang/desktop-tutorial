"""표준 `logging` 으로 찍은 줄도 설정을 거치는가.

## 왜 이 파일이 따로 있나

`observability/logging.py` 의 첫 문단은 "내보내는 줄이 지켜야 할 경계" 라고 선언한다.
그런데 그 경계는 **스물세 곳 중 한 곳에만** 서 있었다(실측 2026-08-06):

    logging.getLogger 를 쓰는 모듈   22개
    get_logger(structlog) 를 쓰는 모듈  1개

`configure_logging()` 이 structlog 만 설정했기 때문에, 22개 모듈의 줄은 파이썬의
``lastResort`` 핸들러로 떨어졌다. 그 핸들러의 성질 둘이 문제였다.

1. **WARNING 이상만 낸다.** 코드베이스의 모든 `logger.info` 가 운영에서 안 보였다.
   v0.3.56 이 "일감이 워커로 갔는지" 알라고 넣은 `job %s queued on %s` 가 한 줄도
   안 나온 것이 이 때문이다 — 큐가 실패해서가 아니었다.
2. **원문을 그대로 쓴다.** 허용 목록도, 스크러버도 안 거친다. 그래서 출력되던 절반이
   하필 비밀값을 실어 나를 확률이 가장 높은 절반이었다 — `jobs/execution.py` 의
   `logger.exception` 은 공급자 예외의 트레이스백을 그대로 낸다.

시험이 이걸 못 잡은 이유는 단순하다. **structlog 경로만 시험했다.**
"막았다" 고 적힌 규칙에는 그것을 확인하는 시험이 붙어야 한다(0-H).
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator

import pytest

from veo.observability.logging import REDACTED, configure_logging

#: 스크러버가 잡아야 하는 모양들. 값 자체는 이 파일이 만든 가짜다.
BEARER = "Bearer abcdefghijklmnopqrstuvwxyz012345"
OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz"
DSN = "postgresql://someuser:supersecretpassword@db.example/veo"


@pytest.fixture
def emitted() -> Iterator[io.StringIO]:
    """설정을 이 시험 전용 스트림으로 걸고, 끝나면 표준 logging 을 원상복구한다."""
    stream = io.StringIO()
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    configure_logging(json_output=True, level="INFO", stream=stream)
    try:
        yield stream
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_level)


def _lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


class TestTheStandardLibraryPathIsConfiguredAtAll:
    def test_an_info_line_is_emitted(self, emitted: io.StringIO) -> None:
        """이것이 깨져 있던 자리다 — `lastResort` 는 INFO 를 버린다."""
        logging.getLogger("veo.jobs.dispatch").info("job %s queued on %s", "abc", "seo")

        lines = _lines(emitted)

        assert lines, "표준 logging 의 INFO 가 아무 데도 안 나왔다"
        assert "queued on seo" in lines[0]["event"]

    def test_debug_is_still_filtered_at_info(self, emitted: io.StringIO) -> None:
        """전부 열어 버리면 그것대로 문제다 — 정한 등급은 지킨다."""
        logging.getLogger("veo.somewhere").debug("noisy")

        assert _lines(emitted) == []

    def test_the_line_carries_the_level(self, emitted: io.StringIO) -> None:
        logging.getLogger("veo.somewhere").warning("something")

        assert _lines(emitted)[0]["level"] == "warning"


class TestNothingSkipsTheScrubber:
    """등급으로 봐주지 않는다 — 이 모듈의 첫 문단이 그렇게 적혀 있다."""

    @pytest.mark.parametrize("secret", [BEARER, OPENAI_KEY, DSN])
    def test_a_secret_in_the_message_is_redacted(
        self, emitted: io.StringIO, secret: str
    ) -> None:
        logging.getLogger("veo.notify.webhook").warning("보내지 못했습니다: %s", secret)

        rendered = emitted.getvalue()

        assert secret not in rendered
        assert REDACTED in rendered

    def test_a_traceback_is_redacted(self, emitted: io.StringIO) -> None:
        """`jobs/execution.py` 가 실제로 하는 일이다 — 공급자 예외를 통째로 찍는다.

        예전에는 이 트레이스백이 스크러버를 한 번도 안 거치고 나갔다.
        """
        try:
            raise RuntimeError(f"provider refused: {OPENAI_KEY}")
        except RuntimeError:
            logging.getLogger("veo.jobs.execution").exception("job %s raised", "abc")

        rendered = emitted.getvalue()

        assert "Traceback" in rendered, "트레이스백이 아예 안 실렸다"
        assert OPENAI_KEY not in rendered
        assert REDACTED in rendered

    def test_an_unreviewed_field_is_dropped_by_name(self, emitted: io.StringIO) -> None:
        """허용 목록 밖의 칸은 값이 아니라 **이름만** 남는다 — structlog 경로와 같다."""
        logging.getLogger("veo.somewhere").warning(
            "무언가", extra={"password": "hunter2"}
        )

        rendered = emitted.getvalue()

        assert "hunter2" not in rendered


class TestConfiguringTwiceDoesNotDoubleEverything:
    def test_one_line_stays_one_line(self, emitted: io.StringIO) -> None:
        configure_logging(json_output=True, level="INFO", stream=emitted)

        logging.getLogger("veo.somewhere").warning("한 번만")

        assert len(_lines(emitted)) == 1
