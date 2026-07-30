import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * 팀원 목록의 위험은 계산이 아니라 **읽기**에 있다.
 *
 * 이 파일이 하는 일은 엔진 응답의 이름을 우리 쪽 표기로 옮기는 것뿐인데, 그 옮기는
 * 과정에서 조용히 틀리면 화면이 사실과 다른 것을 보여준다. 특히 두 가지가 위험하다.
 *
 * **비활성 계정을 활성으로 보이게 하는 것.** 값이 없을 때 활성으로 접으면, 내보낸
 * 직원이 아직 접근 가능한 것처럼 보인다. 없는 값은 활성이 아니다.
 *
 * **목록을 조용히 비우는 것.** 다른 화면에서 실제로 겪은 일이다 — 응답의 형태를
 * 잘못 짚어 모든 목록이 빈 배열이 됐고, 등록은 성공하는데 화면에는 아무것도 나오지
 * 않아 원인을 찾기 어려웠다.
 */

const call = vi.hoisted(() => vi.fn());

vi.mock('@/lib/console-api', () => ({ callConsoleApi: call }));
vi.mock('server-only', () => ({}));

const { changeRole, changeStatus, inviteMember, listMembers, reinvite, isRole, ROLES, ROLE_LABELS } =
  await import('./team');

function ok(data: unknown) {
  return { ok: true as const, data, meta: {} };
}

beforeEach(() => call.mockReset());

describe('팀원 목록', () => {
  it('배열 응답을 그대로 읽는다', async () => {
    call.mockResolvedValue(
      ok([
        {
          id: 'u1',
          display_name: '이재훈',
          email: 'a@b.kr',
          roles: ['ANALYST'],
          is_active: true,
          has_password: true,
          last_login_at: '2026-07-30T01:00:00Z',
        },
      ]),
    );

    const outcome = await listMembers();

    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;
    expect(outcome.data).toHaveLength(1);
    expect(outcome.data[0]).toMatchObject({
      id: 'u1',
      displayName: '이재훈',
      email: 'a@b.kr',
      isActive: true,
      hasPassword: true,
    });
  });

  it('is_active 가 없으면 활성으로 접지 않는다', async () => {
    /** 내보낸 직원이 아직 들어올 수 있는 것처럼 보이면 안 된다. */
    call.mockResolvedValue(ok([{ id: 'u1', display_name: 'x', email: 'x@y.kr' }]));

    const outcome = await listMembers();

    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;
    expect(outcome.data[0]?.isActive).toBe(false);
  });

  it('비밀번호를 아직 안 정한 사람을 구분한다', async () => {
    /** 초대는 갔는데 수락하지 않은 상태다. 화면이 이걸 알려야 재발송할 수 있다. */
    call.mockResolvedValue(ok([{ id: 'u1', display_name: 'x', email: 'x@y.kr', is_active: true }]));

    const outcome = await listMembers();

    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;
    expect(outcome.data[0]?.hasPassword).toBe(false);
  });

  it('배열이 아닌 응답에도 터지지 않는다', async () => {
    call.mockResolvedValue(ok({ items: [] }));

    const outcome = await listMembers();

    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;
    expect(outcome.data).toEqual([]);
  });

  it('실패는 실패대로 넘긴다 — 빈 목록으로 바꾸지 않는다', async () => {
    /** 못 불러온 것과 사람이 없는 것은 다른 사실이다. */
    call.mockResolvedValue({ ok: false, reason: 'SIGNED_OUT', message: null, retryAfterSeconds: null });

    const outcome = await listMembers();

    expect(outcome.ok).toBe(false);
  });
});

describe('초대', () => {
  it('중첩된 응답에서 초대 링크를 꺼낸다', async () => {
    /** 응답은 `{ member, invitation }` 이다. 한 겹을 놓치면 링크가 빈 문자열이 된다. */
    call.mockResolvedValue(
      ok({
        member: { id: 'u2', display_name: '새 직원', email: 'n@b.kr' },
        invitation: { invite_url: 'https://veo.example/invite/tok', expires_at: '2026-08-06T00:00:00Z' },
      }),
    );

    const outcome = await inviteMember({ email: 'n@b.kr', displayName: '새 직원', role: 'ANALYST' });

    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;
    expect(outcome.data.inviteUrl).toBe('https://veo.example/invite/tok');
    expect(outcome.data.expiresAt).toBe('2026-08-06T00:00:00Z');
  });

  it('앞뒤 공백을 떼고 보낸다', async () => {
    call.mockResolvedValue(ok({ member: {}, invitation: {} }));

    await inviteMember({ email: '  n@b.kr ', displayName: '  새 직원  ', role: 'ANALYST' });

    expect(call).toHaveBeenCalledWith('/api/users', {
      method: 'POST',
      body: { email: 'n@b.kr', display_name: '새 직원', role: 'ANALYST' },
    });
  });
});

describe('계정 상태', () => {
  it('비활성으로 바꾸는 요청을 그대로 보낸다', async () => {
    call.mockResolvedValue(ok({ id: 'u1', display_name: 'x', email: 'x@y.kr', is_active: false }));

    const outcome = await changeStatus('u1', false);

    expect(call).toHaveBeenCalledWith('/api/users/u1/status', {
      method: 'PATCH',
      body: { is_active: false },
    });
    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;
    expect(outcome.data.isActive).toBe(false);
  });
});

describe('역할', () => {
  it('엔진이 정의한 여섯 가지뿐이다', () => {
    expect(ROLES).toHaveLength(6);
    expect(isRole('ANALYST')).toBe(true);
    expect(isRole('OWNER')).toBe(false);
    expect(isRole(null)).toBe(false);
  });

  it('역할마다 무엇을 할 수 있는지 설명이 있다', () => {
    /** 이름만 보고는 고를 수 없다. `LAB_ADMIN` 과 `SUPER_ADMIN` 의 차이가 이름에 없다. */
    for (const role of ROLES) {
      expect(ROLE_LABELS[role].label).toBeTruthy();
      expect(ROLE_LABELS[role].note).toBeTruthy();
    }
  });
});

describe('엔진 경로', () => {
  /**
   * 실제로 배포하고 나서야 잡은 결함. `/users` 로 불렀는데 `callConsoleApi` 는 받은
   * 경로를 엔진 주소 뒤에 **그대로 잇기만** 한다 — 접두사를 붙여 주지 않는다. 그래서
   * 엔진이 404 를 돌려줬고 화면에는 영어로 "Not Found" 가 떴다. 목록도 초대도 전부
   * 죽었는데 화면 자체는 멀쩡해 보여서, 무엇이 틀렸는지 알기 어려웠다.
   *
   * 다른 화면들은 처음부터 `/api/customers` 처럼 붙여 부르고 있었다. 나만 빠뜨렸고,
   * 그 사실을 잡아 줄 검사가 없었다.
   */
  it('모든 호출이 /api 로 시작한다', async () => {
    call.mockResolvedValue(ok([]));
    await listMembers();
    await inviteMember({ email: 'a@b.kr', displayName: 'x', role: 'ANALYST' });
    await reinvite('u1');
    await changeRole('u1', 'ANALYST');
    await changeStatus('u1', true);

    expect(call).toHaveBeenCalledTimes(5);
    for (const [path] of call.mock.calls) {
      expect(path).toMatch(/^\/api\/users(\/|$)/);
    }
  });
});
