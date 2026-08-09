/**
 * 점수 표기는 **한 곳**에서만 정한다 — `formatScore`.
 *
 * 사장님 지시(2026-08-09):
 *   "모든 점수는 반올림이나 절삭 없다."
 *   "소수점 두자리까지만 표기. 반올림 절삭 없이 표기만 소수점 두 자리까지."
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
 * `%` 로 보이는 비율(도달 범위·확신도)은 여기서 막지 않는다. 사장님 지시는 **점수**에
 * 대한 것이고, 비율까지 두 자리로 바꾸면 화면 뜻이 달라진다. 남은 자리는
 * `ScoreCard.tsx` 의 `(clamped * 100).toFixed(1)%` 하나이며 별도로 여쭙는다.
 */

import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..');

/** 점수를 그리는 자리라고 보는 이름. 이 낱말 옆의 `toFixed` 는 반올림이다. */
const SCORE_WORDS = /score|gainpoints|gain_points|quality|reach/i;

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

describe('점수 표기는 formatScore 만 쓴다', () => {
  it('점수 옆에서 toFixed·Math.round 를 쓰지 않는다', () => {
    const offenders: string[] = [];

    for (const path of sourceFiles(ROOT)) {
      const lines = readFileSync(path, 'utf-8').split('\n');
      lines.forEach((line, index) => {
        if (!/toFixed\(|Math\.round\(/.test(line)) return;
        if (!SCORE_WORDS.test(line)) return;
        offenders.push(`${path.replace(ROOT, 'src')}:${index + 1}  ${line.trim()}`);
      });
    }

    expect(
      offenders,
      '점수를 toFixed 로 그리면 반올림된다 — 80.579 가 80.6 이 되고, 그것은 재지 않은 ' +
        '값이다. `formatScore` 를 쓴다:\n  ' + offenders.join('\n  '),
    ).toEqual([]);
  });
});
