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

/**
 * 갱신 토큰을 담는 쿠키.
 *
 * 접근 토큰은 15분짜리다. 그것만 두면 15분마다 로그인 화면으로 튕긴다 — 실제로 그랬다.
 * 엔진은 로그인 응답에 14일짜리 갱신 토큰을 함께 주는데 콘솔이 버리고 있었다.
 *
 * 접근 토큰과 **다른 쿠키**에 담는 이유: 접근 토큰은 짧게 살고 갱신 토큰은 길게 산다.
 * 한 쿠키에 담으면 둘 중 하나의 수명을 포기해야 한다.
 */
export const CONSOLE_REFRESH_COOKIE = 'veo_console_refresh';

/** 엔진의 `refresh_token_ttl_seconds` 와 같다. 더 길게 잡으면 이미 죽은 토큰을 들고 있게 된다. */
export const REFRESH_MAX_AGE_SECONDS = 60 * 60 * 24 * 14;

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

export function refreshCookieOptions(): SessionCookieOptions {
  return { ...sessionCookieOptions(null), maxAge: REFRESH_MAX_AGE_SECONDS };
}

export function clearedRefreshCookieOptions(): SessionCookieOptions {
  return { ...sessionCookieOptions(null), maxAge: 0 };
}

export function clearedSessionCookieOptions(): SessionCookieOptions {
  return { ...sessionCookieOptions(null), maxAge: 0 };
}
