/**
 * 관측을 시작할 때 **고른 검색 모드가 그대로 서버에 간다.**
 *
 * 지키는 결함: 화면이 무엇을 골랐든 요청 본문에 `search_mode: 'BROWSING'` 하나만
 * 넣던 자리가 있었다(`app/api/observation/route.ts`). 그러면 화면에 "검색 끔" 칸이
 * 생겨도 실제로는 켠 채로 돌아, 검색해서 나온 답이 "검색 끔" 조건으로 저장된다.
 * 그 위에서 계산한 "검색 없이도 우리가 나오는 비율" 은 아무도 재지 않은 숫자다.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const callConsoleApi = vi.fn();
vi.mock('@/lib/console-api', () => ({
  callConsoleApi: (...args: unknown[]) => callConsoleApi(...args),
}));

const { startObservation } = await import('./observations');

function sentBody(): Record<string, unknown> {
  const [, options] = callConsoleApi.mock.calls[0] as [string, { body: Record<string, unknown> }];
  return options.body;
}

describe('startObservation 이 보내는 엔진 목록', () => {
  beforeEach(() => {
    callConsoleApi.mockReset();
    callConsoleApi.mockResolvedValue({ ok: true, data: { id: 'job-1' } });
  });

  it('두 모드를 고르면 엔진 항목 두 개를 보낸다', async () => {
    await startObservation({
      promptSetId: 'set-1',
      engine: 'OPENAI',
      model: 'gpt-5',
      searchModes: ['BROWSING', 'NO_BROWSING'],
      repetitions: 3,
      idempotencyKey: 'key-1',
    });

    const engines = sentBody()['engines'] as { search_mode: string }[];
    expect(engines).toHaveLength(2);
    expect(engines.map((one) => one.search_mode)).toEqual(['BROWSING', 'NO_BROWSING']);
  });

  it('한 모드만 고르면 그 모드만 보낸다 — 켬을 몰래 끼워 넣지 않는다', async () => {
    await startObservation({
      promptSetId: 'set-1',
      engine: 'OPENAI',
      model: 'gpt-5',
      searchModes: ['NO_BROWSING'],
      repetitions: 3,
      idempotencyKey: 'key-2',
    });

    const engines = sentBody()['engines'] as { search_mode: string }[];
    expect(engines).toHaveLength(1);
    expect(engines[0]?.search_mode).toBe('NO_BROWSING');
  });

  it('엔진과 모델은 모든 모드에서 같다 — 모드만 다른 두 조건이다', async () => {
    await startObservation({
      promptSetId: 'set-1',
      engine: 'OPENAI',
      model: 'gpt-4o',
      searchModes: ['BROWSING', 'NO_BROWSING'],
      repetitions: 5,
      idempotencyKey: 'key-3',
    });

    const engines = sentBody()['engines'] as { engine: string; model: string }[];
    expect(new Set(engines.map((one) => one.engine))).toEqual(new Set(['OPENAI']));
    expect(new Set(engines.map((one) => one.model))).toEqual(new Set(['gpt-4o']));
  });
});
