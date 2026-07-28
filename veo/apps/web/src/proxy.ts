import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Records the requested console path in a request header.
 *
 * A layout cannot see the URL it is rendering for, so without this the auth
 * guard could only ever send people to a bare `/login` and drop where they were
 * going. The value is validated by `safeNextPath` before it is ever used as a
 * redirect target — this header is untrusted input like any other.
 *
 * This proxy makes no authentication or authorization decision. The guard is
 * `requireConsoleSession()` in the console layout, which is where the token is
 * actually verified against the API.
 *
 * (Next.js 16 renamed the `middleware` file convention to `proxy`.)
 */

export const PATHNAME_HEADER = 'x-veo-pathname';

export default function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.set(PATHNAME_HEADER, `${request.nextUrl.pathname}${request.nextUrl.search}`);

  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: ['/console/:path*'],
};
