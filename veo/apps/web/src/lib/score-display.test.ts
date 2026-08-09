/**
 * 점수 표기는 **한 곳**에서만 정한다 — `formatScore`.
 *
 * 사장님 지시(2026-08-09):
 *   "모든 점수는 반올림이나 절삭 없다."
 *   "소수점 두자리까지만 표기. 반올림 절삭 없이 표기만 소수점 두 자리까지."
 *   **"모든 값 동일하게 자르기로."** — 점수만이 아니라 비율·금액·횟수까지 같은 규칙이다.
 *
 * 값은 재어진 그대로 저장되고 전달된다(`tests/release/test_measurement_integrity.py`
 * 가 채점 경로의 `round()` 를 막는다). 화면에서 몇 자리를 보일지만 `formatScore` 가
 * 정하고, **자른다 — 반올림하지 않는다.**
 *
 * ## 왜 시험으로 두나
 *
 * 글로 적어 두면 다음에 화면 하나를 만들 때 `toFixed(1)` 이 다시 들어온다. 그러면 그
 * 화면만 조용히 반올림하고, `80.579` 가 `80.6` 으로 나간다 — 재지 않은 값이다.
 * 어기려면 이 시험을 고쳐야 하고, 고친 것은 커밋에 남는다.
 *
 * 비율도 금액도 횟수도 같은 규칙이다 — `formatPercent` 는 `0.82999` 를 `82.99%` 로 내고
 * (반올림했다면 `83%`), `formatCount` 는 `4.7` 을 `4` 로 낸다(반올림했다면 `5`).
 */

import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..');

/**
 * 표기가 아닌 자리 — 여기서는 `Math.round` 를 막지 않는다.
 *
 * SVG 좌표·회전 각도·진행 막대 폭은 **사람이 읽는 값이 아니라 그리는 치수**다. 화면에
 * 숫자로 나오지 않으므로 자릿수 규칙의 대상이 아니고, 여기까지 막으면 규칙이 무슨 뜻인지
 * 흐려진다.
 */
const NOT_A_DISPLAYED_VALUE = /degrees|percent =|\bx:|\by:|expectedPages/;

/**
 * `toLocaleString` 은 **날짜에만** 허용한다.
 *
 * 숫자에 쓰면 소수를 조용히 반올림한다 — 사용량 `12.34567%` 가 `12.346` 으로 나가고
 * 있었다(2026-08-09 발견, `dashboard/page.tsx`). 정수에는 무해하지만 **부르는 자리에서는
 * 그 값이 정수인지 보이지 않는다.** "여기는 정수라 괜찮다" 는 판단은 다음 사람에게
 * 전달되지 않고, 나중에 그 필드가 소수가 되는 날 아무 경고도 없다.
 *
 * `formatCount` 는 `Math.trunc` 를 먼저 걸고 같은 일을 한다 — 정수에는 결과가 같고
 * 소수에는 안전하다. 바꾸는 데 드는 것이 없다.
 */
const A_DATE_NOT_A_NUMBER = /new Date\(|\bmoment\b|dateStyle|timeStyle/;

function sourceFiles(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      found.push(...sourceFiles(path));
      continue;
    }
    if (!/\.tsx?$/.test(entry) || /\.test\.tsx?$/.test(entry)) continue;
    found.push(path);
  }
  return found;
}

describe('표기는 formatScore · formatPercent · formatCount 만 쓴다', () => {
  it('화면에 나가는 값을 toFixed·Math.round 로 그리지 않는다', () => {
    const offenders: string[] = [];

    for (const path of sourceFiles(ROOT)) {
      const lines = readFileSync(path, 'utf-8').split('\n');
      lines.forEach((line, index) => {
        if (!/toFixed\(|Math\.round\(/.test(line)) return;
        if (NOT_A_DISPLAYED_VALUE.test(line)) return;
        offenders.push(`${path.replace(ROOT, 'src')}:${index + 1}  ${line.trim()}`);
      });
    }

    expect(
      offenders,
      'toFixed·Math.round 는 **반올림**한다 — 80.579 가 80.6 이 되고, 그것은 재지 않은 ' +
        '값이다. 표기는 `formatScore`(점수) · `formatPercent`(비율) · `formatCount`(정수) ' +
        '셋으로만 한다. 셋 다 자르고, 반올림하지 않는다:\n  ' + offenders.join('\n  '),
    ).toEqual([]);
  });

  it('숫자를 toLocaleString 으로 그리지 않는다 — 날짜만 허용', () => {
    const offenders: string[] = [];

    for (const path of sourceFiles(ROOT)) {
      const lines = readFileSync(path, 'utf-8').split('\n');
      lines.forEach((line, index) => {
        if (!/\.toLocaleString\(/.test(line)) return;
        if (A_DATE_NOT_A_NUMBER.test(line)) return;
        offenders.push(`${path.replace(ROOT, 'src')}:${index + 1}  ${line.trim()}`);
      });
    }

    expect(
      offenders,
      'Number#toLocaleString 은 소수를 **반올림**한다 — 12.34567 이 12.346 으로 나간다. ' +
        '정수라서 지금은 무해하더라도 부르는 자리에서는 그것이 보이지 않는다. ' +
        '`formatCount`(정수) 를 쓴다 — Math.trunc 를 먼저 걸고 같은 일을 한다. ' +
        '날짜는 `new Date(...).toLocaleString(...)` 형태로 쓰면 여기 걸리지 않는다:\n  ' +
        offenders.join('\n  '),
    ).toEqual([]);
  });
});
