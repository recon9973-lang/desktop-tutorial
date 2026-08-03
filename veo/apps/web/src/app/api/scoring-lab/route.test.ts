// @vitest-environment node
/**
 * 채점 명세 수명주기 통로.
 *
 * 이 경로가 지키는 것은 **권한이 아니다** — 그것은 엔진이 확인한다(`scoring_spec:publish`
 * 등). 두 벌로 판단하면 언젠가 서로 다르게 답하고, 그날 화면은 되는데 엔진이 거절하거나
 * 더 나쁘게는 그 반대가 된다.
 *
 * 여기서 지키는 것은 둘뿐이다: **모르는 동작을 엔진까지 보내지 않는다**(그러면 사람이
 * 404 를 받는다), 그리고 **엔진의 거절 사유를 그대로 전한다**(삼키면 왜 안 되는지 모른다).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const act = vi.fn();

vi.mock('@/lib/scoring-lab', () => ({ actOnSpecVersion: act }));

const { POST } = await import('./route');

const VERSION = '7b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0';

function post(body: unknown): Request {
  return new Request('https://console.veo.test/api/scoring-lab', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  act.mockReset();
  act.mockResolvedValue({ ok: true, data: null, meta: {} });
});

describe('아는 동작만 엔진으로 보낸다', () => {
  it('수명주기 동작은 그대로 전달된다', async () => {
    const response = await POST(post({ versionId: VERSION, action: 'publish' }));

    expect(response.status).toBe(200);
    expect(act).toHaveBeenCalledWith(VERSION, 'publish');
  });

  it('골든 검증도 보낸다 — 상태를 바꾸지 않지만 언제든 다시 돌려야 한다', async () => {
    await POST(post({ versionId: VERSION, action: 'golden-run' }));

    expect(act).toHaveBeenCalledWith(VERSION, 'golden-run');
  });

  it('모르는 동작은 엔진까지 가지 않는다', async () => {
    const response = await POST(post({ versionId: VERSION, action: 'delete-everything' }));

    expect(response.status).toBe(400);
    expect(act).not.toHaveBeenCalled();
  });

  it('대상이 없으면 엔진을 부르지 않는다', async () => {
    const response = await POST(post({ action: 'publish' }));

    expect(response.status).toBe(400);
    expect(act).not.toHaveBeenCalled();
  });
});

describe('엔진의 거절을 그대로 전한다', () => {
  it('거절 사유가 화면까지 온다', async () => {
    act.mockResolvedValue({
      ok: false,
      reason: 'CONFLICT',
      message: '골든 검증을 통과하지 않은 명세는 발행할 수 없습니다.',
    });

    const response = await POST(post({ versionId: VERSION, action: 'publish' }));
    const body = (await response.json()) as Record<string, unknown>;

    expect(response.status).toBe(400);
    expect(body['message']).toBe('골든 검증을 통과하지 않은 명세는 발행할 수 없습니다.');
  });

  it('로그인이 끊겼으면 401 로 구분한다', async () => {
    act.mockResolvedValue({ ok: false, reason: 'SIGNED_OUT', message: null });

    const response = await POST(post({ versionId: VERSION, action: 'submit' }));

    expect(response.status).toBe(401);
  });
});
