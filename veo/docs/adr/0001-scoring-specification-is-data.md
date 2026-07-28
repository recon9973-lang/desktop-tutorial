# ADR 0001 — 점수 규칙은 코드가 아니라 버전이 있는 데이터다

- 상태: 채택
- 일자: 2026-07-28
- 결정권자: VEO-LAB(방법론) · VENOM(구현)

## 배경

진단 도구의 신뢰는 "이 점수가 왜 이렇게 나왔는가"에 답할 수 있는지에 달려 있다.
가중치가 checker 코드 안에 흩어져 있으면 배점이 조용히 바뀌고, 과거 점수를
재현할 수 없으며, 고객에게 근거를 제시할 수 없다.

## 결정

배점, 심각도 계수, 상한, 게이트, 구간은 전부 `packages/scoring-specs/specs/**`의
YAML 명세에만 존재한다. 명세는 JSON Schema로 검증하고 SHA-256 체크섬을 부여한다.
`veo/scoring/evaluator.py`는 명세를 읽어 계산만 수행하며, 어떤 숫자도 자체 보유하지 않는다.

발행(PUBLISHED)된 명세는 수정하지 않는다. 변경은 새 버전이며, 과거 결과를 새 산식으로
재계산할 때는 원래 점수와 재계산 점수를 모두 보존한다(`score_results.recomputed_from_score_result_id`).

## 결과

- 점수 산식 변경이 리뷰 가능한 데이터 diff가 된다.
- 고객이 `/api/scoring/specs/{spec_id}/{version}`으로 전문을 열람할 수 있다.
- golden fixture가 명세의 조용한 변경을 즉시 실패로 만든다.
- 대가: 새 검사를 추가하려면 명세와 collector를 함께 갱신해야 한다. 의도한 마찰이다.
