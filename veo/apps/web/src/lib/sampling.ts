/**
 * 표본 하한 — 엔진의 `veo.observations.sampling` 과 같은 값이어야 한다.
 *
 * 여기 있는 숫자는 **판정에 쓰지 않는다.** 비율을 낼지 말지는 엔진이 정하고 화면은 그
 * 결과(`adequacy`·`percent_text_ko`)를 받아 그린다. 이 상수는 실행 전에 사람에게
 * "몇 번 돌려야 하는지" 를 알려주기 위한 것뿐이다.
 *
 * 화면에서 다시 계산하기 시작하면 두 벌이 되고, 두 벌은 반드시 갈라진다. 지침서 0-D.
 */

/** 탐색 진단: 질문 곱하기 엔진당 최소 이만큼. 미만이면 퍼센트를 아예 내지 않는다. */
export const MIN_RUNS_FOR_EXPLORATION = 3;

/** 비교 보고: 방법론이 요구하는 최소치. */
export const MIN_RUNS_FOR_COMPARISON = 5;
