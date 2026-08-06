// @vitest-environment node
/**
 * 한국 관측점.
 *
 * 이 창구는 **주소를 받아 남의 서버에 요청을 보낸다.** 잘못 만들면 우리 이름으로 아무나
 * 어디든 두드릴 수 있는 도구가 되고, 클라우드 메타데이터(`169.254.169.254`)까지 닿으면
 * 자격증명이 새어 나간다.
 *
 * 그래서 여기서 지키는 것은 "잘 받아 오는가" 가 아니라 **막아야 할 것을 막는가** 다:
 * 열쇠 없는 호출, 사설·루프백·메타데이터 주소, 리다이렉트 자동 추종.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const lookup = vi.fn();
vi.mock('node:dns/promises', () => ({ lookup: (...args: unknown[]) => lookup(...args) }));

// 나가는 요청은 `fetchPinned` 하나로 모였다. 여기서 그것을 가로채면 **시험이 절대
// 바깥으로 나가지 않는다.** 예전에는 전역 `fetch` 를 바꿔 두었는데, 나가는 경로가
// 바뀌자 가짜가 무력해지면서 시험이 진짜 venomad.com 을 다녀왔다(2026-08-06).
// 무엇을 가로채야 하는지 헷갈리지 않도록, 이 시험은 모듈 경계 하나만 본다.
const pinned = vi.fn();
vi.mock('@/lib/pinned-fetch', () => ({
  fetchPinned: (...args: unknown[]) => pinned(...args),
}));

const { POST } = await import('./route');

/** `fetchPinned` 가 돌려주는 모양. 기본은 빈 200. */
function reply(
  overrides: Partial<{
    status: number;
    headers: Record<string, string>;
    body: Uint8Array;
    truncated: boolean;
  }> = {},
) {
  return {
    status: 200,
    headers: { 'content-type': 'text/html' },
    body: new Uint8Array(),
    truncated: false,
    ...overrides,
  };
}

const TOKEN = 'test-token-value';

