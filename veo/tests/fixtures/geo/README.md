# GEO readiness fixtures

Every case is a directory containing `case.json` plus the raw material that a crawl
would have produced: HTML documents, `robots.txt`, sitemaps, and — where a check needs
history or an outside corroboration — a `providers.json` payload.

Nothing here touches the network. The loader in `apps/api/tests/geo/support.py` turns a
case directory into a `veo.collect.contract.CollectionContext`.

## `case.json`

| key | meaning |
|---|---|
| `name` | directory name, repeated so a loaded case can name itself |
| `purpose_ko` | why this case exists |
| `target_url` | the URL under diagnosis |
| `documents` | list of `{url, file, status?, headers?, primary?}` — `file` is relative to the case directory and may point outside it (`../other/page.html`) when two cases must share byte-identical HTML |
| `robots_txt_file` | relative path, or absent when robots.txt could not be read |
| `sitemap_documents` | `{url: file}` |
| `rendered_dom` | `{url: file}` — DOM after JavaScript, kept apart from the raw HTML |
| `provider_states` | `{provider: ENABLED\|DISABLED\|...}` |
| `provider_payloads_file` | relative path to `providers.json` |
| `url_importance` | `{url: CONVERSION_OR_HOME\|...}` |
| `collected_at` | the moment the crawl is pretended to have happened |

`providers.json` may use the literal `"$CURRENT"` in place of a content hash. The loader
replaces it with the real SHA-256 of the primary document's bytes, which is how the
"the date moved but the content did not" case stays true without a hard-coded digest.

## Cases

| case | what it pins down |
|---|---|
| `hospital_local` | local business with a physical presence, complete entity graph |
| `ecommerce_product` | product page: no byline expected, specifications in a table |
| `publisher_article` | article: author, dates, primary sources |
| `corporate_site` | corporate pages: dates and figures genuinely do not apply |
| `generic_service` | a thin marketing page — the source of most non-PASS outcomes |
| `noindex_page` | raises `EXPOSURE_BLOCKED` without touching the number |
| `search_crawler_blocked` | search-purpose AI crawlers disallowed |
| `training_bot_blocked` | **only** training crawlers disallowed — must score exactly as `generic_service` |
| `contradictory_schema` | JSON-LD contradicts the visible text — `STRUCTURED_DATA_MISMATCH` |
| `no_schema` | no structured data at all — must not be penalised |
| `untruthful_dates` | `dateModified` moved while the bytes stayed identical |
| `http_error` | 503 |
| `auth_required` | 401 behind authentication |
| `edge_challenge` | 403 interstitial from a CDN |
| `js_shell` | an empty shell whose content only exists after JavaScript |
