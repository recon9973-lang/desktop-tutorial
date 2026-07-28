"""robots.txt, read with the one distinction that matters for GEO.

A crawler that fetches a page to answer somebody's question *now* and a crawler that
harvests text to train a model *later* are different agents doing different jobs. Turning
the first away costs a site its place in AI answers. Turning the second away is a
business decision about one's own content, and VEO records it without judging it.

The Python standard library ships ``urllib.robotparser``, which is not used here: it
answers "may this agent fetch this URL" for one agent at a time and discards which rule
decided, and the evidence for these checks has to name the matched directive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import unquote

#: Agents that fetch pages in order to answer a question now.
SEARCH_PURPOSE_CRAWLERS: frozenset[str] = frozenset(
    {
        "googlebot",
        "bingbot",
        "yeti",
        "daumoa",
        "applebot",
        "duckduckbot",
        "oai-searchbot",
        "chatgpt-user",
        "perplexitybot",
        "perplexity-user",
        "claude-searchbot",
        "claude-user",
        "bingpreview",
    }
)

#: Agents that collect text to train models. Disallowing these is never a fault.
TRAINING_PURPOSE_CRAWLERS: frozenset[str] = frozenset(
    {
        "gptbot",
        "google-extended",
        "ccbot",
        "anthropic-ai",
        "claudebot",
        "applebot-extended",
        "bytespider",
        "meta-externalagent",
        "facebookbot",
        "cohere-ai",
        "diffbot",
        "omgilibot",
        "timpibot",
        "pangubot",
    }
)


@dataclass(frozen=True, slots=True)
class Directive:
    """One ``Allow``/``Disallow`` line, kept so evidence can quote it."""

    allow: bool
    path: str

    @property
    def specificity(self) -> int:
        return len(self.path)

    def matches(self, path: str) -> bool:
        pattern = self.path
        if not pattern:
            return False
        if pattern == "/":
            return True
        if pattern.endswith("$"):
            return path == pattern[:-1]
        if "*" in pattern:
            head, _, tail = pattern.partition("*")
            return path.startswith(head) and tail in path[len(head) :]
        return path.startswith(pattern)

    def as_line(self) -> str:
        return f"{'Allow' if self.allow else 'Disallow'}: {self.path}"


@dataclass(frozen=True, slots=True)
class AgentGroup:
    agents: tuple[str, ...]
    directives: tuple[Directive, ...]


@dataclass(frozen=True, slots=True)
class RobotsPolicy:
    """A parsed robots.txt, queried per agent."""

    groups: tuple[AgentGroup, ...] = ()
    sitemaps: tuple[str, ...] = ()
    named_agents: frozenset[str] = field(default_factory=frozenset)

    # ------------------------------------------------------------------ #
    # Per-agent questions
    # ------------------------------------------------------------------ #

    def directives_for(self, agent: str) -> tuple[Directive, ...]:
        """The group that applies to ``agent``: its own if named, otherwise ``*``."""
        lowered = agent.lower()
        for group in self.groups:
            if lowered in group.agents:
                return group.directives
        for group in self.groups:
            if "*" in group.agents:
                return group.directives
        return ()

    def matched_directive(self, agent: str, path: str) -> Directive | None:
        """The directive that decides ``path``: longest match, Allow wins a tie."""
        candidates = [d for d in self.directives_for(agent) if d.matches(path)]
        if not candidates:
            return None
        return max(candidates, key=lambda d: (d.specificity, d.allow))

    def is_disallowed(self, agent: str, path: str) -> bool:
        directive = self.matched_directive(agent, path)
        return directive is not None and not directive.allow

    def blocked_search_agents(self, path: str) -> tuple[str, ...]:
        return tuple(
            sorted(a for a in SEARCH_PURPOSE_CRAWLERS if self.is_disallowed(a, path))
        )

    def blocked_training_agents(self, path: str) -> tuple[str, ...]:
        return tuple(
            sorted(a for a in TRAINING_PURPOSE_CRAWLERS if self.is_disallowed(a, path))
        )

    def declares_training_policy(self) -> bool:
        """True when the file names a training crawler at all — allowed or disallowed.

        Naming one is the signal that the choice was made on purpose. Which way it was
        made is the site owner's business.
        """
        return bool(self.named_agents & TRAINING_PURPOSE_CRAWLERS)

    def declared_training_agents(self) -> tuple[str, ...]:
        return tuple(sorted(self.named_agents & TRAINING_PURPOSE_CRAWLERS))


def parse_robots(text: str) -> RobotsPolicy:
    """Parse a robots.txt body. Unknown lines are ignored, as the protocol requires."""
    groups: list[AgentGroup] = []
    sitemaps: list[str] = []
    named: set[str] = set()

    pending_agents: list[str] = []
    directives: list[Directive] = []
    expecting_agents = True

    def close_group() -> None:
        if pending_agents:
            groups.append(AgentGroup(tuple(pending_agents), tuple(directives)))

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            if not expecting_agents:
                close_group()
                pending_agents = []
                directives = []
                expecting_agents = True
            agent = value.lower()
            pending_agents.append(agent)
            if agent != "*":
                named.add(agent)
        elif key in {"allow", "disallow"}:
            expecting_agents = False
            directives.append(Directive(allow=key == "allow", path=unquote(value)))
        elif key == "sitemap":
            sitemaps.append(value)

    close_group()
    return RobotsPolicy(
        groups=tuple(groups), sitemaps=tuple(sitemaps), named_agents=frozenset(named)
    )


__all__ = [
    "SEARCH_PURPOSE_CRAWLERS",
    "TRAINING_PURPOSE_CRAWLERS",
    "AgentGroup",
    "Directive",
    "RobotsPolicy",
    "parse_robots",
]
