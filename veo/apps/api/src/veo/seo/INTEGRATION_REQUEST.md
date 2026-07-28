# SEO 엔진 → 통합 담당자 요청

`veo/seo/**` 담당자가 다른 소유 영역에 요청하는 사항입니다. 이 패키지는 요청한 파일을
직접 고치지 않았습니다.

---

## 1. 라우터 마운트 (필수)

`veo.seo.router.router`를 API 프리픽스 아래에 포함해 주십시오. 이 패키지는
`veo/api/app.py`를 수정하지 않았습니다.

```python
from veo.seo.router import router as seo_router
...
app.include_router(seo_router, prefix=api_prefix)
```

- `GET  {prefix}/seo/checks` — `Permission.SCAN_READ`
- `POST {prefix}/seo/scan` — `Permission.SCAN_RUN`

두 라우트 모두 `veo.organizations.http.guard`를 라우트 의존성으로 선언해 두었으므로
추가 권한 배선은 없습니다. 마운트되면 `openapi.json` 재생성이 필요합니다.

**의존 없음**: DB 세션, 잡 큐, 외부 자격증명 어느 것도 요구하지 않습니다.

---

## 2. 크롤링 주체 (설계 확인 요청)

`POST /seo/scan`은 **수집이 끝난 자료를 받습니다**. 이 패키지는 네트워크에 나가지
않습니다. `CollectionContext`가 이미 "가져온 문서를 건네받는" 구조로 정의되어 있고,
SSRF 방어·리다이렉트 재검증·응답 크기 예산이 `veo.common.security`에 한 곳으로 모여
있기 때문입니다. 수집기 여덟 개가 각자 fetch 하면 그 통제가 여덟 곳으로 흩어집니다.

따라서 워커 쪽에 다음이 필요합니다.

1. `SafeFetcher`로 대상 URL 집합을 한 번 수집
2. (선택) 렌더러 실행 — 없으면 `rendered_dom`을 **비워** 보내 주십시오
3. `POST /seo/scan` 호출 또는 `veo.seo.run_seo_scan(context)` 직접 호출

`rendered_dom`을 원본 HTML로 채워 보내면 `seo.content.js_render_parity`가 항상 PASS가
됩니다. 이는 명세가 막으려는 바로 그 오판이므로, 렌더러가 돌지 않았다면 반드시 비워
두셔야 합니다. 비어 있으면 UNKNOWN으로 기록됩니다.

---

## 3. 프로바이더 키 이름 확정 요청

`CollectionContext.provider_states` / `provider_payloads`의 키를 아래 이름으로
읽고 있습니다. 자격증명 모듈이 다른 이름을 쓴다면 알려 주십시오 — 이름이 어긋나면
해당 항목이 조용히 UNKNOWN으로 남습니다.

| 키 | 쓰이는 검사 | 페이로드 형태 |
| --- | --- | --- |
| `GOOGLE_PAGESPEED` | `seo.perf.lcp_lab`, `cls_lab`, `tbt_lab` | `{url: {"lighthouse": {audit_id: {"score": float, "display_value": str}}}}` |
| `GOOGLE_CRUX` | `seo.perf.inp_field` | `{url: {"metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "FAST\|AVERAGE\|SLOW"}}}}` |
| `GOOGLE_SEARCH_CONSOLE` | `integration.gsc_verified`, `integration.sitemap_submitted`, `outcome.*` | `{"site": {...}, "sitemaps": [...], "performance": {...}, "index_coverage": {...}}` |
| `NAVER_SEARCH_ADVISOR` | `integration.naver_swa_registered` | `{"site_registered": bool, "ownership_verified": bool}` |
| `INDEXNOW` | `integration.indexnow_configured` | `{"configured": bool, "key_location": str}` |
| `BACKLINK_INDEX` | `offpage.referring_domains_present`, `offpage.no_spam_signal` | `{"referring_domains": int, "spam_flagged_domains": int, "sampled_domains": int}` |
| `BRAND_MENTIONS` | `offpage.brand_name_consistency` | `{"canonical_name": str, "observed_names": [str]}` |

`GOOGLE_PAGESPEED`와 `GOOGLE_CRUX`는 **반드시 별개 키**여야 합니다. lab 값과 field 값을
하나의 자격증명으로 묶으면 한쪽만 있는 상태에서 다른 쪽이 측정된 것처럼 보입니다.

