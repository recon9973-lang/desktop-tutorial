/** Where a signed-in user lands when no particular destination was requested. */
export const DEFAULT_CONSOLE_PATH = '/console/dashboard';

export const LOGIN_PATH = '/login';

/** Paths that must never be a post-login destination. */
const NEVER_A_DESTINATION = [LOGIN_PATH, '/api/session'];

/**
 * Validates a `?next=` value before it is ever used as a redirect target.
 *
 * Only a same-origin, single-slash absolute path survives. Anything that could
 * carry the browser to another origin — an absolute URL, a protocol-relative
 * `//host`, a backslash, a control character smuggled before the authority — is
 * rejected outright rather than sanitised, because a half-cleaned redirect is
 * still an open redirect.
 */
export function safeNextPath(value: unknown): string | null {
  if (typeof value !== 'string' || value === '') {
    return null;
  }

  // Control characters are stripped by some URL parsers, which would change the
  // meaning of the string after this check. Reject rather than normalise.
  if (/[\u0000-\u001f\u007f]/.test(value)) {
    return null;
  }

  if (!value.startsWith('/')) {
    return null;
  }

  if (value.startsWith('//') || value.startsWith('/\\')) {
    return null;
  }

  let parsed: URL;
  try {
    parsed = new URL(value, 'https://veo.invalid');
  } catch {
    return null;
  }

  if (parsed.origin !== 'https://veo.invalid') {
    return null;
  }

  const pathname = parsed.pathname;
  if (NEVER_A_DESTINATION.some((blocked) => pathname === blocked || pathname.startsWith(`${blocked}/`))) {
    return null;
  }

  return `${pathname}${parsed.search}${parsed.hash}`;
}

/** Builds the login URL, carrying a validated destination when there is one. */
export function loginPathFor(next: unknown): string {
  const destination = safeNextPath(next);
  if (destination === null) {
    return LOGIN_PATH;
  }
  return `${LOGIN_PATH}?next=${encodeURIComponent(destination)}`;
}
