"""Google adapters — PageSpeed Insights, the Chrome UX Report, and Search Console.

Four modules, and two of the separations between them are product rules rather than
tidiness:

* :mod:`veo.providers.google.pagespeed` — Lighthouse **lab** metrics. A simulation run in
  a controlled environment, on a network profile Google chose, for a form factor VEO asked
  for. It answers "what would a visitor on this kind of connection experience".
* :mod:`veo.providers.google.crux` — **field** data. Real Chrome users, aggregated over 28
  days, and only for URLs with enough traffic to be publishable. It answers "what did
  visitors actually experience". A URL with no sample is ``NOT_APPLICABLE`` — a fact about
  traffic volume, not a fault in the site.
* :mod:`veo.providers.google.search_console` — ownership, sitemaps, index coverage and the
  search performance series. Performance is an **outcome**, reported beside the readiness
  score and never folded into it: a site can be flawless and unvisited, or badly built and
  ranking on brand terms alone.
* :mod:`veo.providers.google.credentials` — where a credential comes from, and the three
  distinct ways there is not one.

``pagespeed`` imports ``crux`` and never the reverse, so the field vocabulary has exactly
one definition and a lab number has no route into a field-shaped structure.

The retry, circuit-breaking and ``UNKNOWN`` machinery is imported from
:mod:`veo.providers.naver.errors` rather than reimplemented. It is provider-agnostic in
everything but its module path; see ``INTEGRATION_REQUEST.md`` §1 for the rename that
would let it live somewhere honest.
"""

from __future__ import annotations
