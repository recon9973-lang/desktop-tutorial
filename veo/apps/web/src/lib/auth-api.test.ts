import { describe, expect, it, vi } from 'vitest';

import { createAuthApi, resolveAuthApiBaseUrl } from './auth-api';

const BASE_URL = 'https://api.veo.test';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

function envelope(data: unknown) {
  return { data, error: null, meta: {} };
}

function errorEnvelope(code: string, message: string) {
  return {
    data: null,
    error: { code, message, field_errors: [], retryable: false },
    meta: {},
  };
}

function apiWith(fetchImpl: typeof globalThis.fetch) {
  return createAuthApi({ baseUrl: BASE_URL, fetch: fetchImpl });
}

const LOGIN_OK = envelope({
  access_token: 'secret-token-value',
  expires_in: 3600,
});

const IDENTITY_OK = envelope({
  user_id: '6d1f6e5c-0000-4000-8000-000000000001',
  organization_id: '6d1f6e5c-0000-4000-8000-000000000002',
  display_name: '이재훈',
  email: 'analyst@example.com',
  roles: ['ANALYST'],
  permissions: ['project:read', 'issue:write', 'not-a-real-permission'],
});

describe('resolveAuthApiBaseUrl', () => {
  it('prefers the server-only variable', () => {
    expect(
      resolveAuthApiBaseUrl({
        VEO_API_BASE_URL: 'https://server.example',
        NEXT_PUBLIC_VEO_API_BASE_URL: 'https://public.example',
      }),
    ).toBe('https://server.example');
  });

  it('falls back to the public variable', () => {
    expect(
      resolveAuthApiBaseUrl({ NEXT_PUBLIC_VEO_API_BASE_URL: 'https://public.example' }),
    ).toBe('https://public.example');
  });

  it('returns null rather than guessing a host', () => {
    expect(resolveAuthApiBaseUrl({})).toBeNull();
    expect(resolveAuthApiBaseUrl({ VEO_API_BASE_URL: '   ' })).toBeNull();
  });

  it('strips a trailing slash so paths never double up', () => {
    expect(resolveAuthApiBaseUrl({ VEO_API_BASE_URL: 'https://a.example/' })).toBe(
      'https://a.example',
    );
  });
});

