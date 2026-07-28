"""Offline doubles for the ``veo.common`` suite.

Lives in its own module (rather than in ``conftest.py``) so both the fixtures and the
test modules can import the corpus constants without a package-relative import.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from veo.common.security.url_guard import HostResolutionError

# Documentation / well-known addresses only. Nothing here is ever contacted.
PUBLIC_V4 = "93.184.216.34"
PUBLIC_V4_ALT = "23.192.228.80"
PUBLIC_V6 = "2606:2800:220:1:248:1893:25c8:1946"


class FakeResolver:
    """Deterministic stand-in for DNS.

    A zone value is either a sequence of address strings or an exception instance, which
    is raised to simulate SERVFAIL. Unknown hosts raise ``HostResolutionError``, so the
    default-deny path is exercised by omission rather than by explicit setup.
    """

    def __init__(self, zone: Mapping[str, Sequence[str] | BaseException]) -> None:
        self._zone = dict(zone)
        self.calls: list[str] = []

    def __call__(self, host: str) -> Sequence[str]:
        self.calls.append(host)
        try:
            answer = self._zone[host]
        except KeyError:
            raise HostResolutionError(f"no fake record for {host!r}") from None
        if isinstance(answer, BaseException):
            raise answer
        return list(answer)


ZONE: dict[str, Sequence[str] | BaseException] = {
    # --- public, safe to fetch --------------------------------------------------
    "example.com": [PUBLIC_V4],
    "www.example.com": [PUBLIC_V4, PUBLIC_V6],
    "hop-a.example.com": [PUBLIC_V4],
    "hop-b.example.com": [PUBLIC_V4_ALT],
    "xn--exmple-4nf.com": [PUBLIC_V4],  # homograph of example.com (Cyrillic U+0430)
    "xn--r8jz45g.xn--zckzah": [PUBLIC_V4],  # IDN sample host
    # --- resolve into blocked space ---------------------------------------------
    "localtest.me": ["127.0.0.1"],
    "internal.example.com": ["192.168.1.10"],
    "metadata.example.com": ["169.254.169.254"],
    "cgnat.example.com": ["100.64.0.1"],
    "v6-ula.example.com": ["fd00::1"],
    "v6-mapped.example.com": ["::ffff:127.0.0.1"],
    "v6-nat64.example.com": ["64:ff9b::7f00:1"],
    # --- the nasty one: public AND private in the same answer --------------------
    "dual.example.com": [PUBLIC_V4, "10.0.0.5"],
    "dual-reversed.example.com": ["10.0.0.5", PUBLIC_V4],
    # --- resolution problems -----------------------------------------------------
    "empty.example.com": [],
    "servfail.example.com": HostResolutionError("SERVFAIL"),
    "garbage.example.com": ["not-an-ip"],
}
