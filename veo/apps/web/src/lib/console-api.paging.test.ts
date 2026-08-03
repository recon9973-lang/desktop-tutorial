/**
 * 목록은 **끝까지** 읽는다.
 *
 * 예전에는 `?page_size=200` 을 한 번 부르고 그것을 전부라고 여겼다. 거래처가 200곳을
 * 넘는 날 목록은 경고도 없이 잘리고, 화면은 여전히 "이게 전부" 라고 말한다. 지금 12곳이라
 * 당장 아무 일도 없다는 것이 이 결함의 위험한 점이다 — 넘는 날 아무도 모른다.
 *
 * 여기서 지키는 것 셋:
 * 1. 총 개수를 채울 때까지 다음 쪽을 부른다.
 * 2. 총 개수는 **서버가 준 값**을 쓴다 — 화면이 세지 않는다.
 * 3. 끝을 못 찾아도 무한히 부르지 않는다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const call = vi.fn();

vi.mock('server-only', () => ({}));

const { readAllPages: readPages } = await import('./console-api');

/** 주입 지점으로 가짜 쪽 가져오기를 넘긴다 — 모듈 안 호출은 밖에서 못 가로챈다. */
function readAllPages(path: string, options: { maxPages?: number } = {}) {
  return readPages(path, { ...options, fetchPage: call });
}

function page(rows: number, total: number) {
  return {
    ok: true as const,
    data: Array.from({ length: rows }, (_, index) => ({ id: `row-${index}` })),
    meta: {},
    pageInfo: { total_items: total },
  };
}

beforeEach(() => {
  call.mockReset();
});

describe('총 개수를 채울 때까지 읽는다', () => {
  it('한 쪽으로 끝나면 한 번만 부른다', async () => {
    call.mockResolvedValueOnce(page(12, 12));

    const outcome = await readAllPages('/api/customers');

    expect(outcome.ok).toBe(true);
    expect(call).toHaveBeenCalledTimes(1);
    if (outcome.ok) expect(outcome.data).toHaveLength(12);
  });

  it('200 을 넘으면 다음 쪽을 부른다 — 잘리지 않는다', async () => {
    call.mockResolvedValueOnce(page(200, 250)).mockResolvedValueOnce(page(50, 250));

    const outcome = await readAllPages('/api/customers');

    expect(call).toHaveBeenCalledTimes(2);
    if (outcome.ok) expect(outcome.data).toHaveLength(250);
  });

  it('두 번째 쪽을 요청할 때 page 번호가 올라간다', async () => {
    call.mockResolvedValueOnce(page(200, 250)).mockResolvedValueOnce(page(50, 250));

    await readAllPages('/api/customers');

    expect(call.mock.calls[0]?.[0]).toContain('page=1');
    expect(call.mock.calls[1]?.[0]).toContain('page=2');
  });

  it('이미 물음표가 있는 주소에도 붙는다', async () => {
    call.mockResolvedValueOnce(page(1, 1));

    await readAllPages('/api/sites?project=abc');

    expect(call.mock.calls[0]?.[0]).toContain('project=abc&page=1');
  });
});

describe('끝을 잘못 알려줘도 멈춘다', () => {
  it('총계가 없으면 덜 찬 쪽을 끝으로 본다', async () => {
    // 서버가 page_info 를 주지 않는 목록도 있다. 그때는 더 물어볼 근거가 없다.
    call.mockResolvedValueOnce({ ok: true as const, data: [{ id: 'a' }], meta: {} });

    const outcome = await readAllPages('/api/customers');

    expect(call).toHaveBeenCalledTimes(1);
    if (outcome.ok) expect(outcome.data).toHaveLength(1);
  });

  it('총계가 계속 채워지지 않아도 무한히 부르지 않는다', async () => {
    // 서버가 이상한 총계를 주는 경우. 받은 만큼 돌려주되 멈춘다.
    call.mockResolvedValue(page(200, 1_000_000));

    const outcome = await readAllPages('/api/customers', { maxPages: 3 });

    expect(call).toHaveBeenCalledTimes(3);
    if (outcome.ok) expect(outcome.data).toHaveLength(600);
  });
});

describe('실패는 삼키지 않는다', () => {
  it('첫 쪽이 거절되면 그대로 돌려준다', async () => {
    call.mockResolvedValueOnce({ ok: false as const, reason: 'SIGNED_OUT', message: null });

    const outcome = await readAllPages('/api/customers');

    expect(outcome.ok).toBe(false);
  });

  it('두 번째 쪽이 거절되면 절반을 전부인 척하지 않는다', async () => {
    call
      .mockResolvedValueOnce(page(200, 250))
      .mockResolvedValueOnce({ ok: false as const, reason: 'SERVER_ERROR', message: null });

    const outcome = await readAllPages('/api/customers');

    expect(outcome.ok).toBe(false);
  });
});
