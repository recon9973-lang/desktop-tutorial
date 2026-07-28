"""The rule that everything else in this directory is built around.

VEO's job is to fetch other people's websites. A load test is, by construction, a lot of
requests as fast as the machine can make them. Point those two things at each other and
the load test is a denial-of-service attack on somebody's clinic homepage — one that
VEO's own IP address is attached to.

So: no target outside this machine, ever. Every scenario that takes a URL passes it
through :func:`assert_local_target` first, and the check is a refusal, not a warning.
There is deliberately no override flag. If a scenario genuinely needs a remote endpoint,
that is a conversation to have, not an environment variable to set.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

__all__ = ["LoadTargetRefused", "assert_local_target", "is_local_host"]

#: Hostnames that resolve to this machine by definition and need no DNS lookup.
_LOOPBACK_NAMES = frozenset({"localhost", "localhost.localdomain", "ip6-localhost"})


class LoadTargetRefused(Exception):
    """A scenario asked for a target that is not on this machine."""


def is_local_host(host: str | None) -> bool:
    """True only for loopback. Not "private", not "internal" — loopback.

    A private-range address is still somebody else's machine: a colleague's laptop, a
    shared staging box, a router's admin page. The point of a load fixture is that the
    only thing that can be harmed is this process.
    """
    if not host:
        return False
    cleaned = host.strip().strip("[]").lower()
    if cleaned in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(cleaned).is_loopback
    except ValueError:
        # A name that is not a literal address would need DNS to resolve, and a name
        # that resolves to loopback today can resolve elsewhere tomorrow. Refuse.
        return False


def assert_local_target(url: str) -> str:
    """Return ``url`` unchanged, or refuse it.

    Refusals are loud and specific because the person who hits this is usually about to
    do real damage by accident.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise LoadTargetRefused(
            f"load targets must be http or https, got {parsed.scheme!r}: {url}"
        )
    if not is_local_host(parsed.hostname):
        raise LoadTargetRefused(
            f"refusing to load-test {parsed.hostname!r}.\n"
            "VEO's crawler fetches third-party sites; a load run pointed at a real host "
            "is an attack on that host, made from this network with this machine's "
            "address on it.\n"
            "Use the bundled fixture site (infra/load/fixture_site.py) or another "
            "loopback target."
        )
    return url
