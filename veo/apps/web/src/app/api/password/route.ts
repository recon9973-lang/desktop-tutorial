import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';
import { CONSOLE_SESSION_COOKIE } from '@/lib/session-cookie';

/**
 * Changing your own password.
 *
 * Proxied server-side so the access token stays in the httpOnly cookie and never has to
 * be read by client JavaScript to authorise the call. Neither password is logged, and
 * neither is echoed back.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Reason =
  | 'WRONG_CURRENT_PASSWORD'
  | 'SAME_PASSWORD'
  | 'WEAK_PASSWORD'
  | 'SIGNED_OUT'
  | 'SERVER_ERROR'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED';

const STATUS_BY_REASON: Record<Reason, number> = {
  WRONG_CURRENT_PASSWORD: 401,
  SAME_PASSWORD: 409,
  WEAK_PASSWORD: 422,
  SIGNED_OUT: 401,
  SERVER_ERROR: 500,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
};

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

function rejected(reason: Reason): NextResponse {
  return NextResponse.json({ ok: false, reason }, { status: STATUS_BY_REASON[reason], headers: NO_STORE });
}

export async function POST(request: Request): Promise<NextResponse> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) return rejected('NOT_CONFIGURED');

  const token = (await cookies()).get(CONSOLE_SESSION_COOKIE)?.value ?? '';
  if (token === '') return rejected('SIGNED_OUT');

  let currentPassword = '';
  let newPassword = '';
  try {
    const body: unknown = await request.json();
    if (typeof body === 'object' && body !== null) {
      const parsed = body as { currentPassword?: unknown; newPassword?: unknown };
      currentPassword = typeof parsed.currentPassword === 'string' ? parsed.currentPassword : '';
      newPassword = typeof parsed.newPassword === 'string' ? parsed.newPassword : '';
    }
  } catch {
    return rejected('SERVER_ERROR');
  }
  if (currentPassword === '' || newPassword === '') return rejected('WEAK_PASSWORD');

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/auth/password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      cache: 'no-store',
    });
  } catch {
    return rejected('UNAVAILABLE');
  }

  if (response.ok) return NextResponse.json({ ok: true }, { headers: NO_STORE });
  if (response.status === 401) return rejected('WRONG_CURRENT_PASSWORD');
  if (response.status === 409) return rejected('SAME_PASSWORD');
  if (response.status === 422) return rejected('WEAK_PASSWORD');
  return rejected('SERVER_ERROR');
}
