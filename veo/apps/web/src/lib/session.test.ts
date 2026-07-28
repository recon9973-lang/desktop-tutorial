import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const cookieStore = { get: vi.fn() };
const redirect = vi.fn((to: string) => {
  throw new Error(`NEXT_REDIRECT:${to}`);
});
const headerStore = { get: vi.fn() };

vi.mock('next/headers', () => ({
  cookies: async () => cookieStore,
  headers: async () => headerStore,
}));

vi.mock('next/navigation', () => ({
  redirect: (to: string) => redirect(to),
}));

const meMock = vi.fn();
vi.mock('./auth-api', async () => {
  const actual = await vi.importActual<typeof import('./auth-api')>('./auth-api');
  return {
    ...actual,
    getAuthApi: () => ({
      login: vi.fn(),
      logout: vi.fn(),
      me: meMock,
    }),
  };
});

const {
  CONSOLE_SESSION_COOKIE,
  AuthUnavailableError,
  readConsoleSession,
  requireConsoleSession,
  toPublicIdentity,
} = await import('./session');

const IDENTITY = {
  userId: 'u-1',
  organizationId: 'o-1',
  displayName: '이재훈',
  email: 'analyst@example.com',
  roles: ['ANALYST'] as const,
  permissions: ['project:read', 'issue:write'] as const,
};

beforeEach(() => {
  cookieStore.get.mockReset();
  headerStore.get.mockReset();
  redirect.mockClear();
  meMock.mockReset();
  headerStore.get.mockReturnValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('readConsoleSession', () => {
  it('returns null when the cookie is absent', async () => {
    cookieStore.get.mockReturnValue(undefined);
    await expect(readConsoleSession()).resolves.toBeNull();
    expect(meMock).not.toHaveBeenCalled();
  });

  it('returns null when the cookie is blank', async () => {
    cookieStore.get.mockReturnValue({ value: '   ' });
    await expect(readConsoleSession()).resolves.toBeNull();
  });

  it('reads the cookie under the agreed name', async () => {
    cookieStore.get.mockReturnValue({ value: 'tok' });
    meMock.mockResolvedValue({ ok: true, value: IDENTITY });
    await readConsoleSession();
    expect(cookieStore.get).toHaveBeenCalledWith(CONSOLE_SESSION_COOKIE);
  });

  it('resolves the identity from the backend, not from the cookie contents', async () => {
    cookieStore.get.mockReturnValue({ value: 'tok' });
    meMock.mockResolvedValue({ ok: true, value: IDENTITY });

    const session = await readConsoleSession();

    expect(meMock).toHaveBeenCalledWith('tok');
    expect(session?.displayName).toBe('이재훈');
    expect(session?.permissions).toEqual(['project:read', 'issue:write']);
    expect(session?.token).toBe('tok');
  });

  it('treats a rejected token as no session', async () => {
    cookieStore.get.mockReturnValue({ value: 'stale' });
    meMock.mockResolvedValue({ ok: false, reason: 'SESSION_EXPIRED', retryAfterSeconds: null });
    await expect(readConsoleSession()).resolves.toBeNull();
  });

  it('raises rather than inventing a session when the backend is unreachable', async () => {
    cookieStore.get.mockReturnValue({ value: 'tok' });
    meMock.mockResolvedValue({ ok: false, reason: 'UNAVAILABLE', retryAfterSeconds: null });
    await expect(readConsoleSession()).rejects.toBeInstanceOf(AuthUnavailableError);
  });

  it('raises rather than inventing a session when auth is not configured', async () => {
    cookieStore.get.mockReturnValue({ value: 'tok' });
    meMock.mockResolvedValue({
      ok: false,
      reason: 'NOT_CONFIGURED',
      retryAfterSeconds: null,
    });
    await expect(readConsoleSession()).rejects.toBeInstanceOf(AuthUnavailableError);
  });
});

describe('requireConsoleSession', () => {
  it('redirects to the login page when there is no session', async () => {
    cookieStore.get.mockReturnValue(undefined);
    await expect(requireConsoleSession()).rejects.toThrow('NEXT_REDIRECT:/login');
    expect(redirect).toHaveBeenCalledWith('/login');
  });

  it('carries the requested console path through as ?next=', async () => {
    cookieStore.get.mockReturnValue(undefined);
    headerStore.get.mockImplementation((name: string) =>
      name === 'x-veo-pathname' ? '/console/issues?severity=BLOCKER' : null,
    );

    await expect(requireConsoleSession()).rejects.toThrow('NEXT_REDIRECT:');
    expect(redirect).toHaveBeenCalledWith(
      '/login?next=%2Fconsole%2Fissues%3Fseverity%3DBLOCKER',
    );
  });

  it('never forwards an off-site destination', async () => {
    cookieStore.get.mockReturnValue(undefined);
    headerStore.get.mockImplementation((name: string) =>
      name === 'x-veo-pathname' ? 'https://evil.example/console' : null,
    );

    await expect(requireConsoleSession()).rejects.toThrow('NEXT_REDIRECT:/login');
    expect(redirect).toHaveBeenCalledWith('/login');
  });

  it('returns the resolved session when the token is good', async () => {
    cookieStore.get.mockReturnValue({ value: 'tok' });
    meMock.mockResolvedValue({ ok: true, value: IDENTITY });

    const session = await requireConsoleSession();
    expect(session.email).toBe('analyst@example.com');
    expect(redirect).not.toHaveBeenCalled();
  });
});

describe('toPublicIdentity', () => {
  it('strips the access token before anything can be sent to the browser', async () => {
    cookieStore.get.mockReturnValue({ value: 'secret-token-value' });
    meMock.mockResolvedValue({ ok: true, value: IDENTITY });

    const session = await requireConsoleSession();
    const identity = toPublicIdentity(session);

    expect(Object.keys(identity)).not.toContain('token');
    expect(JSON.stringify(identity)).not.toContain('secret-token-value');
    expect(identity.permissions).toEqual(['project:read', 'issue:write']);
  });
});
