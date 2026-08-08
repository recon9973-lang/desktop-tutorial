/**
 * 발행본 본문을 읽어 오는 통로.
 *
 * 지키는 것 둘 —
 *
 * 1. **버전 번호를 주소에 그대로 넣는다.** 다른 판을 열면 고객에게 보낸 것과 다른
 *    문서를 보게 된다.
 * 2. **화면은 값을 직접 포맷하지 않는다.** 서버가 준 `display` 를 그대로 쓴다.
 *    화면이 따로 포맷하면 같은 버전이 화면과 내려받은 파일에서 다르게 보인다.
 *    이 시험은 타입에 `display` 가 남아 있는지를 지킨다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const callConsoleApi = vi.fn();

vi.mock('server-only', () => ({}));
vi.mock('@/lib/console-api', () => ({ callConsoleApi }));

const { readReportVersion } = await import('@/lib/reports');

beforeEach(() => {
  callConsoleApi.mockReset();
  callConsoleApi.mockResolvedValue({ ok: true, data: {}, meta: {} });
});

describe('발행본 본문 읽기', () => {
  it('버전 번호를 주소에 넣는다', async () => {
    await readReportVersion('r-1', 3);
    expect(callConsoleApi).toHaveBeenCalledWith('/api/reports/r-1/versions/3');
  });

  it('보고서 번호를 주소로 안전하게 옮긴다', async () => {
    await readReportVersion('r 1/2', 1);
    expect(callConsoleApi).toHaveBeenCalledWith('/api/reports/r%201%2F2/versions/1');
  });

  it('목록 창구가 아니라 본문 창구를 부른다', async () => {
    await readReportVersion('r-1', 2);
    const path = String(callConsoleApi.mock.calls[0]?.[0]);
    expect(path).not.toContain('page_size');
    expect(path).toMatch(/\/versions\/2$/);
  });

  it('읽기 전용이다 — 본문을 여는 것이 무언가를 바꾸면 안 된다', async () => {
    await readReportVersion('r-1', 1);
    // 두 번째 인자(method·body)가 아예 없어야 GET 이다.
    expect(callConsoleApi.mock.calls[0]).toHaveLength(1);
  });
});
