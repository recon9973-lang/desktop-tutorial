// @vitest-environment node
/**
 * 리포트 내보내기 통로 — E7.
 *
 * 1. 검증 없는 통과는 없다: 형식·식별자가 어긋나면 엔진까지 가지 않는다.
 * 2. 토큰 없는 호출은 401 — 이 통로도 콘솔의 경계 안이다.
 * 3. HTML 은 열람이므로 inline + sandbox, 표 형식은 첨부 그대로.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const cookieStore = new Map<string, { value: string }>();

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => cookieStore.get(name),
  }),
}));

const { GET } = await import('./route');
const { CONSOLE_SESSION_COOKIE } = await import('@/lib/session-cookie');

const REPORT = '0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0';

function request(query: string): Request {
  return new Request(`https://console.veo.test/api/report-export?${query}`);
}

beforeEach(() => {
  cookieStore.clear();
  vi.stubEnv('VEO_API_BASE_URL', 'https://engine.veo.test');
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('검증이 엔진보다 먼저다', () => {
  it('모르는 형식은 422 — 엔진 호출 없이', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    cookieStore.set(CONSOLE_SESSION_COOKIE, { value: 'token' });

    const response = await GET(request(`report=${REPORT}&version=1&format=pdf`));

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('식별자가 UUID 가 아니면 422', async () => {
    cookieStore.set(CONSOLE_SESSION_COOKIE, { value: 'token' });
    const response = await GET(request('report=../../etc&version=1&format=html'));
    expect(response.status).toBe(422);
  });

  it('토큰이 없으면 401', async () => {
    const response = await GET(request(`report=${REPORT}&version=1&format=html`));
    expect(response.status).toBe(401);
  });
});

describe('형식별 전달', () => {
  it('HTML 은 inline + sandbox 로 열람된다', async () => {
    cookieStore.set(CONSOLE_SESSION_COOKIE, { value: 'token' });
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('<!doctype html><title>보고서</title>', {
          status: 200,
          headers: {
            'content-type': 'text/html; charset=utf-8',
            'content-disposition': 'attachment; filename="report.html"',
          },
        }),
      ),
    );

    const response = await GET(request(`report=${REPORT}&version=3&format=html`));

    expect(response.status).toBe(200);
    expect(response.headers.get('content-disposition')).toBe('inline');
    expect(response.headers.get('content-security-policy')).toBe('sandbox');
  });

  it('CSV 는 엔진의 첨부 파일명을 그대로 지닌다', async () => {
    cookieStore.set(CONSOLE_SESSION_COOKIE, { value: 'token' });
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('a,b\n1,2\n', {
          status: 200,
          headers: {
            'content-type': 'text/csv; charset=utf-8',
            'content-disposition': 'attachment; filename="report-v3.csv"',
          },
        }),
      ),
    );

    const response = await GET(request(`report=${REPORT}&version=3&format=csv`));

    expect(response.status).toBe(200);
    expect(response.headers.get('content-disposition')).toContain('report-v3.csv');
  });
});
