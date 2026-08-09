/**
 * 점수 표기 — 값을 고치지 않는다. 자리만 줄인다.
 *
 * 이 시험이 지키는 것 셋:
 *
 * 1. **반올림하지 않는다.** `80.579` 는 `80.58` 이 아니라 `80.57` 이다. 반올림은 재지
 *    않은 값을 만들어 내는 일이고, 그 값이 거래처 화면에 나간다.
 * 2. **부동소수점에 속지 않는다.** `Math.trunc(80.57 * 100) / 100` 은 `80.56` 이다.
 *    값을 지키려고 만든 함수가 값을 깎으면 안 된다.
 * 3. **못 잰 값은 0 이 아니다.** `null` 은 `0.00` 이 아니라 `—` 다.
 */

import { describe, expect, it } from 'vitest';

import { NOT_MEASURED, formatScore, formatScoreWithUnit } from './formatScore';

describe('자르되 반올림하지 않는다', () => {
  it.each([
    [80.57124654676578, '80.57'],
    [77.4811217230749, '77.48'],
    [80.579, '80.57'], // 반올림했다면 80.58
    [59.999, '59.99'], // 반올림했다면 60.00 — 상한 60 과 구별이 안 된다
    [0.999, '0.99'],
  ])('%s -> %s', (given, expected) => {
    expect(formatScore(given)).toBe(expected);
  });

  it('반올림이면 올라갈 값들이 그대로 있다', () => {
    for (const value of [1.005, 2.675, 8.985, 99.999]) {
      expect(Number(formatScore(value))).toBeLessThanOrEqual(value);
    }
  });
});

describe('부동소수점에 속지 않는다', () => {
  it('80.57 은 80.56 이 되지 않는다', () => {
    // Math.trunc(80.57 * 100) / 100 === 80.56 — 이 함수는 그 길을 쓰지 않는다.
    expect(formatScore(80.57)).toBe('80.57');
  });

  it.each([[1.1], [2.2], [3.3], [4.4], [8.2], [16.4]])(
    '%s 가 한 자리 아래로 깎이지 않는다',
    (value) => {
      expect(formatScore(value)).toBe(`${value}0`);
    },
  );
});

describe('자릿수를 늘 두 자리로 맞춘다', () => {
  it.each([
    [100, '100.00'],
    [0, '0.00'],
    [60, '60.00'],
    [83.1, '83.10'],
  ])('%s -> %s', (given, expected) => {
    expect(formatScore(given)).toBe(expected);
  });
});

describe('못 잰 값은 0 이 아니다', () => {
  it.each([[null], [undefined], [Number.NaN], [Number.POSITIVE_INFINITY]])(
    '%s -> —',
    (given) => {
      expect(formatScore(given as number | null | undefined)).toBe(NOT_MEASURED);
    },
  );

  it('단위도 붙이지 않는다 — "—점" 은 말이 안 된다', () => {
    expect(formatScoreWithUnit(null)).toBe(NOT_MEASURED);
    expect(formatScoreWithUnit(78.911122)).toBe('78.91점');
  });
});

describe('음수', () => {
  it('부호를 지킨다', () => {
    expect(formatScore(-3.456)).toBe('-3.45');
  });

  it('잘라서 0 이면 부호를 남기지 않는다 — "-0.00" 은 읽는 사람을 헷갈리게 한다', () => {
    expect(formatScore(-0.001)).toBe('0.00');
  });
});

describe('아주 작은 값', () => {
  it('지수 표기가 와도 자릿수를 센다', () => {
    expect(formatScore(1e-7)).toBe('0.00');
  });
});
