/**
 * 이력은 **눈금마다 따로**다.
 *
 * 한 번의 진단이 SEO 와 GEO 를 각각 저장한다(동반 채점). 그런데 이력을 읽는 쪽이 눈금을
 * 고르지 못하던 동안, GEO 탭은 SEO 이력과 SEO 증감을 그렸다 — 화면은 "GEO" 라고 말하면서
 * SEO 숫자를 보여줬다. 저장은 처음부터 제대로 되고 있었고, 꺼낼 길이 없었을 뿐이다.
 *
 * 여기서 지키는 것은 하나: **읽는 눈금을 서버에 말한다.** 말하지 않으면 서버는 SEO 를
 * 주고, 화면은 그것을 GEO 로 그린다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const call = vi.fn();

vi.mock('@/lib/console-api', () => ({ callConsoleApi: call }));
vi.mock('server-only', () => ({}));

const { readHistory } = await import('./scan-report');

const SITE = '3f2a1b0c-4d5e-6f70-8192-a3b4c5d6e7f8';

function ok(entries: unknown[]) {
  return { ok: true as const, data: { entries }, meta: {} };
}

beforeEach(() => {
  call.mockReset();
  call.mockResolvedValue(ok([]));
});

describe('이력을 읽을 때 눈금을 함께 말한다', () => {
  it('기본은 SEO', async () => {
    await readHistory(SITE);

    expect(call).toHaveBeenCalledWith(expect.stringContaining('kind=SEO'));
  });

  it('GEO 를 달라고 하면 GEO 라고 말한다', async () => {
    await readHistory(SITE, 'GEO');

    expect(call).toHaveBeenCalledWith(expect.stringContaining('kind=GEO'));
  });

  it('사이트는 그대로 실려 간다', async () => {
    await readHistory(SITE, 'GEO');

    expect(call).toHaveBeenCalledWith(expect.stringContaining(`site_id=${SITE}`));
  });

  it('서버가 거절하면 그대로 돌려준다 — 빈 목록으로 꾸미지 않는다', async () => {
    call.mockResolvedValue({ ok: false as const, reason: 'SIGNED_OUT', message: null });

    const outcome = await readHistory(SITE, 'GEO');

    expect(outcome.ok).toBe(false);
  });
});
