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

// Shaped like `MePayload` in the committed OpenAPI document — the person and the
// organization are nested, not flattened. This fixture previously used a flattened
// shape the API never sent, so every test here agreed with the client and none of
// them agreed with the server. That is how the parsing bug reached production.
const IDENTITY_OK = envelope({
  user: {
    id: '6d1f6e5c-0000-4000-8000-000000000001',
    email: 'analyst@example.com',
    display_name: '이재훈',
  },
  organization: {
    id: '6d1f6e5c-0000-4000-8000-000000000002',
    slug: 'venom',
    name: '베놈',
  },
  roles: ['ANALYST'],
  permissions: ['project:read', 'issue:write', 'not-a-real-permission'],
  session_id: '6d1f6e5c-0000-4000-8000-000000000003',
  session_expires_at: '2026-08-11T00:00:00Z',
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
          user: { id: 'u', email: 'e@example.com', display_name: 'n' },
          organization: { id: 'o', slug: 's', name: 'n' },
          roles: ['ANALYST', 'ROOT'],
          permissions: [],
          session_id: 'sid',
          session_expires_at: '2026-08-11T00:00:00Z',
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

describe('me() against the shape the API actually returns', () => {
  /**
   * Built from `MePayload` in the committed OpenAPI document, not from what this
   * client wishes it received.
   *
   * The bug this guards against shipped to production: the client read `user_id`
   * and `organization_id` from the top level, `MePayload` nests them under `user`
   * and `organization`, so every call returned SERVER_ERROR. The console reads
   * that as "no session" and redirects to sign-in — so signing in appeared to do
   * nothing at all, while the API had issued a session and logged a success.
   *
   * Every existing test in this file passed throughout, because they all fed the
   * client the flattened shape it expected. A mock that agrees with the code it
   * tests cannot find a disagreement with the server.
   */
  const ME_PAYLOAD = {
    data: {
      user: {
        id: '11111111-1111-1111-1111-111111111111',
        email: 'owner@example.test',
        display_name: '이재훈',
      },
      organization: { id: '22222222-2222-2222-2222-222222222222', slug: 'venom', name: '베놈' },
      roles: ['SUPER_ADMIN'],
      permissions: ['user:read', 'user:manage'],
      session_id: '33333333-3333-3333-3333-333333333333',
      session_expires_at: '2026-08-11T00:00:00Z',
    },
    error: null,
  };

  function apiReturning(body: unknown) {
    return createAuthApi({
      baseUrl: 'https://api.example',
      fetch: (async () =>
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })) as typeof globalThis.fetch,
    });
  }

  it('reads the identity out of the nested payload', async () => {
    const result = await apiReturning(ME_PAYLOAD).me('a-token');

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.userId).toBe('11111111-1111-1111-1111-111111111111');
    expect(result.value.organizationId).toBe('22222222-2222-2222-2222-222222222222');
    expect(result.value.email).toBe('owner@example.test');
    expect(result.value.displayName).toBe('이재훈');
    expect(result.value.roles).toContain('SUPER_ADMIN');
    expect(result.value.permissions).toContain('user:manage');
  });

  it('falls back to the address when the account has no display name', async () => {
    const withoutName = {
      ...ME_PAYLOAD,
      data: { ...ME_PAYLOAD.data, user: { ...ME_PAYLOAD.data.user, display_name: '' } },
    };
    const result = await apiReturning(withoutName).me('a-token');

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.displayName).toBe('owner@example.test');
  });

  it('refuses a flattened payload rather than half-reading it', async () => {
    // The shape this client used to expect. If the API ever changes to it, that is
    // a contract change and should fail loudly here, not degrade into a redirect.
    const flattened = {
      data: {
        user_id: '11111111-1111-1111-1111-111111111111',
        organization_id: '22222222-2222-2222-2222-222222222222',
        email: 'owner@example.test',
        roles: ['SUPER_ADMIN'],
        permissions: [],
      },
      error: null,
    };
    const result = await apiReturning(flattened).me('a-token');

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.reason).toBe('SERVER_ERROR');
  });
});
