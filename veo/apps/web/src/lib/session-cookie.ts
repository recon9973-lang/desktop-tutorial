import 'server-only';

/**
 * The console session cookie, and the only place its name and flags are written.
 *
 * The access token lives here and nowhere else: not in `localStorage`, not in a
 * client-readable cookie, never serialised into a page. It is set and cleared
 * exclusively by the route handlers under `app/api/session`, which run on the
 * server, so no browser code ever holds the value.
 */
export const CONSOLE_SESSION_COOKIE = 'veo_console_session';

/** Used when the backend states no lifetime for the grant: eight hours. */
export const DEFAULT_SESSION_MAX_AGE_SECONDS = 60 * 60 * 8;

export interface SessionCookieOptions {
  readonly httpOnly: true;
  readonly secure: boolean;
  readonly sameSite: 'lax';
  readonly path: '/';
  readonly maxAge: number;
}

/**
 * `Secure` is dropped only for a local `next dev` run over plain HTTP, where the
 * browser would otherwise refuse the cookie and sign-in could never be tested.
 * Every other environment, tests included, gets it.
 */
function secureFlag(nodeEnv = process.env.NODE_ENV): boolean {
  return nodeEnv !== 'development';
}

export function sessionCookieOptions(
  maxAgeSeconds: number | null,
): SessionCookieOptions {
  return {
    httpOnly: true,
    secure: secureFlag(),
    sameSite: 'lax',
    path: '/',
    maxAge:
      maxAgeSeconds !== null && maxAgeSeconds > 0
        ? maxAgeSeconds
        : DEFAULT_SESSION_MAX_AGE_SECONDS,
  };
}

export function clearedSessionCookieOptions(): SessionCookieOptions {
  return { ...sessionCookieOptions(null), maxAge: 0 };
}
