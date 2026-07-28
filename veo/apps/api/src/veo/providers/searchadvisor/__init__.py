"""네이버 서치어드바이저 adapter.

One module, and most of it is an honest account of what does not exist.

Naver Search Advisor publishes **no public API** for site registration state, ownership
verification, crawl statistics, sitemap processing or index status. Those are read by a
person in a browser session, and no amount of wanting turns that into an endpoint. What
*is* documented and callable is IndexNow submission, which Naver supports at its own
endpoint.

So this package does two things and refuses a third:

* implements IndexNow submission the way every other VEO adapter behaves — typed errors,
  fixed customer-safe Korean messages, no key means no connection;
* returns an explicit ``NOT_AVAILABLE`` with a Korean explanation, and a note on what a
  human can do instead, for every capability Naver does not expose;
* does **not** ship a plausible-looking client for the surfaces that do not exist. A fake
  client is worse than no client, because a fake one gets believed.

The error, retry and circuit-breaking machinery is imported from
:mod:`veo.providers.naver.errors` — the same provider, so the Korean text there is already
the right Korean text.
"""

from __future__ import annotations
