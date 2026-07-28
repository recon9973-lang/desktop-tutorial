// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from 'vitest';

const login = vi.fn();
const logout = vi.fn();
const me = vi.fn();

vi.mock('@/lib/auth-api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/auth-api')>('@/lib/auth-api');
  return { ...actual, getAuthApi: () => ({ login, logout, me }) };
});

const { POST } = await import('./route');
const { CONSOLE_SESSION_COOKIE } = await import('@/lib/session-cookie');

function request(cookie?: string): Request {
  return new Request('https://console.veo.test/api/session/logout', {
    method: 'POST',
    ...(cookie === undefined ? {} : { headers: { cookie } }),
  });
}

beforeEach(() => {
  logout.mockReset();
  logout.mockResolvedValue({ ok: true, value: null });
});

describe('POST /api/session/logout', () => {
  it('clears the session cookie', async () => {
    const response = await POST(request(`${CONSOLE_SESSION_COOKIE}=tok`));
    const cookie = (response.headers.get('set-cookie') ?? '').toLowerCase();

    expect(cookie).toContain(`${CONSOLE_SESSION_COOKIE}=`);
    expect(cookie).toContain('max-age=0');
    expect(cookie).toContain('httponly');
    expect(cookie).toContain('path=/');
  });

  it('redirects back to the login page so the browser lands somewhere real', async () => {
    const response = await POST(request(`${CONSOLE_SESSION_COOKIE}=tok`));
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe('https://console.veo.test/login');
  });

  it('asks the backend to revoke the token it held', async () => {
    await POST(request(`${CONSOLE_SESSION_COOKIE}=tok`));
    expect(logout).toHaveBeenCalledWith('tok');
  });

  it('still clears the cookie when the backend refuses to revoke', async () => {
    logout.mockResolvedValue({ ok: false, reason: 'UNAVAILABLE', retryAfterSeconds: null });
    const response = await POST(request(`${CONSOLE_SESSION_COOKIE}=tok`));

    expect(response.status).toBe(303);
    expect((response.headers.get('set-cookie') ?? '').toLowerCase()).toContain('max-age=0');
  });

  it('is harmless when there was no session to begin with', async () => {
    const response = await POST(request());
    expect(logout).not.toHaveBeenCalled();
    expect(response.status).toBe(303);
  });
});