`contracts/enums.py`의 `DataSource`에는 `NAVER_SEARCH_ADVISOR`, `INDEXNOW`,
`BACKLINK_INDEX`, `BRAND_MENTIONS`에 해당하는 값이 없습니다. 열거형에 추가할지, 아니면
프로바이더 키를 `DataSource`와 분리된 어휘로 둘지 결정해 주십시오. 저희는 후자로
가정하고 문자열 상수를 `veo/seo/collectors/*.py`에 두었습니다.

---

## 4. 파싱 의존성 — 현재 요청 없음

`lxml`과 `beautifulsoup4`는 설치되어 있지 않습니다(확인함). **추가를 요청하지
않습니다.** `veo/seo/parsing/`은 표준 라이브러리 `html.parser`만 씁니다.

사이트맵도 `xml.etree.ElementTree`가 아니라 `html.parser`로 읽습니다. 사이트맵은 진단
대상 사이트가 주는 신뢰할 수 없는 입력이고, ElementTree는 엔터티 선언을 전개하므로
중첩 엔터티 몇 줄이 프로세스 메모리를 수 기가바이트로 늘릴 수 있습니다. 회귀 테스트가
`apps/api/tests/seo/test_parsing.py::test_entity_declarations_are_not_expanded`에
있습니다. 나중에 XML 파서를 도입하신다면 `defusedxml` 쪽을 검토해 주십시오.

---

## 5. 저장소 루트 `pytest.ini`에 `--import-mode=importlib` 누락

`apps/api/pyproject.toml`에는 있고 저장소 루트 `pytest.ini`에는 없습니다. 루트
`pytest.ini`의 주석은 importlib 모드를 쓴다고 적어 두었지만 `addopts`에는
`--strict-markers`만 있습니다.

그 결과 `pytest apps/api/tests`는 통과하지만, 인자 없이 `pytest`를 실행하면
`tests/credentials/test_router.py`·`tests/geo/test_router.py`·`tests/seo/test_router.py`가
같은 모듈 이름으로 충돌해 수집 단계에서 멈춥니다(`tests/geo/test_service.py`와
`tests/seo/test_service.py`도 같습니다). 저희 파일명을 바꾸는 방법도 있지만 geo 쪽
충돌은 남고, 애초에 루트 설정 한 줄이 빠진 문제입니다.

```ini
addopts = --strict-markers --import-mode=importlib
```

`pytest.ini`는 저희 소유가 아니라 수정하지 않았습니다.

---

## 6. 확인 요청 — `Permission.EVIDENCE_READ`

`POST /seo/scan` 응답에는 증거 레코드의 `excerpt`(최대 2000자)가 포함됩니다. 현재는
`SCAN_RUN`만 요구합니다. 증거 본문을 `EVIDENCE_READ` 없이 보여도 되는지, 아니면
`EVIDENCE_READ`가 없는 호출자에게는 `evidence` 배열을 비워야 하는지 정책 결정을
부탁드립니다. 저장소(object storage) 연동이 붙기 전이라 `storage_key`는 항상 null입니다.

---

## 7. 명세에 대한 의견 (변경 요청 아님)

`veo.seo.readiness` 1.0.0을 그대로 구현했습니다. 두 가지만 기록해 둡니다.

- **hreflang 전용 검사가 없습니다.** hreflang 집합이 자기 참조를 빠뜨리거나 서로
  되가리키지 않는 경우는 `seo.canonical.declared_and_consistent`("다른 신호와 일치하는가")
  안에서 판정하고 있습니다. VEO-LAB이 별도 항목을 원한다면 명세에 추가해 주십시오 —
  추가되는 즉시 저희 테스트가 실패해 미구현을 알립니다.
- **`seo.integration.indexnow_configured`의 `evidence_required`가 `http_response`입니다.**
  키 파일을 크롤링해 확인하는 방식을 염두에 둔 것으로 보입니다. 현재는 프로바이더
  응답으로만 판정하며, 연동이 없으면 UNKNOWN입니다. 크롤 기반 확인을 원하시면 워커가
  `/{key}.txt`를 수집 대상에 넣어 주셔야 합니다.
