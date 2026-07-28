"""Issue identity: the same problem across two scans is one issue, not two rows.

An issue is identified by *what is wrong* and *where*: the ``check_id`` from the
specification, plus the set of affected URLs reduced to canonical form. Nothing about a
particular scan enters the fingerprint — not the run id, not the timestamp, not the
evidence hashes — because the whole point is that Friday's finding recognises Monday's.

Get this wrong in either direction and the product loses the ability it exists for:

* Too *narrow* a fingerprint (say, one that includes the evidence hash) and every scan
  mints a fresh row. Recurrence tracking then reports zero recurrences forever, and the
  history that would let someone say "this is the third time" never accumulates.
* Too *wide* a fingerprint (say, ``check_id`` alone) and two genuinely different
  problems — a missing canonical tag on the blog and on the shop — merge into one row
  that can never be resolved, because fixing half of it changes nothing.

The canonical form comes from :mod:`veo.common.urls`, the same normaliser the crawler
uses, so an issue's URLs collapse exactly the way the crawl frontier's did.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from veo.collect.contract import IssueDraft
from veo.common.urls import UrlNormalizationError, canonical_url

#: Bumping this changes every fingerprint, which orphans existing issue history. It is
#: here so that such a change has to be deliberate and dated rather than accidental.
FINGERPRINT_VERSION = "1"

#: Field separator inside the hashed payload. A record separator that cannot appear in a
#: canonical URL or a check id is what stops ``("ab", ["c"])`` and ``("a", ["bc"])``
#: hashing alike.
_FIELD = "\x1f"
_RECORD = "\x1e"


def normalize_url_for_identity(raw: str) -> str | None:
    """One URL in the form used for comparison, or ``None`` if it is not a URL at all.

    A URL that cannot be canonicalised — userinfo present, a percent sign in the host,
    an obfuscated address — is returned *verbatim* rather than dropped. Dropping it would
    let two different problems share a fingerprint, and silently rewriting it would be
    worse; keeping the original string at least stays stable across scans.
    """
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        return canonical_url(stripped)
    except UrlNormalizationError:
        return stripped


def normalize_affected_urls(urls: Iterable[str]) -> tuple[str, ...]:
    """The affected URL set: canonical, de-duplicated and sorted.

    Sorting is what makes the set an actual set. Two collectors that visit the same pages
    in a different order must produce the same identity, or the ordering of a crawl would
    silently become part of what a problem *is*.
    """
    seen: set[str] = set()
    for raw in urls:
        normalized = normalize_url_for_identity(raw)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
    return tuple(sorted(seen))


def issue_fingerprint(check_id: str, affected_urls: Iterable[str]) -> str:
    """A stable SHA-256 fingerprint of ``(check_id, normalised affected URL set)``."""
    identifier = check_id.strip()
    if not identifier:
        raise ValueError("check_id 없이는 이슈 지문을 만들 수 없습니다.")

    urls = normalize_affected_urls(affected_urls)
    payload = _RECORD.join(
        (FINGERPRINT_VERSION, identifier, _FIELD.join(urls))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_of_draft(draft: IssueDraft) -> str:
    """The fingerprint of a finding a collector just proposed."""
    return issue_fingerprint(draft.check_id, draft.affected_urls)


__all__ = [
    "FINGERPRINT_VERSION",
    "fingerprint_of_draft",
    "issue_fingerprint",
    "normalize_affected_urls",
    "normalize_url_for_identity",
]
