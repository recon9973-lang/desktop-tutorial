"""우리가 남의 서버에 밝히는 신원.

크롤러는 남의 서버에 요청을 보낸다. 그 서버 운영자가 우리를 **알아보고 거절할 수 있어야**
한다. 그러려면 세 가지가 맞물려야 한다.

1. User-Agent 가 우리를 밝힌다.
2. robots.txt 매칭에 쓰는 이름이 그 UA 의 토큰과 **같다.**
3. UA 가 가리키는 안내 페이지가 실제로 있다.

2026-08-06 실측에서 셋이 전부 어긋나 있었다:

    작업의뢰서 §5.2 요구      VEOBot/1.0
    실제 UA                   VEO-Bot/1.0 (하이픈)
    robots 매칭 이름          veo-bot
    안내 페이지               HTTP 404

거래처가 `User-agent: VEOBot` 으로 우리를 막아도 매칭 이름이 달라 **걸리지 않았다.**
남의 서버가 우리를 거절할 방법을 우리가 없애 놓은 상태였다.

두 값을 잇는 검사가 없어서 아무도 알아채지 못했다. 이 파일이 그 연결이다(0-H).
"""

from __future__ import annotations

import re

from veo.common.security.fetcher import CRAWLER_FROM, DEFAULT_USER_AGENT
from veo.seo.parsing.robots import CRAWLER_AGENT_NAME


def product_token(user_agent: str) -> str:
    """UA 의 앞머리 토큰. robots.txt 가 매칭하는 이름이 이것이다.

    `VEOBot/1.0 (+https://...)` → `VEOBot`
    """
    return re.split(r"[/\s]", user_agent.strip(), maxsplit=1)[0]


class TestTheNameIsOne:
    def test_robots_matching_uses_the_name_we_actually_present(self) -> None:
        """**이 시험이 이 결함의 본체다.** 둘이 갈리면 robots.txt 준수가 무너진다."""
        assert product_token(DEFAULT_USER_AGENT).lower() == CRAWLER_AGENT_NAME.lower()

    def test_the_token_has_no_separator(self) -> None:
        """`VEO-Bot` 처럼 구분자를 넣으면 `VEOBot` 그룹과 매칭되지 않는다.

        robots.txt 의 User-agent 매칭은 토큰 문자열 비교라, 하이픈 하나가 곧 다른 봇이다.
        """
        assert "-" not in product_token(DEFAULT_USER_AGENT)
        assert "_" not in product_token(DEFAULT_USER_AGENT)


class TestWeCanBeReached:
    def test_the_user_agent_points_at_the_guidance_page(self) -> None:
        """운영자가 로그에서 우리를 보고 찾아갈 곳이 UA 안에 있어야 한다."""
        assert "+https://veo.seokorea.org/bot" in DEFAULT_USER_AGENT

    def test_there_is_an_address_to_write_to(self) -> None:
        assert "@" in CRAWLER_FROM and CRAWLER_FROM.endswith("seokorea.org")


class TestWeDoNotPretendToBeSomeoneElse:
    def test_the_user_agent_names_no_other_crawler(self) -> None:
        """타사 봇 사칭은 절대 금지다(의뢰서 §5.2).

        실측에서 Googlebot UA 로는 거래처의 자바스크립트 검사가 면제됐다. 그 면제는
        사이트가 **구글에게** 준 것이고, 우리가 구글인 척하면 사이트 주인을 속이는 것이다.
        """
        lowered = DEFAULT_USER_AGENT.lower()
        for other in ("googlebot", "yeti", "bingbot", "gptbot", "claudebot", "mozilla"):
            assert other not in lowered, f"UA 에 {other} 가 들어 있다"
