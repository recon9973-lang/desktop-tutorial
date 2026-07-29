"""robots.txt 가 깨져 있으면 알려 준다.

검수에서 나온 것: robots.txt 에 문법이 어긋난 줄이 있어도 점수가 정상과 같았다.
파싱 불가한 줄을 건너뛰는 것은 구글도 하는 일이라 판정 자체는 맞지만, 그래서 고객은
**자기 robots.txt 가 망가져 있다는 사실을 영영 모른다.**

건너뛴 줄이 `Disallow: /admin` 을 의도한 것이었다면 의도한 차단이 걸리지 않은 것이고,
`Sitemap:` 을 의도한 것이었다면 사이트맵이 전달되지 않은 것이다. 어느 쪽이든 운영자가
믿고 있는 상태와 실제가 다르다.

감점은 경미로 둔다 — 크롤링을 막는 것이 아니라 의도가 전달되지 않는 문제이고, 실제로
무엇이 막혔는지는 다른 항목이 따로 판정한다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, issues_for

from veo.scoring import CheckStatus
from veo.seo.collectors import CrawlIndexabilityCollector

COLLECTOR = CrawlIndexabilityCollector()
CHECK = "seo.robots.txt_parses_cleanly"


def run(robots: str | None):
    context = build_context("healthy")
    return COLLECTOR.collect(dataclasses.replace(context, robots_txt=robots))


class TestACleanFile:
    def test_a_well_formed_robots_passes(self) -> None:
        assert by_id(run("User-agent: *\nAllow: /\nSitemap: https://a.kr/s.xml"))[
            CHECK
        ].status is CheckStatus.PASS

    def test_comments_and_blank_lines_are_not_faults(self) -> None:
        text = "# 주석입니다\n\nUser-agent: *\n\n  \nDisallow: /admin  # 뒤 주석\n"
        assert by_id(run(text))[CHECK].status is CheckStatus.PASS

    def test_an_empty_file_is_clean(self) -> None:
        """빈 robots.txt 는 '아무것도 막지 않는다' 는 뜻이지 고장이 아니다."""
        assert by_id(run(""))[CHECK].status is CheckStatus.PASS


class TestABrokenFile:
    def test_a_line_without_a_colon_is_reported(self) -> None:
        text = "User-agent: *\nDisallow /admin\nAllow: /\n"

        assert by_id(run(text))[CHECK].status is CheckStatus.WARNING

    def test_the_line_number_is_named(self) -> None:
        """"어딘가 깨졌습니다" 로는 고칠 수 없다. 몇 번째 줄인지 말해야 한다."""
        text = "User-agent: *\nDisallow /admin\nAllow: /\n"

        outcome = by_id(run(text))[CHECK]
        assert "2" in (outcome.note or "")

    def test_the_broken_line_content_is_shown(self) -> None:
        outcome = by_id(run("User-agent: *\nDisallow /admin\n"))[CHECK]

        assert "Disallow /admin" in str(outcome.observed_value)

    def test_a_file_that_is_not_robots_at_all_is_reported(self) -> None:
        assert by_id(run("!!! 이건 robots.txt 가 아닙니다 @@@"))[CHECK].status is (
            CheckStatus.WARNING
        )

    def test_the_issue_says_what_the_skipped_line_would_have_done(self) -> None:
        drafts = issues_for(run("User-agent: *\nDisallow /admin\n"), CHECK)

        assert drafts
        assert drafts[0].remediation_ko
        assert drafts[0].business_impact_ko


class TestNoFileAtAll:
    def test_a_missing_robots_is_not_a_broken_robots(self) -> None:
        """robots.txt 가 없는 것은 전부 허용한다는 뜻이다. 없는 결함을 지어내지 않는다."""
        assert by_id(run(None))[CHECK].status is CheckStatus.NOT_APPLICABLE
