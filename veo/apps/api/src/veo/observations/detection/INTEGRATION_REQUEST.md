# 통합 요청 — 브랜드 탐지 작업자 → 통합 담당

이 작업자의 편집 범위는 세 곳입니다.

- `apps/api/src/veo/observations/detection/**`
- `apps/api/tests/observations/detection/**`
- `tests/fixtures/observations/**`

그 밖의 파일은 읽기만 했습니다. 특히 `veo/observations/{sampling,prompts,runs,runner,
providers,__init__}.py`, `veo/db/**`, `veo/common/urls.py`, `veo/geo/entity_graph.py`,
`veo/api/app.py`, `alembic/**` 은 손대지 않았습니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 0. 먼저 알아야 할 사실 — 이 패키지는 저장하지 않습니다

`detection` 은 **텍스트 → 판정** 만 합니다. DB 세션도, HTTP 호출도, 모델 호출도
없습니다. 결과를 행으로 바꾸는 것은 관측 러너의 몫입니다.

```python
from veo.observations.detection import BrandProfile, detect_answer

result = detect_answer(answer_text, own=brand, competitors=rivals, citations=urls)

run = ObservationRun(
    ...,
    brand_mentioned=result.brand_mentioned,
    brand_cited=result.brand_cited,
    citations=result.own_citation_urls,
    mentioned_entities=result.mentioned_entity_keys,
)
for event in (result.own, *result.competitors):
    if event.verdict is not MentionVerdict.NOT_FOUND:
        session.add(EntityMention(ai_answer_id=..., **event.as_entity_mention_values()))
for match in citation_matches:
    session.add(Citation(ai_answer_id=..., **match.as_citation_values()))
```

`as_entity_mention_values()` 와 `as_citation_values()` 는 **기존 컬럼만** 채웁니다.
새 컬럼을 요청하지 않습니다.

---

## 요청 #1 — `veo.observations.__init__` 에 detection 재수출

**상태:** 열림
**대상 파일:** `apps/api/src/veo/observations/__init__.py` (이 작업자 범위 밖)
**우선순위:** 낮음

지금은 `from veo.observations.detection import detect_answer` 로 서브패키지를 직접
import 해야 합니다. 동작에는 문제가 없고, 필요하면 아래를 추가해 주십시오.

```python
from veo.observations.detection import (
    AnswerDetection, BrandProfile, MentionEvent, MentionVerdict, detect_answer,
)
```

순환 참조는 없습니다. `detection` 은 `veo.observations` 의 다른 모듈을 import 하지
않습니다 (`runs.py` 의 규약은 **지키기만** 하고 import 하지 않습니다).

---

