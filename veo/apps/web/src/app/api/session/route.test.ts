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

const TOKEN = 'super-secret-access-token';

function request(body: unknown): Request {
  return new Request('https://console.veo.test/api/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function setCookieHeader(response: Response): string {
  return response.headers.get('set-cookie') ?? '';
}

beforeEach(() => {
  login.mockReset();
  logout.mockReset();
  me.mockReset();
});

describe('POST /api/session — success', () => {
  beforeEach(() => {
    login.mockResolvedValue({
      ok: true,
      value: { accessToken: TOKEN, expiresInSeconds: 3600 },
    });
  });

  it('sets the token in an httpOnly, Secure, SameSite=Lax cookie', async () => {
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));
    const cookie = setCookieHeader(response);

    expect(response.status).toBe(200);
    expect(cookie).toContain(`${CONSOLE_SESSION_COOKIE}=${TOKEN}`);
    expect(cookie.toLowerCase()).toContain('httponly');
    expect(cookie.toLowerCase()).toContain('secure');
    expect(cookie.toLowerCase()).toContain('samesite=lax');
    expect(cookie.toLowerCase()).toContain('path=/');
  });

  it('bounds the cookie by the lifetime the backend stated', async () => {
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));
    expect(setCookieHeader(response).toLowerCase()).toContain('max-age=3600');
  });

  it('never returns the token in the response body', async () => {
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));
    const text = await response.text();
    expect(text).not.toContain(TOKEN);
    expect(JSON.parse(text)).toEqual({ ok: true, redirectTo: '/console/dashboard' });
  });

  it('honours a safe destination', async () => {
    const response = await POST(
      request({ email: 'a@example.com', password: 'b', next: '/console/issues' }),
    );
    await expect(response.json()).resolves.toEqual({
      ok: true,
      redirectTo: '/console/issues',
    });
  });

  it('refuses to redirect off-site', async () => {
    const response = await POST(
      request({ email: 'a@example.com', password: 'b', next: 'https://evil.example' }),
    );
    await expect(response.json()).resolves.toEqual({
      ok: true,
      redirectTo: '/console/dashboard',
    });
  });

  it('trims and lowercases the email before sending it on', async () => {
    await POST(request({ email: '  Analyst@Example.COM ', password: 'b' }));
    expect(login).toHaveBeenCalledWith({
      email: 'analyst@example.com',
      password: 'b',
    });
  });

  it('does not trim the password', async () => {
    await POST(request({ email: 'a@example.com', password: '  spaced  ' }));
    expect(login).toHaveBeenCalledWith({
      email: 'a@example.com',
      password: '  spaced  ',
    });
  });
});

describe('POST /api/session — failure', () => {
  it('returns 401 and the generic reason for rejected credentials', async () => {
    login.mockResolvedValue({
      ok: false,
      reason: 'INVALID_CREDENTIALS',
      retryAfterSeconds: null,
    });
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      ok: false,
      reason: 'INVALID_CREDENTIALS',
    });
    expect(setCookieHeader(response)).not.toContain(TOKEN);
  });

  it('returns 429 and the retry delay on lockout', async () => {
    login.mockResolvedValue({ ok: false, reason: 'LOCKED_OUT', retryAfterSeconds: 120 });
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));

    expect(response.status).toBe(429);
    expect(response.headers.get('Retry-After')).toBe('120');
    await expect(response.json()).resolves.toEqual({
      ok: false,
      reason: 'LOCKED_OUT',
      retryAfterSeconds: 120,
    });
  });

  it('returns 503 when the backend is unreachable, and signs nobody in', async () => {
    login.mockResolvedValue({ ok: false, reason: 'UNAVAILABLE', retryAfterSeconds: null });
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({ ok: false, reason: 'UNAVAILABLE' });
    expect(setCookieHeader(response)).toBe('');
  });

  it('returns 503 when auth is not configured, and signs nobody in', async () => {
    login.mockResolvedValue({
      ok: false,
      reason: 'NOT_CONFIGURED',
      retryAfterSeconds: null,
    });
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      ok: false,
      reason: 'NOT_CONFIGURED',
    });
  });

  it('rejects a missing field without asking the backend, and without saying which', async () => {
    const response = await POST(request({ email: '', password: '' }));

    expect(login).not.toHaveBeenCalled();
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      ok: false,
      reason: 'INVALID_CREDENTIALS',
    });
  });

  it('rejects a body that is not JSON', async () => {
    const response = await POST(
      new Request('https://console.veo.test/api/session', {
        method: 'POST',
        body: 'not json',
      }),
    );

    expect(login).not.toHaveBeenCalled();
    expect(response.status).toBe(401);
  });

  it('never caches an auth response', async () => {
    login.mockResolvedValue({
      ok: false,
      reason: 'INVALID_CREDENTIALS',
      retryAfterSeconds: null,
    });
    const response = await POST(request({ email: 'a@example.com', password: 'b' }));
    expect(response.headers.get('Cache-Control')).toContain('no-store');
  });
});