describe('createAuthApi — login', () => {
  it('posts the credentials and returns the access token', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(LOGIN_OK));
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'analyst@example.com',
      password: 'correct horse',
    });

    expect(result).toEqual({
      ok: true,
      value: { accessToken: 'secret-token-value', expiresInSeconds: 3600 },
    });

    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${BASE_URL}/api/auth/login`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({
      email: 'analyst@example.com',
      password: 'correct horse',
    });
  });

  it('never lets the response be cached', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(LOGIN_OK));
    await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.cache).toBe('no-store');
  });

  it.each([
    [400, 'VALIDATION_FAILED'],
    [401, 'UNAUTHENTICATED'],
    [403, 'PERMISSION_DENIED'],
    [404, 'NOT_FOUND'],
  ])(
    'collapses a %i %s into one indistinguishable failure',
    async (status, code) => {
      const fetchImpl = vi.fn(async () =>
        jsonResponse(errorEnvelope(code, `계정 상태: ${code}`), { status }),
      );
      const result = await apiWith(
        fetchImpl as unknown as typeof globalThis.fetch,
      ).login({ email: 'a@example.com', password: 'b' });

      expect(result.ok).toBe(false);
      if (result.ok) return;
      expect(result.reason).toBe('INVALID_CREDENTIALS');
      // The upstream message could hint at whether the account exists.
      expect(JSON.stringify(result)).not.toContain('계정 상태');
    },
  );

  it('reports lockout separately, with the retry delay', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(errorEnvelope('RATE_LIMITED', 'too many attempts'), {
        status: 429,
        headers: { 'Retry-After': '120' },
      }),
    );
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });

    expect(result).toEqual({ ok: false, reason: 'LOCKED_OUT', retryAfterSeconds: 120 });
  });

  it('reports a server fault as a server fault', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(errorEnvelope('INTERNAL_ERROR', 'boom'), { status: 500 }),
    );
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });
    expect(result).toEqual({ ok: false, reason: 'SERVER_ERROR', retryAfterSeconds: null });
  });

  it('reports an unreachable backend instead of pretending the login worked', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('fetch failed');
    });
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });
    expect(result).toEqual({ ok: false, reason: 'UNAVAILABLE', retryAfterSeconds: null });
  });

  it('treats an unparseable body as a server fault, not a success', async () => {
    const fetchImpl = vi.fn(
      async () => new Response('<html>gateway</html>', { status: 200 }),
    );
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });
    expect(result.ok).toBe(false);
  });

  it('treats a 200 with no token as a server fault, not a success', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(envelope({ expires_in: 60 })));
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });
    expect(result.ok).toBe(false);
  });

  it('accepts a grant with no stated lifetime', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(envelope({ access_token: 'abc' })));
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).login({
      email: 'a@example.com',
      password: 'b',
    });
    expect(result).toEqual({
      ok: true,
      value: { accessToken: 'abc', expiresInSeconds: null },
    });
  });
});

describe('createAuthApi — me', () => {
  it('sends the bearer token and maps the identity', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(IDENTITY_OK));
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).me(
      'secret-token-value',
    );

    expect(result).toEqual({
      ok: true,
      value: {
        userId: '6d1f6e5c-0000-4000-8000-000000000001',
        organizationId: '6d1f6e5c-0000-4000-8000-000000000002',
        displayName: '이재훈',
        email: 'analyst@example.com',
        roles: ['ANALYST'],
        // The unrecognised entry is discarded rather than trusted.
        permissions: ['project:read', 'issue:write'],
      },
    });

    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${BASE_URL}/api/auth/me`);
    expect(new Headers(init.headers).get('Authorization')).toBe(
      'Bearer secret-token-value',
    );
  });

  it('drops a role the contract does not define', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(
        envelope({
          user_id: 'u',
          organization_id: 'o',
          display_name: 'n',
          email: 'e@example.com',
          roles: ['ANALYST', 'ROOT'],
          permissions: [],
        }),
      ),
    );
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).me('t');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.roles).toEqual(['ANALYST']);
  });

  it('reports an expired or rejected token distinctly', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(errorEnvelope('UNAUTHENTICATED', 'nope'), { status: 401 }),
    );
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).me('t');
    expect(result).toEqual({
      ok: false,
      reason: 'SESSION_EXPIRED',
      retryAfterSeconds: null,
    });
  });

  it('reports an unreachable backend rather than an empty identity', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('ECONNREFUSED');
    });
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).me('t');
    expect(result).toEqual({ ok: false, reason: 'UNAVAILABLE', retryAfterSeconds: null });
  });
});

describe('createAuthApi — logout', () => {
  it('tells the backend to revoke the token', async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 204 }));
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).logout(
      'secret-token-value',
    );

    expect(result.ok).toBe(true);
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${BASE_URL}/api/auth/logout`);
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('Authorization')).toBe(
      'Bearer secret-token-value',
    );
  });

  it('does not throw when the backend is unreachable', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('down');
    });
    const result = await apiWith(fetchImpl as unknown as typeof globalThis.fetch).logout(
      't',
    );
    expect(result.ok).toBe(false);
  });
});

describe('createAuthApi — unconfigured', () => {
  it('fails every call instead of authenticating anyone', async () => {
    const fetchImpl = vi.fn();
    const api = createAuthApi({
      baseUrl: null,
      fetch: fetchImpl as unknown as typeof globalThis.fetch,
    });

    const login = await api.login({ email: 'a@example.com', password: 'b' });
    const me = await api.me('t');
    const logout = await api.logout('t');

    expect(login).toEqual({ ok: false, reason: 'NOT_CONFIGURED', retryAfterSeconds: null });
    expect(me.ok).toBe(false);
    expect(logout.ok).toBe(false);
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
