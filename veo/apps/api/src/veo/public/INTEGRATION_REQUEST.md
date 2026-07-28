# Public surface — integration requests

Everything below needs a file this worker does not own. Nothing here blocks the package:
`veo/public/**` is complete and its tests pass without any of it. Each item states what
is degraded until it lands, and items 1–4 are the ones that must land **before the
surface is exposed to the open internet**.

---

## 1. Mount the router — `veo/api/app.py`

`veo.public.router.router` is an `APIRouter` with prefix `/public/v1` and tag `public`.
It is not mounted, and `tests/public/test_router.py::test_the_router_is_not_mounted_by_the_application`
asserts that it stays unmounted until you do it deliberately.

```python
from veo.public.router import router as public_router
application.include_router(public_router)   # NOT under settings.api_prefix
```

Note the missing prefix: the public surface is versioned on its own path (`/public/v1`)
because it is a different product surface with a different contract lifetime from the
console API. Mounting it under `/api` would make `/api/public/v1/...`, which is not what
the front end is being built against.

| method | path | auth |
|---|---|---|
| `POST` | `/public/v1/seo-scans` | **none** |
| `POST` | `/public/v1/geo-readiness-scans` | **none** |
| `POST` | `/public/v1/keyword-lookups` | **none** |
| `GET` | `/public/v1/results/{token}` | **none** |
| `POST` | `/public/v1/leads` | **none** |

No permission is involved: `tests/public/test_isolation.py` asserts that no route here
pulls in anything from `veo.authz`, `veo.auth`, `veo.organizations` or `veo.db`.
`openapi.json` needs regenerating after mounting.

**Until then:** the surface is reachable only through `veo.public.service.PublicScanService`.

---

## 2. CORS for the marketing site — `veo/api/app.py` / deployment settings

`settings.cors_allowed_origins` currently defaults to `["http://localhost:3000"]`. The
public scan is called from the marketing site, which is a different origin from the
console. Add that origin to `VEO_CORS_ALLOWED_ORIGINS`.

One thing to check while you are there: the app sets `allow_credentials=True`. The public
routes need no cookie and no `Authorization` header, and a wildcard origin combined with
credentials is refused by browsers anyway. If the public origin is added to the same
list, nothing breaks — but the public surface never wants credentialed CORS, so a
separate middleware scoped to `/public` would be tidier if you are already in there.

**Until then:** browsers on the marketing domain cannot call the endpoints.

---

## 3. `SafeFetcher` cannot catch its own transport errors — `veo/common/security/fetcher.py`

`SafeFetcher._stream` wraps `client.stream(...)` in `try/except httpx.HTTPError`, but
`httpx.Client.stream` is a `@contextmanager`: the request is not sent until the returned
object is *entered*, one frame later in `fetch`. So a connection refusal, a DNS failure
at connect time, or a TLS handshake error propagates out of `SafeFetcher.fetch` as a raw
`httpx.ConnectError` rather than as `TransportFailedError`.

Reproduced in `tests/public/test_service.py::test_a_site_that_refuses_the_connection_is_answered_not_raised`
— with the `except (FetchError, httpx.HTTPError)` in `veo/public/service.py::_fetch`
removed, that test gets an `httpx.ConnectError`, which on the mounted router is a 500.

Suggested fix in the fetcher:

```python
with self._client() as client:
    for hop_index in range(max_hops):
        ...
        try:
            with self._stream(client, method, decision) as response:
                ...
        except httpx.TimeoutException as exc:
            raise TransportFailedError(f"timed out fetching hop {hop_index}") from exc
        except httpx.HTTPError as exc:
            raise TransportFailedError(
                f"transport failure on hop {hop_index}: {type(exc).__name__}"
            ) from exc
```

This affects every caller of `SafeFetcher`, not only the public surface — the collection
pipeline has the same exposure.

**Until then:** `veo/public/service.py` catches `httpx.HTTPError` defensively, and the
public surface is correct. Internal callers are not.

---

## 4. Redis backing for the rate limiter and the result store — new module, owner TBD

`veo.public.limits.InMemoryRateLimiter` and `veo.public.service.InMemoryPublicResultStore`
both count and store **inside one process**. Consequences, stated plainly:

* Both public limits multiply by the number of API processes. `public_rate_limit_per_hour
  = 10` (scans, per caller) becomes 40 scans/hour with four uvicorn workers, and
  `public_target_host_limit_per_hour = 60` (**requests**, per target host — the figure
  that stops VEO being an attack amplifier) becomes 240 requests/hour against any one
  victim instead of 60.
* Note the two settings count different units and are not comparable: a scan makes two
  outbound requests, the page and its `robots.txt`. So the shipped single-process cap is
  60 requests/hour to any one host, which is about **30 full scans** of that host from
  the entire public surface. Measured, not estimated: driving the endpoint until it
  refuses delivers exactly 60 requests and serves 30 scans.
