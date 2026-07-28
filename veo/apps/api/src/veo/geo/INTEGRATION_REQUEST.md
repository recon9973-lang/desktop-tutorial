# GEO readiness — integration requests

Everything below needs a file this worker does not own. Nothing here blocks the engine:
the package is complete and its tests pass without any of it. Each item says what is
degraded until it lands.

---

## 1. Mount the router — `veo/api/app.py`

`veo.geo.router.router` is an `APIRouter` with prefix `/geo` and tag `geo`. It is not
mounted, and `tests/geo/test_router.py::test_the_router_is_not_mounted_by_the_application`
asserts that it stays unmounted until you do it deliberately.

```python
from veo.geo.router import router as geo_router
application.include_router(geo_router, prefix=API_PREFIX)
```

Endpoints and permissions:

| method | path | permission |
|---|---|---|
| `GET` | `/geo/readiness/spec` | `Permission.SCAN_READ` |
| `POST` | `/geo/readiness/analyses` | `Permission.SCAN_RUN` |

No new permission is needed — both already exist in the matrix and are held by the roles
that should have them. `openapi.json` will need regenerating after mounting.

**Until then:** the engine is reachable only through `veo.geo.service.run_geo_readiness`.

---

## 2. First-class content history on `CollectionContext` — `veo/collect/contract.py`

`geo.fresh.dates_truthful` is the check that catches a `dateModified` moving while the
page's bytes stay identical. It needs, per URL, what that URL previously said and what it
previously hashed to. `CollectionContext` has nowhere to put that, so the collector reads
it from `provider_payloads["content_history"]` and requires
`provider_states["content_history"] == ENABLED`.

That works, but it files real crawl history under "provider payload", which it is not —
it is VEO's own prior observation. Requested shape:

```python
@dataclass(frozen=True, slots=True)
class PriorObservation:
    url: str
    observed_at: datetime
    content_hash: str
    declared_modified: str | None

# on CollectionContext
prior_observations: Mapping[str, tuple[PriorObservation, ...]] = field(default_factory=dict)
```

`veo/geo/collectors/freshness_signals.py` reads the current shape in exactly one place
(`_history_for`) and would move over in a few lines.

**Until then:** on a first scan, and on any scan without the provider, the check reports
`UNKNOWN` with a reason. It costs no points and lowers coverage, which is the correct
behaviour — but it means the check never fires for customers whose history VEO already
holds in `score_results`.

---

## 3. Provider vocabulary — wherever provider names are registered

Three provider keys are read by this package. They need to exist in whatever registry
`ProviderState` is populated from, so an operator can see them as configured or not:

| key | supplies | checks that go UNKNOWN without it |
|---|---|---|
| `geo_external` | outside corroboration: registries, directories, press, reviews | all four `geo.external.*` |
| `official_records` | the authoritative name / address / telephone for the business | `geo.entity.nap_consistent` (falls back to page-vs-schema comparison at lower confidence) |
| `content_history` | see item 2 | `geo.fresh.dates_truthful` |

Payload contract for `geo_external`:

```json
{
  "entity_name": "온담치과의원",
  "sources": [
    {
      "url": "https://…",
      "source_type": "DIRECTORY | OFFICIAL_REGISTRY | NEWS | REVIEW | SOCIAL | ACADEMIC",
      "independent": true,
      "claimed_profile": true,
      "facts": { "name": "…", "telephone": "…", "address": "…" }
    }
  ]
}
```

`independent` means "not a channel the business itself publishes". `claimed_profile`
means "the business controls this listing". Both are the provider's judgement, and the
outcomes carry `EXTERNAL_ESTIMATE` confidence accordingly.

**Until then:** five of the 37 checks report `UNKNOWN` on a scan with no providers wired.

---

## 4. Dependencies — nothing requested

`lxml` and `beautifulsoup4` are **not** installed here, and this package does not ask for
them. `veo/geo/parsing.py` is built on `html.parser` and `json` from the standard library
and handles the fixture corpus, including malformed JSON-LD and unclosed tags.

If a future check needs real CSS selectors or XPath, that is the point to raise a
dependency request — not before.

---

## 5. Golden fixtures — `packages/scoring-specs/golden/` (VEO-LAB)

`geo-01-all-pass`, `geo-02-noindex-gate` and `geo-03-no-schema-online-only` already pin
the evaluator's behaviour. One more would be worth having, and it belongs to VEO-LAB
rather than to this worker because it is a statement about the methodology:

> **`geo-04-training-crawler-blocked`** — identical to `geo-01-all-pass` except
> `geo.access.training_bot_policy_declared` is `WARNING` instead of `PASS`, with the
> expected `overall_score` unchanged. That fixes "blocking training crawlers is free" at
> the specification level, where it belongs, instead of only in this package's tests.

The engine already asserts the same property end to end
(`test_blocking_only_training_crawlers_costs_exactly_nothing`), so this is belt and
braces, not a gap.

---

## 6. Worker job type — `apps/worker`

`JobType.GEO_READINESS_SCAN` exists in `veo/contracts/enums.py` and nothing dispatches it
yet. When the crawl pipeline is ready, the task body is:

```python
report = run_geo_readiness(context)     # context built by the collection pipeline
# report.score        -> persist to score_results
# report.issues       -> persist to the issue tracker
# report.evidence     -> persist to evidence storage
# report.gate_status_codes -> persist beside the score, never folded into it
```

The one rule for whoever writes that: **the gate statuses get their own column.** A
readiness score of 95 with `EXPOSURE_BLOCKED` is a real and common state, and collapsing
it into a single number destroys the only actionable part of it.
