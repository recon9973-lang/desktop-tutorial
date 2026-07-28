# `veo.observations.providers` + `veo.observations.runner` → integration requests

Everything below is outside `apps/api/src/veo/observations/providers/**` and
`apps/api/src/veo/observations/runner.py`, and therefore not mine to change. None of it is
required for this module to be *correct* — with none of it done, every engine reports
`DISABLED_NO_CREDENTIAL`, every run is error-coded, and every rate is "측정 불가". Items 3,
4 and 5 are what stand between that state and a real observation anyone should act on.

---

## 1. Credential fields for all four engines — **delivered**

`ProviderCredentials` now carries `openai_api_key`, `google_gemini_api_key`,
`perplexity_api_key` and `anthropic_api_key`, with `gemini_state()`, `perplexity_state()`
and `anthropic_state()` alongside `openai_state()`, and all four reported by `states()`.

Every adapter is built through `HttpAnswerProvider.from_settings`, which reads its own
`settings_field`. The `os.environ` shim that stood in for the missing fields has been
deleted, along with the `VEO_PERPLEXITY_API_KEY` / `VEO_ANTHROPIC_API_KEY` constants that
named it. No further action — recorded here so the trail is legible.

One small follow-up remains, folded into item 2 below: `base.credential_state` still
carries a private copy of the placeholder table from `core/settings.py`, needed for the
direct-construction path (`OpenAIAnswerProvider(credential=SecretStr(...))`, which the
tests use). A public `provider_state_for(value: SecretStr | None) -> ProviderState`
exported from `core/settings.py` would let that copy go.

## 2. Move the provider-resilience base out of the Naver package (requested)

`ResilientCaller`, `RetryPolicy`, `CircuitBreaker`, `CallOutcome`, `ProviderFailure` and
`UNKNOWN` live in `veo/providers/naver/errors.py`. They are provider-neutral; only the
error subclasses and their Korean text are Naver-specific. Reusing them here — rather than
forking a second resilience pattern — means `AnswerProviderError` subclasses
`NaverProviderError`, because that is the type `ResilientCaller.call` catches.

That inheritance is correct in behaviour and wrong in name. Requested: move the neutral
half to `veo/providers/errors.py` —

* `UnknownValue` / `UNKNOWN`, `CallOutcome`, `ProviderFailure`, `RetryPolicy`,
  `CircuitBreaker`, `CircuitState`, `ResilientCaller`;
* a neutral `ProviderError` base carrying `error_code` / `provider_state` / `retryable` /
  `message_ko`;

and leave `veo/providers/naver/errors.py` re-exporting them with the `Naver*` subclasses
and the Naver Korean strings. Nothing in this module's behaviour changes; the only edit
here would be the import line and the base class of `AnswerProviderError`.

Please also export `provider_state_for` from `core/settings.py` (see item 1) so the
placeholder table stops being duplicated in `base.py`.

No customer-facing string in this module mentions Naver — `test_answer_providers.py::
test_no_provider_error_message_names_naver` asserts it — so the current arrangement is
safe to ship as-is.

## 3. A durable `RecordedAnswerStore` (required before any customer-facing run)

`providers/storage.py` ships one implementation, `InMemoryAnswerStore`, and the module
docstring says plainly that the S3 adapter is out of scope for this worker. A durable
implementation of the protocol is needed, and it is load-bearing rather than cosmetic:
`ObservationRun.__post_init__` refuses to record a mention without a stored answer, so
with a process-local store every mention claimed today is evidence that vanishes on the
next deploy.

The protocol is three methods (`put`, `find`, `read`) plus `raw` for hash verification.
Requirements the runner depends on:

* `find(key)` is what makes a pass idempotent per `(prompt_id, conditions, attempt)` — it
  must be a real existence check, not a cached guess;
* `put` must be write-through before it returns, because the run row is written from its
  return value;
* object keys are `{conditions_fingerprint}/{prompt_id}/{attempt:04d}.json` under
  `storage://answers/`;
* retention should match the evidence policy, and expiry must be visible to whatever
  serves the evidence screen — a run pointing at an expired object needs to say
  "근거 보관 기간이 지났습니다", not 404.

## 4. Persistence for `ObservationRun` and `RunReport` (required)

