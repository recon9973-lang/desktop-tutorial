# ADR 0003 — GEO 준비도와 실제 AI 가시성은 끝까지 분리한다

- 상태: 채택
- 일자: 2026-07-28

## 배경

"AI 검색 최적화 점수"라는 단일 숫자는 두 가지 다른 것을 섞는다. 하나는 페이지가
AI 답변 엔진에 사용될 수 있는 구조인지(준비도), 다른 하나는 실제로 언급·인용됐는지
(관측)이다. 준비가 잘 되어도 인용되지 않을 수 있고, 그 반대도 있다. 둘을 합치면
어느 쪽도 실행 가능한 정보가 되지 않는다.

## 결정

- 준비도: 결정적 검사, `veo.geo.readiness` 명세, `score_results`에 저장.
- 관측: 반복 실행 표본, `observation_runs`/`ai_answers`/`citations`/`entity_mentions`에 저장.
  비율 지표로만 제공하고 100점 환산 단일 점수를 기본값으로 삼지 않는다.
- 두 값은 별도 API, 별도 점수, 별도 화면 섹션을 가진다. 어떤 계산에서도 합산하지 않는다.
- 한 번의 모델 응답을 시장 점유율로 표현하지 않는다. 프롬프트×엔진당 최소 3회,
  비교 보고는 5회 이상을 기본으로 하고, 비율에는 신뢰구간을 붙인다.

## 결과

- `test_published_specs.py::test_geo_readiness_never_carries_observation_metrics`가
  준비도 명세에 관측 지표가 섞이는 것을 차단한다.
- `test_schema_invariants.py::test_readiness_scores_and_observed_visibility_live_in_different_tables`가
  스키마 수준에서 같은 규칙을 고정한다.
