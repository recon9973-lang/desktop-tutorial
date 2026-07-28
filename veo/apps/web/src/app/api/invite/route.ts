import { NextResponse } from 'next/server';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';

/**
 * Accepting an invitation — setting a password for the first time.
 *
 * Proxied through the server for the same reason sign-in is: the API origin stays
 * server-side, so the browser never needs a cross-origin request carrying an
 * invitation token and a password, and no CORS allowance has to exist for the
 * one unauthenticated write in the product.
 *
 * Nothing here is logged. The token is a credential until it is spent, and the
 * password is one afterwards.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Reason = 'INVALID_TOKEN' | 'WEAK_PASSWORD' | 'SERVER_ERROR' | 'UNAVAILABLE' | 'NOT_CONFIGURED';

const STATUS_BY_REASON: Record<Reason, number> = {
  INVALID_TOKEN: 404,
  WEAK_PASSWORD: 422,
  SERVER_ERROR: 500,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
};

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

function rejected(reason: Reason): NextResponse {
  return NextResponse.json(
    { ok: false, reason },
    { status: STATUS_BY_REASON[reason], headers: NO_STORE },
  );
}

export async function POST(request: Request): Promise<NextResponse> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return rejected('NOT_CONFIGURED');
  }

  let token = '';
  let password = '';
  try {
    const body: unknown = await request.json();
    if (typeof body === 'object' && body !== null) {
      const parsed = body as { token?: unknown; password?: unknown };
      token = typeof parsed.token === 'string' ? parsed.token : '';
      password = typeof parsed.password === 'string' ? parsed.password : '';
    }
  } catch {
    return rejected('INVALID_TOKEN');
  }

  if (token === '' || password === '') {
    return rejected('INVALID_TOKEN');
  }

  let response: Response;
  try {
    response = await fetch(
      `${baseUrl}/api/invitations/${encodeURIComponent(token)}/accept`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ password }),
        cache: 'no-store',
      },
    );
  } catch {
    return rejected('UNAVAILABLE');
  }

  if (response.ok) {
    // Deliberately no identity in the reply. The account now exists and the person
    // signs in with it like anyone else; handing back a session here would make this
    // route a second way to become authenticated.
    return NextResponse.json({ ok: true }, { headers: NO_STORE });
  }
  if (response.status === 404) {
    return rejected('INVALID_TOKEN');
  }
  if (response.status === 422) {
    return rejected('WEAK_PASSWORD');
  }
  return rejected('SERVER_ERROR');
}
