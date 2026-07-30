import { NextResponse, type NextRequest } from 'next/server';

import {
  CONSOLE_REFRESH_COOKIE,
  CONSOLE_SESSION_COOKIE,
  refreshCookieOptions,
  sessionCookieOptions,
} from '@/lib/session-cookie';

/**
 * 15분마다 로그인 화면으로 튕기지 않게 한다.
 *
 * 접근 토큰은 15분짜리다. 엔진은 로그인 응답에 **14일짜리 갱신 토큰**을 함께 주는데,
 * 콘솔이 그것을 버리고 있었다. 그래서 15분만 지나면 세션이 사라졌고, 매번 아이디와
 * 비밀번호를 다시 쳐야 했다.
 *
 * 여기서 하는 일은 하나다 — 콘솔 화면을 열 때 접근 토큰이 없고 갱신 토큰이 있으면,
 * 조용히 새 접근 토큰을 받아 쿠키에 얹고 그대로 진행한다.
 *
 * **미들웨어에서 하는 이유.** Next.js 는 서버 컴포넌트가 쿠키를 고치는 것을 막는다.
 * 화면을 그리는 중에는 새 토큰을 받아도 저장할 자리가 없다. 미들웨어는 응답을 만들기
 * 전에 돌고 쿠키를 얹을 수 있는 유일한 자리다.
 *
 * 갱신에 실패하면 아무것도 하지 않고 넘긴다. 그다음은 평소대로 로그인 화면이다 —
 * 여기서 실패를 감추면 "왜 안 들어가지는지" 를 알 수 없게 된다.
 */
export async function middleware(request: NextRequest) {
  if (request.cookies.has(CONSOLE_SESSION_COOKIE)) {
    return NextResponse.next();
  }

  const refresh = request.cookies.get(CONSOLE_REFRESH_COOKIE)?.value ?? '';
  if (refresh === '') {
    return NextResponse.next();
  }

  const baseUrl = process.env['VEO_API_BASE_URL'] ?? '';
  if (baseUrl === '') {
    return NextResponse.next();
  }

  let grant: { access?: string; expires?: number | null; refresh?: string } | null = null;
  try {
    const response = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: 'no-store',
    });
    if (!response.ok) {
      // 갱신 토큰이 죽었다. 들고 있어 봐야 매 요청마다 헛되이 부르게 되므로 지운다.
      const passthrough = NextResponse.next();
      passthrough.cookies.set({
        name: CONSOLE_REFRESH_COOKIE,
        value: '',
        ...refreshCookieOptions(),
        maxAge: 0,
      });
      return passthrough;
    }
    const body: unknown = await response.json();
    const data =
      typeof body === 'object' && body !== null && 'data' in body
        ? ((body as { data: unknown }).data as Record<string, unknown> | null)
        : null;
    grant = {
      access: typeof data?.['access_token'] === 'string' ? data['access_token'] : undefined,
      expires: typeof data?.['expires_in'] === 'number' ? data['expires_in'] : null,
      refresh: typeof data?.['refresh_token'] === 'string' ? data['refresh_token'] : undefined,
    };
  } catch {
    return NextResponse.next();
  }

  if (grant.access === undefined) {
    return NextResponse.next();
  }

  const next = NextResponse.next();
  next.cookies.set({
    name: CONSOLE_SESSION_COOKIE,
    value: grant.access,
    ...sessionCookieOptions(grant.expires ?? null),
  });
  // 엔진이 갱신 토큰을 새로 주면(회전) 그것으로 바꾼다. 옛것을 그대로 두면 다음
  // 갱신에서 거절당한다.
  if (grant.refresh !== undefined) {
    next.cookies.set({
      name: CONSOLE_REFRESH_COOKIE,
      value: grant.refresh,
      ...refreshCookieOptions(),
    });
  }
  return next;
}

export const config = {
  // 콘솔 화면에서만 돈다. 공개 화면과 정적 자원에서까지 갱신을 시도할 이유가 없다.
  matcher: ['/console/:path*'],
};
