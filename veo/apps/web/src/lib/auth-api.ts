import 'server-only';

import type { Role } from '@veo/shared-types';

import { parsePermissions, parseRoles } from './permissions';
import type { Permission } from './permissions';

/**
 * ────────────────────────────────────────────────────────────────────────────
 *  THE ONE PLACE THAT ASSUMES ANYTHING ABOUT THE AUTH API
 * ────────────────────────────────────────────────────────────────────────────
 *
 * The auth endpoints are being written elsewhere and are not in the generated
 * `@veo/api-client` yet, so this module talks to them over `fetch` directly.
 * Every assumption the front end makes is in this file and nowhere else; when
 * the real contract lands, correcting it here is the whole integration.
 *
 * Assumed contract (see `apps/web/INTEGRATION_REQUEST.md` §7):
 *
 *   POST {base}/api/auth/login   {"email","password"}
 *        200 → {"data":{"access_token": str, "expires_in": int|null}, ...}
 *        400/401/403/404 → rejected credentials, indistinguishable by design
 *        429 → locked out, `Retry-After` in seconds
 *
 *   GET  {base}/api/auth/me      Authorization: Bearer <token>
 *        200 → {"data":{"user_id","organization_id","display_name","email",
 *                       "roles":[Role], "permissions":[Permission]}, ...}
 *        401 → the token is no longer good
 *
 *   POST {base}/api/auth/logout  Authorization: Bearer <token>
 *        2xx → revoked
 *
 * The response envelope follows the shape the rest of the API already uses
 * (`{data, error, meta}`), matching `@veo/api-client`. It is re-implemented here
 * rather than imported so that regenerating that client cannot silently change
 * how a login failure is classified.
 *
 * Nothing in this module ever reports success it did not receive. An unreachable
 * or misconfigured backend produces `UNAVAILABLE` / `NOT_CONFIGURED`, never a
 * session.
 */

export const AUTH_LOGIN_PATH = '/api/auth/login';
export const AUTH_ME_PATH = '/api/auth/me';
export const AUTH_LOGOUT_PATH = '/api/auth/logout';

export interface AuthCredentials {
  readonly email: string;
  readonly password: string;
}

export interface AuthTokenGrant {
  readonly accessToken: string;
  /** `null` when the backend did not state a lifetime. */
  readonly expiresInSeconds: number | null;
  /**
   * 접근 토큰이 만료된 뒤 새 것을 받아 오는 열쇠. 엔진이 주지 않으면 `null`.
   *
   * 접근 토큰은 15분짜리다. 이것을 버리면 15분마다 로그인 화면으로 튕긴다 —
   * 실제로 그랬고, 그래서 매번 아이디와 비밀번호를 다시 쳐야 했다.
   */
  readonly refreshToken: string | null;
}

export interface AuthIdentity {
  readonly userId: string;
  readonly organizationId: string;
  readonly displayName: string;
  readonly email: string;
  readonly roles: readonly Role[];
  /** Resolved by the API. The front end never derives this from the roles. */
  readonly permissions: readonly Permission[];
}

export type AuthFailureReason =
  /** Wrong email, wrong password, unknown account, disabled account — one bucket. */
  | 'INVALID_CREDENTIALS'
  /** Too many attempts. */
  | 'LOCKED_OUT'
  /** A token that was once valid no longer is. */
  | 'SESSION_EXPIRED'
  /** The backend answered, but with a fault. */
  | 'SERVER_ERROR'
  /** The backend could not be reached at all. */
  | 'UNAVAILABLE'
  /** This deployment has no API base URL, so authentication cannot happen. */
  | 'NOT_CONFIGURED';

export interface AuthFailure {
  readonly ok: false;
  readonly reason: AuthFailureReason;
  readonly retryAfterSeconds: number | null;
}

export type AuthResult<T> = { readonly ok: true; readonly value: T } | AuthFailure;

export interface AuthApi {
  login(credentials: AuthCredentials): Promise<AuthResult<AuthTokenGrant>>;
  me(token: string): Promise<AuthResult<AuthIdentity>>;
  logout(token: string): Promise<AuthResult<null>>;
}

export interface AuthApiOptions {
  /** `null` means "not configured"; every call then fails closed. */
  readonly baseUrl: string | null;
  readonly fetch?: typeof globalThis.fetch;
}

function failure(
  reason: AuthFailureReason,
  retryAfterSeconds: number | null = null,
): AuthFailure {
  return { ok: false, reason, retryAfterSeconds };
}

/**
 * Resolves the API origin.
 *
 * The server-only variable wins. `NEXT_PUBLIC_VEO_API_BASE_URL` is accepted as a
 * fallback because a single-origin deployment configures only that one — it is a
 * host name, never a credential. When neither is set this returns `null` rather
 * than guessing `localhost`, so a misconfigured deployment fails loudly.
 */
export function resolveAuthApiBaseUrl(
  env: Record<string, string | undefined> = process.env,
): string | null {
  const candidate = env['VEO_API_BASE_URL'] ?? env['NEXT_PUBLIC_VEO_API_BASE_URL'] ?? '';
  const trimmed = candidate.trim().replace(/\/+$/, '');
  return trimmed === '' ? null : trimmed;
}