## 요청 #2 — `BrandProfile` 을 채울 원본이 스키마에 부족합니다 (가장 중요)

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/identity.py`, `alembic/**`
**우선순위:** 높음

`BrandProfile` 의 필드와 현재 스키마의 대응입니다.

| 필드 | 출처 | 상태 |
| --- | --- | --- |
| `entity_key` | 호출자가 정함 | 있음 |
| `display_name` | `competitors.display_name` / 프로젝트의 브랜드명 | 있음 |
| `aliases` | `competitors.brand_aliases` (JSON) | 경쟁사만 있음 |
| `own_domains` | `competitors.origin` / `sites` | 부분적 |
| `address_terms` | **없음** | 없음 |
| `phone_numbers` | **없음** | 없음 |
| `distinguishing_terms` | **없음** | 없음 |

**뒤의 셋이 없으면 일반명 브랜드는 전부 `NEEDS_REVIEW` 로 갑니다.** 이것은 버그가
아니라 설계입니다 — 근거가 없으면 판단하지 않습니다. 다만 `서울치과` · `중앙병원` 급
고객은 **모든 언급이 검수 대기열로 갑니다.** 운영 부하가 실제로 발생합니다.

`competitors` 에는 `brand_aliases` JSON 이 이미 있으므로, 자사 브랜드 쪽에도 같은
형태의 선언 자리를 하나 주시면 충분합니다. 컬럼 이름은 통합 담당이 정해 주십시오.

```python
# projects 또는 sites 에
brand_declaration: Mapped[JsonObject] = json_column()
# {"display_name": ..., "aliases": [...], "own_domains": [...],
#  "address_terms": ["강남구", "역삼동"], "phone_numbers": ["02-..."],
#  "distinguishing_terms": ["임플란트 센터"]}
```

`own_domains` 는 문자열 목록이고 `도메인` 또는 `도메인/경로접두사` 형태입니다.
`blog.naver.com` 처럼 **경로 없는 공용 플랫폼 호스트는 거부**합니다
(`OwnDomainRule.parse` 가 `ValueError`). 그렇게 하지 않으면 그 플랫폼의 모든 인용이
고객 것으로 계산됩니다. 선언 UI 를 만들 때 이 오류 메시지를 그대로 보여 주십시오.

---

## 요청 #3 — 리다이렉트 해제는 네트워크 없이만 합니다 (알림 + 결정 요청)

**상태:** 열림
**대상 파일:** 결정 사항 (수집 파이프라인)
**우선순위:** 중간

`google.com/url?q=…` 처럼 **목적지가 URL 안에 들어 있는** 래퍼는 벗깁니다.
`bit.ly` · `t.co` · `naver.me` 처럼 **HTTP 요청을 해야만 알 수 있는** 단축 URL 은
벗기지 않고 `CitationOwnership.UNRESOLVED` 로 표시합니다.

즉 **엔진이 단축 URL 로 우리 페이지를 인용하면 우리 인용으로 세지 않습니다.**
추측하지 않기로 한 결과이고, 대신 과소집계가 됩니다.

해소하려면 수집 단계에서 단축 URL 을 한 번 펼쳐(`HEAD` + `Location`) 저장해 주십시오.
`veo.common.security.url_guard` 를 통과시키는 조건에서 하시면 됩니다. 이 패키지는
네트워크를 타지 않으므로 여기서 할 수 없습니다.

---

## 요청 #4 — 검수 대기열 UI 가 필요합니다

**상태:** 열림
**대상 파일:** 관측 검수 담당 / `apps/web/**`
**우선순위:** 중간

`NEEDS_REVIEW` 는 **언급으로 세지 않습니다** (`is_mentioned` 는 `CONFIRMED` 만
참입니다). 사람이 확정하기 전까지 그 언급은 노출률의 분자에 들어가지 않습니다.
검수가 없으면 일반명 고객의 수치는 **실제보다 낮게** 나옵니다.

한 건을 검수하는 데 필요한 것은 전부 `MentionEvent` 에 들어 있습니다.

- `spans` — 오프셋과 인용 문구. `source` 가 `ANSWER_TEXT` 면 답변 원문 기준,
  `CITATION_URL` 이면 `source_ref` (정규화된 URL) 기준입니다.
- `signals` — 신뢰도가 움직인 이유가 한국어 문장으로 들어 있습니다.
- `match_confidence` · `confidence_band` — 임계값은 `CONFIRMATION_THRESHOLD = 0.75`.

`review_state` 는 `as_entity_mention_values()` 가 `PENDING_REVIEW` / `NOT_REVIEWED`
로 채웁니다. 사람이 확정하면 `CONFIRMED` 로 바꾸고 언급으로 세면 됩니다.

---

## 요청 #5 — SOV 집계는 `raw_occurrence_count` 를 더하면 안 됩니다 (경쟁사 담당에게)

**상태:** 알림
**대상:** `veo/competitors/sov.py` 호출자

`veo/competitors/INTEGRATION_REQUEST.md` 요청 #5 에 대한 답입니다.

- `ParticipantVisibility.mentioned_answer_count` = `is_mentioned` 인
  `MentionEvent` 를 **응답 단위로** 센 값입니다. `raw_occurrence_count` 는 절대
  더하지 마십시오. 그 값은 부가 신호이고, 더하는 순간 노출률이 반복 횟수만큼
  부풀어 오릅니다.
- `needs_human_disambiguation=True` 인 언급은 **분자에서 빠집니다.** 경쟁사
  담당이 권했던 방식과 같습니다. 별도 표시가 필요하면
  `AnswerDetection.needs_review` 를 그대로 쓰시면 됩니다.
- 우리와 경쟁사는 **같은 함수**(`detect_mentions`)를 같은 인자로 통과합니다.
  `test_competitor_detection_calls_the_same_function_as_ours` 가 호출을 가로채
  지키고 있습니다.

---

## 요청 #6 — 새 의존성 없음 (알림)

표준 라이브러리와 이미 있는 `veo.common.urls` 만 씁니다. `lxml` · `bs4` 는 쓰지
않았고, `pyproject.toml` 변경을 요청하지 않습니다. 모델 호출은 이 패키지 어디에도
없으며, `test_no_model_is_consulted_anywhere_in_this_module` 이 소스를 직접 검사해
막고 있습니다.

---

## 부록 — 이 패키지가 지키기로 한 규칙과, 아직 남은 위험

### 지키는 규칙 (바꾸려면 테스트가 먼저 막습니다)

1. **한 응답 한 브랜드 = 언급 1건.** 다섯 번 나와도 1건이고 `raw_occurrence_count`
   만 5 입니다. (`test_five_occurrences_are_one_event_with_a_raw_count_of_five`)
2. **언급과 인용은 다른 사실입니다.** 남의 기사가 우리를 다뤄도 그것은 그 매체의
   인용입니다. (`test_a_third_party_citation_is_not_ours`)
3. **인용은 언급을 포함합니다.** 자사 도메인 인용은 본문 언급이 없어도 언급이고,
   `brand_cited` 가 참이면 `brand_mentioned` 도 반드시 참입니다.
   (`test_a_citation_can_never_exist_without_a_mention`)
4. **모르면 사람에게 넘깁니다.** 동명 업체는 세지 않고 `NEEDS_REVIEW` 입니다.
   (`test_a_same_name_business_elsewhere_goes_to_review_not_to_the_count`)
5. **모든 판정은 스팬을 답니다.** 오프셋과 인용 문구가 함께 나옵니다.
   (`test_every_verdict_that_claims_anything_carries_a_span`)
6. **결정적입니다.** 같은 입력은 몇 번을 돌려도 같은 결과입니다.

### 남은 위험 (정직하게 적습니다)

1. **조사 목록은 닫힌 목록입니다.** `normalize.py` 의 `_PARTICLES` 에 없는 어미가
   붙으면 그 등장은 `WEAK` 로 떨어지고, 그 등장만 있는 응답은 `NEEDS_REVIEW` 가
   됩니다. 놓치는 것이 아니라 **사람에게 갑니다.** 실제 답변을 모으면서 목록을
   늘려야 합니다.
2. **한글이 앞뒤로 붙으면 판단하지 않습니다.** `강남베놈치과` 는 분점일 수도, 다른
   상호일 수도 있습니다. 지금은 `WEAK` → 검수입니다. 분점명을 `aliases` 로 선언하면
   바로 확정됩니다.
3. **자모가 분리된 한글은 다루지 않습니다.** `fold` 는 오프셋을 지키려고 **한 글자가
   한 글자로 접히는 경우만** 접습니다(전각 라틴·전각 숫자는 접힙니다). NFD 로 자모가
   풀린 입력은 매칭되지 않습니다. 실제 엔진 출력에서 본 적은 없지만 보장은 못 합니다.
4. **지역명 목록이 좁습니다.** `KOREAN_LOCALITY_TERMS` 는 광역 단위와 서울·부산의
   자치구, 주요 시만 담았고 `남구` · `서구` · `동구` · 읍면동은 뺐습니다. 일반
   단어와 충돌해 **멀쩡한 언급을 검수로 보내는** 쪽이 더 나쁘다고 판단했습니다.
   그래서 광역시명 없이 자치구만 적힌 답변(`유성구의 서울치과`, `덕진구 서울치과`)은
   지역 충돌 신호를 받지 못하고, 일반명 기본값 0.40 으로만 걸러집니다 — 여전히
   검수로 가지만 근거 문장이 약해집니다.
5. **선언을 그대로 믿습니다.** `own_domains` · `address_terms` 가 틀리게 채워지면
   탐지도 틀립니다. 너무 넓은 도메인 선언(공용 플랫폼·퍼블릭 서픽스)만 거부하고,
   "틀리게 채운" 경우는 막을 방법이 없습니다.
6. **감정(sentiment)은 판단하지 않습니다.** `entity_mentions.sentiment` 는 이
   패키지가 채우지 않습니다. 규칙으로 결정적으로 낼 수 있는 값이 아니라고 보고
   비워 둡니다.
