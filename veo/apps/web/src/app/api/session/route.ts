import { NextResponse } from 'next/server';

import { getAuthApi } from '@/lib/auth-api';
import { DEFAULT_CONSOLE_PATH, safeNextPath } from '@/lib/next-path';
import { CONSOLE_SESSION_COOKIE, sessionCookieOptions } from '@/lib/session-cookie';

/**
 * Sign-in.
 *
 * This handler exists so the access token never touches the browser. The token
 * goes straight from the auth API into an httpOnly, Secure, SameSite=Lax cookie
 * set on this response; the JSON that reaches the client carries only where to
 * navigate next. There is no code path here that sets a cookie without a token
 * the API actually issued.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Reason =
  | 'INVALID_CREDENTIALS'
  | 'LOCKED_OUT'
  | 'SERVER_ERROR'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED';

const STATUS_BY_REASON: Record<Reason, number> = {
  INVALID_CREDENTIALS: 401,
  LOCKED_OUT: 429,
  SERVER_ERROR: 500,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
};

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

function rejected(reason: Reason, retryAfterSeconds: number | null): NextResponse {
  const body =
    retryAfterSeconds === null
      ? { ok: false, reason }
      : { ok: false, reason, retryAfterSeconds };

  const headers: Record<string, string> = { ...NO_STORE };
  if (retryAfterSeconds !== null) {
    headers['Retry-After'] = String(retryAfterSeconds);
  }

  return NextResponse.json(body, { status: STATUS_BY_REASON[reason], headers });
}

interface LoginBody {
  readonly email: string;
  readonly password: string;
  readonly next: unknown;
}

async function readBody(request: Request): Promise<LoginBody | null> {
  let parsed: unknown;
  try {
    parsed = await request.json();
  } catch {
    return null;
  }

  if (typeof parsed !== 'object' || parsed === null) {
    return null;
  }

  const body = parsed as Record<string, unknown>;
  const email = typeof body['email'] === 'string' ? body['email'].trim().toLowerCase() : '';
  // The password is passed through untouched: trimming it would silently reject
  // a legitimate passphrase that begins or ends with a space.
  const password = typeof body['password'] === 'string' ? body['password'] : '';

  if (email === '' || password === '') {
    return null;
  }

  return { email, password, next: body['next'] };
}

export async function POST(request: Request): Promise<NextResponse> {
  const body = await readBody(request);

  if (body === null) {
    // A malformed or incomplete submission is answered exactly like a wrong
    // password, so probing the endpoint reveals nothing about any account.
    return rejected('INVALID_CREDENTIALS', null);
  }

  const result = await getAuthApi().login({
    email: body.email,
    password: body.password,
  });

  if (!result.ok) {
    return rejected(result.reason === 'SESSION_EXPIRED' ? 'INVALID_CREDENTIALS' : result.reason, result.retryAfterSeconds);
  }

  const redirectTo = safeNextPath(body.next) ?? DEFAULT_CONSOLE_PATH;

  const response = NextResponse.json(
    { ok: true, redirectTo },
    { status: 200, headers: NO_STORE },
  );

  response.cookies.set({
    name: CONSOLE_SESSION_COOKIE,
    value: result.value.accessToken,
    ...sessionCookieOptions(result.value.expiresInSeconds),
  });

  return response;
}
