"""Reading a provider response under a byte ceiling.

Four provider packages each grew their own copy of this — Google, Naver Search Ad, Naver
DataLab and the answer engines — because four people wrote them in parallel, each inside
their own directory, each correctly refusing to reach into somebody else's. The copies
were identical apart from the exception they raise.

Duplication of ordinary code is untidy. Duplication of a *safety control* is worse: this
is the thing that stops a hostile or broken provider from handing VEO a body large enough
to exhaust its memory, and four copies mean four places to correct when the rule changes
and one that will be missed. The exception type is the only part that legitimately
differs, so it is the only part that stays a parameter.
"""

from __future__ import annotations

from typing import TypeVar

import httpx

__all__ = ["read_capped"]

_E = TypeVar("_E", bound=Exception)


def read_capped(
    response: httpx.Response, max_bytes: int, too_large: type[Exception]
) -> bytes:
    """Return the body, raising ``too_large`` if it exceeds ``max_bytes``.

    The ceiling is enforced **while the body arrives**, not after. Reading first and
    checking afterwards would mean an oversized response is already in memory by the time
    it is refused, which is the failure this exists to prevent.

    A test double built from a bytes literal is already materialised and cannot be
    streamed; ``httpx`` reports that as :class:`httpx.StreamConsumed`. That path still
    charges the whole body against the same ceiling, so a fixture cannot pass a size a
    real response would not.
    """
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise too_large(f"over {max_bytes} bytes")
            chunks.append(chunk)
    except httpx.StreamConsumed:
        body = response.content
        if len(body) > max_bytes:
            raise too_large(f"over {max_bytes} bytes") from None
        return body
    return b"".join(chunks)
