# 브랜드 탐지 픽스처

`veo.observations.detection` 이 실제 한국어 AI 답변에서 무엇을 세고 무엇을 사람에게
넘기는지 고정하는 사례들입니다. 네트워크를 타지 않고, LLM 을 부르지 않습니다.

로더는 `apps/api/tests/observations/detection/support.py` 에 있습니다.

## 파일 형식

| 키 | 뜻 |
|---|---|
| `name` | 파일 이름과 같은 사례 이름 |
| `purpose_ko` | 이 사례가 존재하는 이유 |
| `answer_text` | 엔진이 낸 답변 원문 (합성입니다. 실제 응답이 아닙니다) |
| `citations` | 답변이 근거로 단 URL 목록. 순서가 곧 `position` |
| `brand` | 고객 브랜드 프로필 (`BrandProfile` 의 필드와 1:1) |
| `competitors` | 선언된 경쟁사 프로필 목록 |
| `expected.own` | 고객 브랜드에 대해 기대하는 판정 |
| `expected.competitors` | `competitor_id` 별 기대 판정 |

`expected` 에 오프셋은 적지 않습니다. 스팬이 원문과 일치하는지는
`test_fixture_cases.py` 가 모든 사례에 대해 일반 규칙으로 검사합니다.

## 사례

| 사례 | 고정하는 것 |
|---|---|
| `plain_mention` | 조사 없이 그대로 언급 — 1건, `CONFIRMED` |
| `particle_forms` | 조사가 붙은 다섯 번의 등장 = 언급 1건, 원시 등장 수 5 |
| `same_name_other_business` | 같은 이름 다른 병원 — 세지 않고 `NEEDS_REVIEW` |
| `competitor_mentioned` | 경쟁사만 언급됨 — 우리는 `NOT_FOUND` |
| `cited_via_redirect` | 본문 언급 없이 리다이렉트로 감싼 우리 URL 인용 — 인용도 언급이다 |
| `third_party_article` | 브랜드를 다룬 남의 기사 인용 — 우리 인용이 아니다 |
| `no_mention` | 아무것도 없음 |
| `inside_competitor_sentence` | 경쟁사 문장 안에서만 등장한 일반명 — `NEEDS_REVIEW` |

## 경고

`answer_text` 는 전부 합성입니다. 실제 병원 이름·주소·전화번호가 아니며
(`베놈치과` 는 VENOM 자체 예시, 나머지는 가공된 이름), 실제 AI 엔진 응답도 아닙니다.
