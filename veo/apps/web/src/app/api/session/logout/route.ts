import { NextResponse } from 'next/server';

import { getAuthApi } from '@/lib/auth-api';
import { LOGIN_PATH } from '@/lib/next-path';
import { CONSOLE_SESSION_COOKIE, clearedSessionCookieOptions } from '@/lib/session-cookie';

/**
 * Sign-out.
 *
 * A plain form POST, so it works with JavaScript disabled and needs no client
 * code. The cookie is cleared on this response whatever the backend says: if
 * revocation cannot be reached, leaving the browser holding a token would be
 * worse than a token that outlives the browser's copy of it.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function readToken(request: Request): string | null {
  const header = request.headers.get('cookie');
  if (header === null) {
    return null;
  }

  for (const part of header.split(';')) {
    const separator = part.indexOf('=');
    if (separator === -1) {
      continue;
    }
    if (part.slice(0, separator).trim() === CONSOLE_SESSION_COOKIE) {
      const value = part.slice(separator + 1).trim();
      return value === '' ? null : decodeURIComponent(value);
    }
  }

  return null;
}

export async function POST(request: Request): Promise<NextResponse> {
  const token = readToken(request);

  if (token !== null) {
    await getAuthApi().logout(token);
  }

  const response = NextResponse.redirect(new URL(LOGIN_PATH, request.url), {
    // 303 so the browser follows with GET rather than repeating the POST.
    status: 303,
    headers: { 'Cache-Control': 'no-store, private' },
  });

  response.cookies.set({
    name: CONSOLE_SESSION_COOKIE,
    value: '',
    ...clearedSessionCookieOptions(),
  });

  return response;
}
