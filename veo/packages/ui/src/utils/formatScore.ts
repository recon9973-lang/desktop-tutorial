/**
 * 점수 표기 — **값은 그대로 두고, 보이는 자리만** 소수점 둘까지.
 *
 * 사장님 지시(2026-08-09):
 *   "모든 점수는 반올림이나 절삭 없다."
 *   "소수점 두자리까지만 표기. 반올림 절삭 없이 표기만 소수점 두 자리까지."
 *
 * 둘은 다른 말이 아니다. **저장하고 주고받는 값은 재어진 그대로**(80.57124654676578)
 * 이고, **화면에 몇 자리를 보일지만** 여기서 정한다. 채점 경로에는 `round()` 가 한 곳도
 * 없고 `tests/release/test_measurement_integrity.py` 가 그것을 지킨다.
 *
 * ## 왜 `toFixed(2)` 가 아닌가
 *
 * `toFixed` 는 **반올림한다.** `80.579.toFixed(2)` 는 `"80.58"` 이다 — 재지 않은 값을
 * 만들어 낸다. 여기서는 **자른다**: `80.579` → `"80.57"`. 자르기는 실제 값보다 커지는
 * 일이 없고, 두 자리 뒤에 무엇이 있든 앞 두 자리는 잰 값 그대로다.
 *
 * ## 왜 문자열로 자르나
 *
 * `Math.trunc(v * 100) / 100` 은 부동소수점 때문에 틀린다 — `80.57 * 100` 이
 * `8056.999999999999` 라서 `80.56` 이 나온다. 잰 값을 고치지 않으려고 만든 함수가
 * 값을 고치면 안 되므로, 십진 표기를 문자열로 잘라 낸다.
 */

/** 소수점 아래 몇 자리를 보일 것인가. */
const DIGITS = 2;

/** 잴 수 없었던 값. `0` 이 아니라 **없음**이라고 말해야 한다. */
export const NOT_MEASURED = '—';

/**
 * 잰 값을 그대로 두고 소수점 두 자리까지만 보인다. 반올림하지 않고 **자른다.**
 *
 * `null`·`undefined`·`NaN`·무한대는 {@link NOT_MEASURED} 로 낸다 — 못 잰 것을 `0.00`
 * 으로 그리면 "쟀는데 0" 과 구별되지 않는다.
 */
export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return NOT_MEASURED;
  }

  const negative = value < 0;
  const magnitude = Math.abs(value);

  // 지수 표기(1e-7)는 자릿수를 문자열로 셀 수 없다. 그때만 충분히 긴 십진수로 편다 —
  // `toFixed(20)` 은 자르기 전 단계라 표기에 영향을 주지 않는다.
  const plain = magnitude.toString().includes('e')
    ? magnitude.toFixed(20)
    : magnitude.toString();

  const dot = plain.indexOf('.');
  const whole = dot === -1 ? plain : plain.slice(0, dot);
  const fraction = dot === -1 ? '' : plain.slice(dot + 1);
  const shown = fraction.slice(0, DIGITS).padEnd(DIGITS, '0');

  // `-0.001` 이 `-0.00` 으로 보이면 부호가 뜻 없이 남는다. 잘라서 0 이면 0 이다.
  const body = `${whole}.${shown}`;
  if (negative && Number(body) !== 0) return `-${body}`;
  return body;
}

/** 점수 뒤에 `점` 을 붙인 표기. 못 잰 값에는 붙이지 않는다. */
export function formatScoreWithUnit(value: number | null | undefined): string {
  const shown = formatScore(value);
  return shown === NOT_MEASURED ? shown : `${shown}점`;
}
