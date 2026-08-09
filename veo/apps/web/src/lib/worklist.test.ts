/**
 * 대장(`docs/WORKLIST.md`)이 **낡지 않게** 막는다.
 *
 * ## 왜 시험이어야 하나
 *
 * 사장님 CLAUDE.md 가 진단해 둔 그대로다 — *"앞의 것은 글이고 뒤의 것은 관문이다.
 * 글은 행동하는 순간에 개입하지 않는다."*
 *
 * 대장을 만들어 두고 "항상 갱신하겠다" 고 적는 것은 **글**이다. 그 약속은 바쁜 판에서
 * 제일 먼저 밀린다. 실제로 이 저장소에서 그 일이 이미 일어났다 —
 * `PLAN-2026-08-total-review.md` 의 오류 목록은 E1·E2·E3·E7·E8 을 미완으로 적어 두고
 * 있었는데 **다섯 개 다 끝나 있었다.** 낡은 목록을 믿고 이미 한 일을 또 할 뻔했다.
 *
 * 그래서 관문으로 만든다. **판을 올리고 대장을 안 고치면 이 시험이 실패한다.**
 * 어기려면 시험을 고쳐야 하고, 고친 것은 커밋에 남는다.
 *
 * ## 무엇을 지키나
 *
 * 대장의 내용 전체를 검사할 수는 없다 — 그것은 사람이 쓰는 글이다. 대신 **기계가
 * 확인할 수 있는 세 가지**만 본다.
 *
 * 1. **최신 판이 §3 날짜별 기록에 있다.**
 * 2. **최신 판이 §2 기능별 현황에도 있다** — 머리말의 미배포 목록이 거기다.
 * 3. 다섯 장이 다 있다 — 장 하나가 사라지면 그 물음에 답할 곳이 없어진다.
 *
 * ## 무엇을 지키지 **않나**
 *
 * 옛 판을 하나씩 확인하지 않는다. §3 은 지난 날을 `0.3.44~57` 처럼 **묶어서** 적는다 —
 * 그게 읽기 좋고, 그 판들은 이미 나갔다. 이 시험이 잡으려는 것은 **방금 올린 판을
 * 안 적은 것** 하나다. 거기가 실제로 밀리는 자리다.
 */

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { APP_VERSION, CHANGELOG } from './changelog';

const LEDGER = join(import.meta.dirname, '..', '..', '..', '..', 'docs', 'WORKLIST.md');

function ledger(): string {
  return readFileSync(LEDGER, 'utf-8');
}

describe('대장은 낡지 않는다', () => {
  it('방금 올린 판이 날짜별 기록에 있다', () => {
    const text = ledger().split('# §3.')[1] ?? '';

    expect(
      text.includes(APP_VERSION),
      `판 ${APP_VERSION} 을 올렸는데 대장 §3 에 안 적었다. 한 줄 넣는다 — ` +
        '적지 않으면 다음 사람이 git log 를 뒤져야 하고, 그것이 이 대장을 만든 이유다.',
    ).toBe(true);
  });

  it('기능별 현황이 최신 판을 말한다', () => {
    // 머리말만 보지 않는다 — 미배포 목록이 표 안에 적히기도 한다.
    const text = ledger().split('# §2.')[1]?.split('# §3.')[0] ?? '';

    expect(
      text.includes(APP_VERSION),
      `§2 가 최신 판(${APP_VERSION})을 말하지 않는다. 미배포 목록을 안 고치면 ` +
        '"무엇이 아직 안 나갔나" 를 대장이 틀리게 말한다.',
    ).toBe(true);
  });

  it('changelog 의 맨 앞이 곧 APP_VERSION 이다', () => {
    // 이 시험들이 전부 APP_VERSION 을 기준으로 삼는다. 그 값이 changelog 맨 앞과
    // 어긋나면 위 두 검사가 엉뚱한 판을 찾는다.
    expect(CHANGELOG[0]?.version).toBe(APP_VERSION);
  });

  it('다섯 장이 다 있다', () => {
    const text = ledger();
    // 장 하나가 사라지면 그 물음에 답할 곳이 없어지고, 답이 다시 저장소로 흩어진다.
    for (const section of [
      '# §1. 확정',
      '# §2. 기능별 현황',
      '# §3. 날짜별 기록',
      '# §4. 남은 것',
      '# §5. 사장님 몫',
    ]) {
      expect(text.includes(section), `대장에 「${section}」 장이 없다`).toBe(true);
    }
  });

  it('사장님 몫에 "왜 내가 못 하나" 가 적혀 있다', () => {
    const text = ledger();
    const section = text.split('# §5.')[1] ?? '';

    // 규칙 1 — 요청하기 전에 못 하는 이유가 셋 중 하나인지 본다. 그 칸이 비면
    // 내가 할 수 있는 일까지 사장님께 넘어간다.
    expect(section).toContain('왜 내가 못 하나');
    expect(section).toContain('내가 먼저 한 것');
  });
});
