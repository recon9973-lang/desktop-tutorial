/**
 * 서버가 준 값을 **모양이 틀려도 터지지 않게** 읽는다 — 한 곳에서.
 *
 * ## 왜 한 곳이어야 하나
 *
 * 이 네 함수가 저장소에 **스물한 벌** 흩어져 있었다(2026-08-09 실측). 같은 일을 하는데
 * 이름이 둘씩이었다 — `asRecord`/`record`, `textOrNull`/`strOrNull`. 본문은 글자
 * 하나까지 같았다.
 *
 * 지침서 0-D 가 금지하는 것이 정확히 이것이다. 중복은 낭비로 끝나지 않는다 — **나중에
 * 만든 쪽이 원본의 제약을 모른 채 더 관대해진다.** 이 저장소에서 이미 값을 치렀다:
 * 표본 규칙을 두 벌 갖고 있었는데 새로 쓴 쪽이 1~2회 표본에도 퍼센트를 내줬다
 * (`observations/metrics.py:12`).
 *
 * ## 두 갈래를 남긴 이유
 *
 * `record` 는 빈 객체를, `recordOrNull` 은 `null` 을 낸다. 하나로 합치지 않았다 —
 * 부르는 쪽이 다른 일을 한다. 목록을 읽을 때는 빈 객체가 편하고(`{}` 에서 꺼내면 전부
 * `undefined` 라 그대로 흘러간다), 응답 전체를 검사할 때는 **모양이 틀렸다는 사실
 * 자체**가 필요하다. 그 자리에서 `{}` 를 받으면 "빈 응답" 과 "응답이 아님" 이 같아진다.
 */

/** 객체가 아니면 **빈 객체**. 목록을 읽어 내려갈 때 쓴다. */
export function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/** 객체가 아니면 **`null`**. "응답이 아니다" 를 구별해야 할 때 쓴다. */
export function recordOrNull(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** 배열이 아니면 빈 배열. */
export function list(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

/**
 * 문자열 칸 하나. 없거나 빈 문자열이면 `null`.
 *
 * **빈 문자열을 `null` 로 접는 것은 의도다.** 서버가 "값이 없다" 를 `""` 로 보내는
 * 자리가 있고, 화면에서 둘은 같은 뜻이다 — 둘 다 "적을 것이 없음" 이다.
 */
export function textOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

/**
 * 문자열 칸 하나. 없으면 **빈 문자열**.
 *
 * `textOrNull` 과 갈라 둔 이유는 부르는 쪽이 다른 일을 하기 때문이다 — 화면에 그대로
 * 넣을 자리는 `''` 가 편하고(그리면 아무것도 안 보인다), "값이 없다" 를 판단해야 하는
 * 자리는 `null` 이 필요하다. 하나로 합치면 뒤쪽이 `'' ` 를 값으로 세게 된다.
 */
export function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}