interface Envelope {
  readonly data?: unknown;
  readonly error?: { readonly code?: unknown; readonly message?: unknown } | null;
}

async function readEnvelope(response: Response): Promise<Envelope | null> {
  try {
    const parsed: unknown = await response.json();
    if (typeof parsed !== 'object' || parsed === null) {
      return null;
    }
    return parsed as Envelope;
  } catch {
    return null;
  }
}

function retryAfterFrom(response: Response): number | null {
  const header = response.headers.get('Retry-After');
  if (header === null) {
    return null;
  }
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

/**
 * Maps an HTTP status onto a reason.
 *
 * 400/401/403/404 all collapse to `INVALID_CREDENTIALS`: the API deliberately
 * refuses to say whether an account exists, and this front end must not become
 * the oracle it avoided being. The upstream message is discarded for the same
 * reason — it is written for operators, not for an unauthenticated visitor.
 */
function classifyLoginStatus(response: Response): AuthFailure {
  if (response.status === 429) {
    return failure('LOCKED_OUT', retryAfterFrom(response));
  }
  if (response.status >= 400 && response.status < 500) {
    return failure('INVALID_CREDENTIALS');
  }
  return failure('SERVER_ERROR');
}

function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function createAuthApi(options: AuthApiOptions): AuthApi {
  const { baseUrl } = options;
  const doFetch = options.fetch ?? globalThis.fetch;

  async function call(
    path: string,
    init: RequestInit,
  ): Promise<{ readonly response: Response } | AuthFailure> {
    if (baseUrl === null) {
      return failure('NOT_CONFIGURED');
    }
    try {
      const response = await doFetch(`${baseUrl}${path}`, {
        ...init,
        // Authentication answers are per-user and must never be reused.
        cache: 'no-store',
      });
      return { response };
    } catch {
      return failure('UNAVAILABLE');
    }
  }

  return {
    async login(credentials): Promise<AuthResult<AuthTokenGrant>> {
      const outcome = await call(AUTH_LOGIN_PATH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
        }),
      });
      if ('ok' in outcome) {
        return outcome;
      }

      const { response } = outcome;
      if (!response.ok) {
        return classifyLoginStatus(response);
      }

      const envelope = await readEnvelope(response);
      const data = asRecord(envelope?.data);
      if (data === null) {
        // A 200 we cannot read is a server fault, never a sign-in.
        return failure('SERVER_ERROR');
      }

      const accessToken = readString(data, 'access_token');
      if (accessToken === null) {
        return failure('SERVER_ERROR');
      }

      const expires = data['expires_in'];
      const refresh = data['refresh_token'];
      return {
        ok: true,
        value: {
          accessToken,
          expiresInSeconds:
            typeof expires === 'number' && Number.isFinite(expires) && expires > 0
              ? Math.floor(expires)
              : null,
          refreshToken: typeof refresh === 'string' && refresh !== '' ? refresh : null,
        },
      };
    },

    async me(token): Promise<AuthResult<AuthIdentity>> {
      const outcome = await call(AUTH_ME_PATH, {
        method: 'GET',
        headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      });
      if ('ok' in outcome) {
        return outcome;
      }

      const { response } = outcome;
      if (response.status === 401 || response.status === 403) {
        return failure('SESSION_EXPIRED');
      }
      if (!response.ok) {
        return failure(response.status === 429 ? 'LOCKED_OUT' : 'SERVER_ERROR', retryAfterFrom(response));
      }

      const envelope = await readEnvelope(response);
      const data = asRecord(envelope?.data);
      if (data === null) {
        return failure('SERVER_ERROR');
      }

      // `MePayload` nests the person and the organization rather than flattening
      // them. This used to read `user_id` / `organization_id` from the top level,
      // found nothing, and returned SERVER_ERROR — which the console reads as "no
      // session" and answers by redirecting to sign-in. The visible symptom was
      // that signing in appeared to do nothing, while the API had in fact issued a
      // session and recorded a successful login.
      const user = asRecord(data['user']);
      const organization = asRecord(data['organization']);
      if (user === null || organization === null) {
        return failure('SERVER_ERROR');
      }

      const userId = readString(user, 'id');
      const organizationId = readString(organization, 'id');
      const email = readString(user, 'email');
      if (userId === null || organizationId === null || email === null) {
        return failure('SERVER_ERROR');
      }

      return {
        ok: true,
        value: {
          userId,
          organizationId,
          // An account with no display name shows its email, never a stand-in name.
          displayName: readString(user, 'display_name') ?? email,
          email,
          roles: parseRoles(data['roles']),
          permissions: parsePermissions(data['permissions']),
        },
      };
    },

    async logout(token): Promise<AuthResult<null>> {
      const outcome = await call(AUTH_LOGOUT_PATH, {
        method: 'POST',
        headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      });
      if ('ok' in outcome) {
        return outcome;
      }
      if (!outcome.response.ok) {
        return failure('SERVER_ERROR');
      }
      return { ok: true, value: null };
    },
  };
}

/** The app-wide instance. Reads configuration at call time, not at import time. */
export function getAuthApi(): AuthApi {
  return createAuthApi({ baseUrl: resolveAuthApiBaseUrl() });
}
