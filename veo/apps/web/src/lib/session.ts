import 'server-only';

import { cache } from 'react';
import { cookies, headers } from 'next/headers';
import { redirect } from 'next/navigation';
import type { Role } from '@veo/shared-types';

import { getAuthApi } from './auth-api';
import { loginPathFor } from './next-path';
import type { Permission } from './permissions';
import { CONSOLE_SESSION_COOKIE } from './session-cookie';

export { CONSOLE_SESSION_COOKIE };
export { LOGIN_PATH } from './next-path';

/** Header the middleware writes so a layout can learn the requested path. */
export const PATHNAME_HEADER = 'x-veo-pathname';

/**
 * Everything about the signed-in user that is safe to hand to a client component.
 *
 * Note what is missing: the access token. `toPublicIdentity` is the only way a
 * session crosses into the browser, and it cannot carry the token because the
 * token is not part of this type.
 */
export interface PublicConsoleIdentity {
  readonly userId: string;
  readonly organizationId: string;
  readonly displayName: string;
  readonly email: string;
  readonly roles: readonly Role[];
  /** Resolved by the API's `/auth/me`, never derived from the roles here. */
  readonly permissions: readonly Permission[];
}

/** Server-side view. Adds the bearer token used to call the API. */
export interface ConsoleSession extends PublicConsoleIdentity {
  readonly token: string;
}

/**
 * Raised when authentication cannot be decided at all — the API is unreachable
 * or this deployment has no API configured.
 *
 * This is deliberately not a redirect to `/login`: sending someone to a sign-in
 * form that also cannot work would present an outage as a credentials problem.
 * The console error boundary renders it as the outage it is.
 */
export class AuthUnavailableError extends Error {
  readonly reason: 'UNAVAILABLE' | 'NOT_CONFIGURED';

  constructor(reason: 'UNAVAILABLE' | 'NOT_CONFIGURED') {
    super(
      reason === 'NOT_CONFIGURED'
        ? '인증 서버가 설정되지 않았습니다.'
        : '인증 서버에 연결할 수 없습니다.',
    );
    this.name = 'AuthUnavailableError';
    this.reason = reason;
  }
}

async function readSessionToken(): Promise<string | null> {
  const cookieStore = await cookies();
  const value = cookieStore.get(CONSOLE_SESSION_COOKIE)?.value;
  if (typeof value !== 'string' || value.trim() === '') {
    return null;
  }
  return value;
}

/**
 * Resolves the caller from the session cookie.
 *
 * Holding the cookie proves nothing on its own: the identity, the roles and the
 * permission list all come from the API's `/auth/me`. A cookie the API rejects is
 * simply no session.
 *
 * Wrapped in React's `cache` so a layout and the page beneath it resolve the
 * session once per request rather than twice.
 */
export const readConsoleSession = cache(async function readConsoleSession(): Promise<ConsoleSession | null> {
  const token = await readSessionToken();
  if (token === null) {
    return null;
  }

  const result = await getAuthApi().me(token);

  if (result.ok) {
    return { ...result.value, token };
  }

  if (result.reason === 'UNAVAILABLE' || result.reason === 'NOT_CONFIGURED') {
    throw new AuthUnavailableError(result.reason);
  }

  // SESSION_EXPIRED, SERVER_ERROR: nothing here can be trusted as a session.
  return null;
});

/** The path the visitor asked for, as recorded by the middleware. */
async function requestedPath(): Promise<string | null> {
  const headerStore = await headers();
  return headerStore.get(PATHNAME_HEADER);
}

/**
 * Auth guard for the `(console)` route group.
 *
 * Called from the console layout, so no console page below it can render for a
 * visitor without a valid session.
 */
export async function requireConsoleSession(): Promise<ConsoleSession> {
  const session = await readConsoleSession();

  if (session === null) {
    redirect(loginPathFor(await requestedPath()));
  }

  return session;
}

/**
 * The guard plus the token-free view, for pages that only need to know who is
 * asking and what they may see.
 */
export async function requireConsoleIdentity(): Promise<PublicConsoleIdentity> {
  return toPublicIdentity(await requireConsoleSession());
}

/** Strips the access token. The only way a session may reach a client component. */
export function toPublicIdentity(session: ConsoleSession): PublicConsoleIdentity {
  return {
    userId: session.userId,
    organizationId: session.organizationId,
    displayName: session.displayName,
    email: session.email,
    roles: session.roles,
    permissions: session.permissions,
  };
}