* A restart forgets every counter, so a restart loop resets the limit.
* A share link minted by worker A returns 404 from worker B. With more than one process
  the results endpoint is broken roughly `1 - 1/n` of the time.

`settings.redis_url` already exists. Both protocols (`RateLimiter`, `PublicResultStore`)
are single-method-ish and were written to be re-implemented over Redis without touching
the service: a sorted-set sliding window for the limiter, and `SETEX` keyed by the token
fingerprint with the TTL already carried on `StoredPublicResult.expires_at`.

**Until then:** run exactly one public-facing API process, or treat the configured limit
as per-process and divide it by the worker count.

---

## 5. Trusted-proxy configuration — deployment, not code

`veo.public.router.client_address` reads `request.client.host` and deliberately ignores
`X-Forwarded-For`: a rate-limit key the caller can choose is not a rate limit. Behind a
load balancer that makes every request appear to come from the balancer, which collapses
the per-IP bucket into one global bucket.

The fix is at the ASGI layer, where the trusted hop count is known — `uvicorn
--proxy-headers --forwarded-allow-ips <balancer ip>`, or Starlette's
`ProxyHeadersMiddleware` configured with the trusted network. Please confirm the
deployment topology so the right one is set; do **not** solve it by parsing the header
in application code.

**Until then:** behind a proxy, the per-IP bucket is effectively global and the session
bucket is doing all the work. The per-target-host bucket is unaffected, so the
amplification protection still holds.

---

## 6. Durable lead storage — `alembic/`, `veo/db/models/`

`veo.public.leads.InMemoryLeadStore` loses every lead on restart, and each process keeps
its own. That is not acceptable for a sales pipeline, and a durable table is a schema
this worker does not own.

Requested shape — deliberately narrow, matching what `StoredLead` already holds:

```
public_leads
  id                uuid  pk
  received_at       timestamptz  not null
  name              text  not null
  phone             text  null
  email             text  null
  site_url          text  null
  -- exactly one of phone/email must be present (check constraint)
```

No `organization_id`: a lead has no tenant yet, which is the whole point of the surface.
Whoever converts a lead into a customer is the one who attaches it to an organization.

**Until then:** leads survive only until the process restarts. Do not launch a paid
campaign against this endpoint before the table exists.

---

## 7. Marketing-consent handling — legal, then code

Not implemented, and deliberately so. Korea's 개인정보 보호법 and 정보통신망법 treat
collection consent and advertising-consent as separate acts, require the purpose, the
retention period and the consequence of refusing to be stated separately, and do not
accept a pre-ticked box. Writing a checkbox and a plausible Korean sentence here would
produce something that *looks* compliant, which is worse than not having it.

What exists today: the lead is recorded as a service enquiry, and the response states —
in `consent_note_ko` — that no marketing consent was taken or stored.

What is needed before any marketing use of these contacts:

1. The approved Korean text for 수집·이용 동의 and for 광고성 정보 수신 동의, separately.
2. The retention period to state, and whether it differs for the two.
3. Whether the consent record itself must be stored (timestamp, version of the text
   shown, and IP or not) — this changes item 6's table.

**Until then:** contacts collected here may be used to answer the enquiry and nothing
else.

---

## 8. A `TARGET_UNREACHABLE` error code — `veo/contracts/enums.py`

When a customer's own site refuses the connection, the public service currently answers
`PROVIDER_UNAVAILABLE`, which is the closest existing code and is still wrong: the target
site is not one of VEO's providers, and a front-end that groups by error code will file
"your website is down" under "VEO's integrations are down".

Requested: `TARGET_UNREACHABLE`, retryable, alongside the existing `TARGET_URL_REJECTED`.

**Until then:** the Korean message is correct and the code is misleading. One line in
`veo/public/service.py::_fetch` changes when the code exists.

---

## 9. A public-suffix list, if per-owner host limiting is wanted — new dependency

`HostBudgetGuard` charges the target-host bucket per **hostname**. A victim reachable at
`www.example.com`, `example.com` and `shop.example.com` therefore gets three separate
budgets, and an attacker who knows a victim's hostnames can multiply the traffic by the
number of them.

Limiting by registrable domain instead would need a public-suffix list to tell
`example.co.kr` (registrable) from `co.kr` (a suffix). Deriving it by counting dots is
wrong for every Korean second-level domain, which is most of the customer base, so it is
not being guessed at here. `publicsuffix2` or an embedded PSL snapshot would be a new
dependency, and this worker is not permitted to add one.

**Until then:** the cap is per hostname, not per site owner. The `CLIENT_IP` and
`SESSION` buckets still bound the total, so this multiplies a victim's exposure by their
hostname count rather than removing the limit.
