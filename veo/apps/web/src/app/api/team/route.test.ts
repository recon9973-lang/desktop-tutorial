// @vitest-environment node
/**
 * 초대 링크가 화면까지 도착하는가.
 *
 * 한동안 도착하지 않았다. 경로는 `inviteUrl` 로 내보내는데 화면은 `invite_url` 을 읽어서,
 * 링크가 조용히 빈 문자열이 됐다. 발급은 실제로 됐고 성공 문구도 떴으므로 화면만 보고는
 * 알 수 없었다 — 관리자가 빈 값을 복사해 전달하는 실패였다.
 *
 * 그래서 여기서 확인하는 것은 "경로가 200 을 준다" 가 아니라, **경로가 낸 본문을 화면이
 * 쓰는 바로 그 함수(`readInvite`)로 읽었을 때 링크가 나오는가** 이다. 두 쪽 중 한쪽만
 * 이름을 바꾸면 이 시험이 깨진다.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const inviteMember = vi.fn();
const reinvite = vi.fn();

vi.mock('@/lib/team', async () => {
  // 역할 상수는 실제 구현을 쓴다 — 검증 문턱까지 흉내내면 시험이 거짓으로 통과한다.
  const roles = await import('@/app/(console)/console/team/roles');
  return {
    isRole: roles.isRole,
    inviteMember,
    reinvite,
    changeRole: vi.fn(),
    changeStatus: vi.fn(),
  };
});

const { POST } = await import('./route');
const { readInvite } = await import('@/app/(console)/console/team/invite-wire');

const LINK = 'https://veo.seokorea.org/invite/abcdefghijklmnopqrstuvwxyz012345';
const EXPIRES = '2026-08-06T00:00:00Z';
const USER = '3f2a1b0c-4d5e-6f70-8192-a3b4c5d6e7f8';

function post(body: unknown): Request {
  return new Request('https://console.veo.test/api/team', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('발급한 링크가 화면이 읽는 이름으로 도착한다', () => {
  it('새 구성원 초대 — 화면의 readInvite 로 링크가 나온다', async () => {
    inviteMember.mockResolvedValue({
      ok: true,
      data: { inviteUrl: LINK, expiresAt: EXPIRES },
    });

    const response = await POST(
      post({ email: 'someone@example.com', displayName: '홍길동', role: 'SUPER_ADMIN' }),
    );
    const issued = readInvite(await response.json());

    expect(response.status).toBe(200);
    expect(issued.inviteUrl).toBe(LINK);
    expect(issued.expiresAt).toBe(EXPIRES);
  });

  it('재발송 — 같은 이름으로 도착한다', async () => {
    reinvite.mockResolvedValue({
      ok: true,
      data: { inviteUrl: LINK, expiresAt: EXPIRES },
    });

    const response = await POST(post({ userId: USER }));
    const issued = readInvite(await response.json());

    expect(reinvite).toHaveBeenCalledWith(USER);
    expect(issued.inviteUrl).toBe(LINK);
  });
});

describe('링크를 못 받은 것을 성공으로 접지 않는다', () => {
  it('엔진이 링크를 비워 보내면 화면이 읽는 값도 빈 문자열이다', async () => {
    // 화면은 이 빈 값을 보고 "받지 못했습니다" 라고 말한다. 여기서 확인하는 것은
    // 빈 값이 링크처럼 생긴 무언가로 둔갑하지 않는다는 것.
    inviteMember.mockResolvedValue({ ok: true, data: { inviteUrl: '', expiresAt: '' } });

    const response = await POST(
      post({ email: 'a@b.co', displayName: '홍길동', role: 'ANALYST' }),
    );

    expect(readInvite(await response.json()).inviteUrl).toBe('');
  });

  it('거절은 링크 자리를 만들지 않는다', async () => {
    inviteMember.mockResolvedValue({
      ok: false,
      reason: 'REFUSED',
      message: '이미 등록된 이메일입니다.',
    });

    const response = await POST(
      post({ email: 'a@b.co', displayName: '홍길동', role: 'ANALYST' }),
    );
    const body = (await response.json()) as Record<string, unknown>;

    expect(response.status).toBe(400);
    expect(body['message']).toBe('이미 등록된 이메일입니다.');
    expect(readInvite(body).inviteUrl).toBe('');
  });
});
