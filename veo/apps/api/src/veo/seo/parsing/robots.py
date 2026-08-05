"""``robots.txt`` with the grouping and precedence rules search engines actually apply.

Getting this wrong in either direction is expensive. Reporting a crawlable URL as
blocked sends a customer chasing a rule that is not stopping anything; reporting a
blocked URL as crawlable hides the single most damaging fault a site can have. So the
rules below follow RFC 9309 rather than intuition:

* Consecutive ``User-agent`` lines introduce **one** group. A ``Disallow`` after two
  agent lines belongs to both.
* Exactly one group applies to a given crawler: the most specific matching name. The
  ``*`` group is a fallback and is used only when no name matches.
* Within that group the **longest matching pattern** wins. Length ties go to ``Allow``.
* ``*`` matches any run of characters and a trailing ``$`` anchors the end of the path.
* ``Disallow:`` with an empty value is not a rule; it allows everything.
* Paths are matched case-sensitively; agent names are not.
* ``Sitemap`` is a file-level directive and belongs to no group.

Every decision carries the line that produced it, because "blocked" without a quotable
rule is an assertion nobody can act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: The product token VEO's crawler presents. Naver's crawler is ``Yeti``; a Korean site
#: frequently has a group for it that differs from the wildcard group, which is exactly
#: why the group selection below has to be right.
#:
#: **이 값은 우리가 실제로 보내는 User-Agent 의 토큰과 같아야 한다.** 2026-08-06 실측:
#: UA 는 `VEO-Bot/1.0`(하이픈), 이 값은 `veo-bot`, 작업의뢰서 §5.2 의 요구는 `VEOBot/1.0`
#: — 셋이 전부 달랐다. 거래처가 `User-agent: VEOBot` 으로 우리를 막아도 매칭이 안 돼
#: **robots.txt 준수가 이름 불일치로 무너지는** 상태였다. 남의 서버가 우리를 거절할
#: 방법을 우리가 없애 놓은 셈이다.
#:
#: 두 값을 잇는 검사가 없어서 아무도 알아채지 못했다. `tests/seo/test_robots.py` 가
#: 이제 그 연결을 고정한다(0-H).
CRAWLER_AGENT_NAME = "veobot"

#: 보고서가 이야기하는 검색엔진들. robots.txt 판정은 **이들 기준**으로 한다.
#:
#: `veo-bot` 이 들어갈 수 있는지는 우리 수집의 문제이지 고객 사이트의 상태가 아니다.
#: `Yeti` 는 네이버 크롤러이고, 국내 병원 고객에게는 Googlebot 만큼, 흔히 그보다 중요하다.
REPORTED_CRAWLERS: tuple[str, ...] = ("Googlebot", "Yeti")

#: 사람에게 보여줄 이름.
CRAWLER_LABELS_KO: dict[str, str] = {"Googlebot": "구글(Googlebot)", "Yeti": "네이버(Yeti)"}


@dataclass(frozen=True, slots=True)
class RobotsRule:
    allow: bool
    pattern: str
    line_number: int

    @property
    def directive(self) -> str:
        return f"{'Allow' if self.allow else 'Disallow'}: {self.pattern}"

    @property
    def specificity(self) -> int:
        return len(self.pattern)


@dataclass(frozen=True, slots=True)
class RobotsGroup:
    agents: tuple[str, ...]
    rules: tuple[RobotsRule, ...]

    def matches(self, user_agent: str) -> int | None:
        """Length of the most specific agent token this group matches, or ``None``.

        A longer token is a more specific claim on the crawler, which is how a group for
        ``Yeti`` beats a group for ``*``.
        """
        lowered = user_agent.lower()
        best: int | None = None
        for agent in self.agents:
            if agent == "*":
                candidate = 0
            elif agent in lowered:
                candidate = len(agent)
            else:
                continue
            if best is None or candidate > best:
                best = candidate
        return best


@dataclass(frozen=True, slots=True)
class RobotsDecision:
    allowed: bool
    matched_rule: str | None
    line_number: int | None
    group_agents: tuple[str, ...]
    reason_ko: str


@dataclass(frozen=True, slots=True)
class RobotsFile:
    groups: tuple[RobotsGroup, ...] = ()
    sitemaps: tuple[str, ...] = ()
    raw: str = ""
    malformed_lines: tuple[int, ...] = field(default=())

    def group_for(self, user_agent: str) -> RobotsGroup | None:
        best: RobotsGroup | None = None
        best_match_length = -1
        for group in self.groups:
            match_length = group.matches(user_agent)
            if match_length is None or match_length <= best_match_length:
                continue
            best, best_match_length = group, match_length
        return best

    def decide(self, path: str, *, user_agent: str = CRAWLER_AGENT_NAME) -> RobotsDecision:
        """Whether ``path`` may be crawled, and which line decided it."""
        group = self.group_for(user_agent)
        if group is None:
            return RobotsDecision(
                allowed=True,
                matched_rule=None,
                line_number=None,
                group_agents=(),
                reason_ko="이 크롤러에 적용되는 그룹이 robots.txt에 없어 크롤링이 허용됩니다.",
            )

        winner: RobotsRule | None = None
        for rule in group.rules:
            if not _pattern_matches(rule.pattern, path):
                continue
            if winner is None:
                winner = rule
                continue
            longer = rule.specificity > winner.specificity
            tie_broken_by_allow = (
                rule.specificity == winner.specificity and rule.allow and not winner.allow
            )
            if longer or tie_broken_by_allow:
                winner = rule

        if winner is None:
            return RobotsDecision(
                allowed=True,
                matched_rule=None,
                line_number=None,
                group_agents=group.agents,
                reason_ko="일치하는 규칙이 없어 기본값인 허용이 적용됩니다.",
            )

        reason = (
            f"{winner.directive} 규칙이 이 경로와 일치해 "
            f"{'허용' if winner.allow else '차단'}되었습니다."
        )
        return RobotsDecision(
            allowed=winner.allow,
            matched_rule=winner.directive,
            line_number=winner.line_number,
            group_agents=group.agents,
            reason_ko=reason,
        )


def parse_robots(text: str) -> RobotsFile:
    """Parse a ``robots.txt`` body. Malformed lines are skipped, never fatal."""
    groups: list[RobotsGroup] = []
    sitemaps: list[str] = []
    malformed: list[int] = []

    agents: list[str] = []
    rules: list[RobotsRule] = []
    expecting_agents = False

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append(RobotsGroup(agents=tuple(agents), rules=tuple(rules)))
        agents, rules = [], []

    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        field_name, separator, value = line.partition(":")
        if not separator:
            malformed.append(number)
            continue
        key = field_name.strip().lower()
        value = value.strip()

        if key == "user-agent":
            if not expecting_agents:
                flush()
                expecting_agents = True
            if value:
                agents.append(value.lower())
            continue

        expecting_agents = False
        if key in {"allow", "disallow"}:
            if key == "disallow" and not value:
                # An empty Disallow is the documented way to say "nothing is blocked".
                continue
            if not value:
                continue
            rules.append(RobotsRule(allow=key == "allow", pattern=value, line_number=number))
        elif key == "sitemap" and value:
            sitemaps.append(value)

    flush()

    return RobotsFile(
        groups=tuple(groups),
        sitemaps=tuple(sitemaps),
        raw=text,
        malformed_lines=tuple(malformed),
    )


def _pattern_matches(pattern: str, path: str) -> bool:
    """Match a robots path pattern, honouring ``*`` and a trailing ``$``."""
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "".join(".*" if char == "*" else re.escape(char) for char in body)
    compiled = re.compile("^" + regex + ("$" if anchored else ""))
    return compiled.match(path) is not None


__all__ = [
    "CRAWLER_AGENT_NAME",
    "RobotsDecision",
    "RobotsFile",
    "RobotsGroup",
    "RobotsRule",
    "parse_robots",
]