`alembic/**` and the ORM are not mine. Nothing in this module writes to the database; the
runner returns a `RunReport` and stops. Two things need columns beyond the existing run
fields, and both matter:

* **`skipped`** — a budget-truncated pass returns the list of work it did not execute. If
  only `runs` is persisted, the pass is indistinguishable from a complete one, which is
  exactly the "we measured everything" reading the ceiling exists to prevent.
* **`below_repetition_floor`** and **`stopped_reason`** — the caveats that must travel
  with the rate rather than being recomputed by whoever renders it.

Cost is `float | None` on purpose. A `NOT NULL DEFAULT 0` on a cost column would turn "we
do not know what this cost" into "this was free".

## 5. Confirm the Gemini mapping against a live response (required before first use)

`providers/gemini.py` is written to the documented Generative Language API and has not
been exercised against the real service. Four things should be confirmed with one real
call before any customer-facing observation run, because each one silently changes a
number rather than raising:

| what                    | what this adapter assumes                                          |
| ----------------------- | ------------------------------------------------------------------ |
| model version field     | `modelVersion` at the top level, falling back to `model`           |
| answer text             | `candidates[0].content.parts[].text`, concatenated                 |
| grounding sources       | `candidates[0].groundingMetadata.groundingChunks[].web.uri`        |
| token usage             | `usageMetadata.promptTokenCount` / `candidatesTokenCount`          |

Two of those fail safe and one does not. A wrong *model version* field raises
`AnswerSchemaError` and the run is "측정 불가"; wrong *usage* keys yield `cost_usd = None`
with `NO_USAGE_REPORTED`, which is honest but disables budget enforcement. A wrong
*grounding* path is the dangerous one: it would silently produce zero citations on every
grounded run, so 인용률 would read 0% rather than "측정 불가". If confirming the path is
not possible quickly, prefer running Gemini with `SearchMode.NO_BROWSING` — that records
`NOT_EXPOSED_BY_PROVIDER` and cannot be mistaken for a measured zero.

The same applies to `providers/perplexity.py` and `providers/anthropic.py`, which have
never been called either. `providers/openai.py` is written to the documented Responses
API and is also unconfirmed against a recorded live response.

## 6. A price table (requested)

`base.DEFAULT_PRICE_TABLE` is empty, deliberately: no per-token price is hard-coded
anywhere in this module, because a stale price rendered as a cost is a fabrication. The
consequence is that with no table configured, `cost_usd` is `None` with
`CostBasis.NO_PRICE_CONFIGURED`, and **a budget ceiling cannot be enforced** — the runner
stops with `StopReason.COST_UNMEASURABLE` rather than spending an unknown amount under a
limit somebody asked for.

Requested: a VEO-LAB-owned price list (per model version, USD per million input/output
tokens, with the date it was checked) passed in as `PriceTable`. Where it lives is the
integration maintainer's call — settings, a YAML spec beside the scoring specs, or a
database table. It should carry the "as of" date, so a study can be re-costed later
against the prices that actually applied.

## 7. Wiring (requested, when there is a job to wire it to)

`veo/api/app.py` is not mine and this module mounts nothing. When the
`GEO_OBSERVATION_RUN` job type is implemented, the construction is:

```python
registry = build_registry(price_table=lab_price_table())  # reads ProviderCredentials
runner = ObservationRunner(
    registry=registry,
    store=durable_answer_store(),
    detector=SubstringMentionDetector(brand_target),
    max_concurrency=4,
    budget_usd=study.budget_usd,
)
report = runner.execute(prompt_set, conditions=..., repetitions=study.repetitions)
```

Two things the caller must not do:

* pass `allow_below_floor=True` without carrying `report.summary_ko` through to whatever
  the customer sees;
* call `aggregate_rate(report.runs, ...)` without checking `report.is_complete`. The
  aggregate is honest about sample size and about mixed conditions; it has no way to know
  that sixteen planned runs were never executed.

`veo/observations/__init__.py` is a fixed contract and exports nothing from here, so
consumers import `veo.observations.runner` and `veo.observations.providers.*` directly. If
the integration maintainer would rather re-export them, that is a one-line change in a
file that is not mine.
