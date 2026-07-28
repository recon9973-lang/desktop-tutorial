# Integration request — `idna` (UTS-46) for host normalisation

**Raised by:** security / `veo.common`
**Status:** open — **not blocking**. `veo.common.urls` ships today on the standard
library and is fully tested; this is a correctness hardening, not a missing feature.

## What is being requested

Add the `idna` package (PyPI `idna`, pure Python, no transitive dependencies — it is
already an indirect dependency of `httpx`, so this is very likely a lockfile change
rather than a new package in the image).

## Why

`veo.common.urls._normalize_host` converts an internationalised host to punycode with
the standard library codec, `str.encode("idna")`. That codec implements **IDNA 2003**
(RFC 3490 + nameprep). Browsers, and therefore the URLs customers paste into VEO,
implement **UTS-46 / IDNA 2008**. Three consequences, all of which make VEO's view of a
host differ from the user's browser:

1. **Deviation characters map differently.** IDNA 2003 folds `ß` to `ss` and `ς` to `σ`;
   UTS-46 (transitional processing off, which is what browsers do now) does not. So
   `straße.example` resolves to one name in a browser and a different one here. Today
   VEO would analyse a host the customer never visited.
2. **Names the stdlib codec refuses.** Any label the 2003 tables reject — including
   emoji domains and some scripts added after Unicode 3.2 — raises `UnicodeError` and
   is reported as `MALFORMED_URL`. That is a safe failure but a wrong one: the site
   exists and a browser reaches it.
3. **No CheckBidi/CheckJoiners.** UTS-46 validation catches some malformed RTL labels
   that the stdlib codec passes through.

## Security impact

**None known, and the failure mode is fail-closed.** Every difference above ends in
either a rejection or a *different* hostname that is then put through the identical IP
validation pipeline. There is no path where the stdlib codec produces a host that
bypasses the guard while `idna` would not.

The one property that must survive the swap is the fullwidth-digit fold — `U+FF11
U+FF12 U+FF17 . U+FF10 . U+FF10 . U+FF11` must keep collapsing to `127.0.0.1` so it is
caught as loopback rather than treated as an opaque name. UTS-46 maps fullwidth digits
to ASCII digits as well, so it holds; `test_fullwidth_digits_cannot_smuggle_loopback`
in `tests/common/test_url_guard.py` pins it either way.

## Proposed change when approved

* Add `idna>=3.7,<4.0` to `apps/api/pyproject.toml`.
* In `_normalize_host`, replace `host.encode("idna")` with
  `idna.encode(host, uts46=True, transitional=False, std3_rules=False)`, keeping the
  existing `UnicodeError`/`ValueError` → `ILLEGAL_HOST` mapping (add `idna.IDNAError`).
* No test changes are expected. If any test in `tests/common/test_urls.py` changes
  behaviour, the swap is wrong and should be reverted.

## Meanwhile

The stdlib path is implemented, documented in the `veo.common.urls` module docstring,
and covered by the IDN and homograph cases in `tests/common/`.