function post(body: unknown, token: string | null = TOKEN): Request {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token !== null) headers['x-veo-egress-token'] = token;
  return new Request('https://veo.test/api/egress', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.stubEnv('VEO_EGRESS_TOKEN', TOKEN);
  lookup.mockReset();
  pinned.mockReset();
  pinned.mockResolvedValue(reply());
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('열쇠', () => {
  it('열쇠가 없으면 거절한다', async () => {
    const response = await POST(post({ url: 'https://a.example', userAgent: 'x' }, null));
    expect(response.status).toBe(401);
  });

  it('열쇠가 틀리면 거절한다', async () => {
    const response = await POST(post({ url: 'https://a.example', userAgent: 'x' }, 'wrong'));
    expect(response.status).toBe(401);
  });

  it('열쇠가 설정되지 않은 배포에서는 창구 자체가 없다', async () => {
    vi.stubEnv('VEO_EGRESS_TOKEN', '');
    const response = await POST(post({ url: 'https://a.example', userAgent: 'x' }));
    expect(response.status).toBe(404);
  });
});

describe('나가면 안 되는 주소', () => {
  it.each([
    ['클라우드 메타데이터', '169.254.169.254'],
    ['루프백', '127.0.0.1'],
    ['사설 10/8', '10.0.0.5'],
    ['사설 172.16/12', '172.20.1.1'],
    ['사설 192.168/16', '192.168.0.1'],
    ['통신사 내부(CGNAT)', '100.100.1.1'],
    ['IPv6 루프백', '::1'],
    ['IPv6 사설', 'fd00::1'],
    ['IPv4 를 감싼 사설 IPv6', '::ffff:10.0.0.1'],
  ])('%s 는 거절한다', async (_name, address) => {
    lookup.mockResolvedValue([{ address, family: address.includes(':') ? 6 : 4 }]);
    const response = await POST(post({ url: 'https://inside.example', userAgent: 'x' }));
    expect(response.status).toBe(403);
  });

  it('공개 주소 하나라도 사설이면 거절한다', async () => {
    lookup.mockResolvedValue([
      { address: '203.245.24.59', family: 4 },
      { address: '127.0.0.1', family: 4 },
    ]);
    const response = await POST(post({ url: 'https://mixed.example', userAgent: 'x' }));
    expect(response.status).toBe(403);
  });

  it('이름을 못 풀면 거절한다', async () => {
    lookup.mockRejectedValue(new Error('ENOTFOUND'));
    const response = await POST(post({ url: 'https://nowhere.example', userAgent: 'x' }));
    expect(response.status).toBe(400);
  });

  it.each(['file:///etc/passwd', 'ftp://a.example/x', 'gopher://a.example'])(
    '%s 처럼 http 가 아닌 주소는 거절한다',
    async (url) => {
      const response = await POST(post({ url, userAgent: 'x' }));
      expect(response.status).toBe(400);
    },
  );
});

describe('받아 오기', () => {
  beforeEach(() => {
    lookup.mockResolvedValue([{ address: '203.245.24.59', family: 4 }]);
  });

  it('검사한 바로 그 주소로 접속한다', async () => {
    /**
     * 이 시험이 이 파일의 핵심이다. 위에서 주소를 검사해 놓고 접속할 때 이름을 다시
     * 풀면, 그 사이에 주소가 바뀔 수 있다(DNS 재바인딩). 검사와 접속이 **같은 주소**를
     * 보는지 여기서 못박는다.
     */
    lookup.mockResolvedValue([{ address: '203.245.24.59', family: 4 }]);

    await POST(post({ url: 'https://venomad.com/a?b=1', userAgent: 'VEO-Bot/1.0' }));

    expect(pinned).toHaveBeenCalledTimes(1);
    expect(pinned.mock.calls[0]?.[0]).toMatchObject({
      address: '203.245.24.59',
      hostname: 'venomad.com',
    });
  });

  it('받은 바이트를 그대로 돌려준다', async () => {
    const body = new TextEncoder().encode('<html><title>베놈애드</title></html>');
    pinned.mockResolvedValue(reply({ body }));

    const response = await POST(post({ url: 'https://venomad.com', userAgent: 'VEO-Bot/1.0' }));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(Buffer.from(payload.bodyBase64, 'base64')).toEqual(Buffer.from(body));
    expect(payload.truncated).toBe(false);
  });

  it('리다이렉트를 따라가지 않는다', async () => {
    /** 따라가면 다음 홉이 API 쪽 가드의 재검증을 건너뛴다 — 경유가 구멍이 되는 자리다. */
    pinned.mockResolvedValue(reply({ status: 301, headers: { location: '/next' } }));

    const response = await POST(post({ url: 'https://venomad.com', userAgent: 'VEO-Bot/1.0' }));
    const payload = await response.json();

    expect(payload.status).toBe(301);
    expect(payload.headers.location).toBe('/next');
  });

  it('잘렸으면 잘렸다고 말한다', async () => {
    pinned.mockResolvedValue(reply({ body: new Uint8Array(10), truncated: true }));

    const payload = await (
      await POST(post({ url: 'https://venomad.com', userAgent: 'VEO-Bot/1.0' }))
    ).json();

    expect(payload.truncated).toBe(true);
  });

  it('쿠키·인증 헤더는 돌려주지 않는다', async () => {
    pinned.mockResolvedValue(
      reply({ headers: { 'content-type': 'text/html', 'set-cookie': 'SESSION=secret' } }),
    );

    const payload = await (
      await POST(post({ url: 'https://venomad.com', userAgent: 'VEO-Bot/1.0' }))
    ).json();

    expect(JSON.stringify(payload.headers)).not.toContain('secret');
    expect(payload.headers['set-cookie']).toBeUndefined();
  });
});
