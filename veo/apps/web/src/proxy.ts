import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

import {
  CONSOLE_REFRESH_COOKIE,
  CONSOLE_SESSION_COOKIE,
  refreshCookieOptions,
  sessionCookieOptions,
} from '@/lib/session-cookie';

/**
 * 콘솔 요청이 화면에 닿기 전에 두 가지를 한다.
 *
 * **1. 어느 경로를 열려던 것인지 헤더에 남긴다.** 레이아웃은 자기가 어느 URL을 위해
 * 그려지는지 볼 수 없다. 이것이 없으면 인증 가드가 사람을 맨 `/login` 으로만 보내고
 * 가려던 곳을 잃는다. 이 값은 신뢰하지 않는 입력이라 `safeNextPath` 로 검증한 뒤에만
 * 이동 대상으로 쓴다.
 *
 * **2. 만료된 접근 토큰을 조용히 갱신한다.** 접근 토큰은 15분짜리다. 엔진은 로그인
 * 응답에 14일짜리 갱신 토큰을 함께 주는데 콘솔이 그것을 버리고 있어서, 15분만 지나면
 * 로그인 화면으로 튕겼다 — 매번 아이디와 비밀번호를 다시 쳐야 했던 이유다.
 *
 * 여기서 갱신하는 이유: Next.js 는 서버 컴포넌트가 쿠키를 고치는 것을 막는다. 화면을
 * 그리는 중에는 새 토큰을 받아도 저장할 자리가 없다. 응답을 만들기 전에 도는 이 자리가
 * 쿠키를 얹을 수 있는 유일한 곳이다.
 *
 * 인증 판정은 여전히 여기서 하지 않는다. 토큰을 실제로 검증하는 것은 콘솔 레이아웃의
 * `requireConsoleSession()` 이다. 갱신에 실패하면 아무 일도 없었던 것처럼 넘기고,
 * 그다음은 평소대로 로그인 화면이다 — 여기서 실패를 감추면 왜 못 들어가는지 알 수 없다.
 *
 * (Next.js 16 renamed the `middleware` file convention to `proxy`.)
 */

export const PATHNAME_HEADER = 'x-veo-pathname';

export default async function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.set(PATHNAME_HEADER, `${request.nextUrl.pathname}${request.nextUrl.search}`);
  const forward = { request: { headers } };

  if (request.cookies.has(CONSOLE_SESSION_COOKIE)) {
    return NextResponse.next(forward);
  }

  const refresh = request.cookies.get(CONSOLE_REFRESH_COOKIE)?.value ?? '';
  const baseUrl = process.env['VEO_API_BASE_URL'] ?? '';
  if (refresh === '' || baseUrl === '') {
    return NextResponse.next(forward);
  }

  let data: Record<string, unknown> | null = null;
  try {
    const response = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: 'no-store',
    });
    if (!response.ok) {
      // 갱신 토큰이 죽었다. 들고 있어 봐야 매 요청마다 헛되이 부르게 되므로 지운다.
      const spent = NextResponse.next(forward);
      spent.cookies.set({
        name: CONSOLE_REFRESH_COOKIE,
        value: '',
        ...refreshCookieOptions(),
        maxAge: 0,
      });
      return spent;
    }
    const body: unknown = await response.json();
    data =
      typeof body === 'object' && body !== null && 'data' in body
        ? ((body as { data: unknown }).data as Record<string, unknown> | null)
        : null;
  } catch {
    return NextResponse.next(forward);
  }

  if (data === null || typeof data['access_token'] !== 'string') {
    return NextResponse.next(forward);
  }
  const access = data['access_token'];

  const next = NextResponse.next(forward);
  const expires = typeof data['expires_in'] === 'number' ? data['expires_in'] : null;
  next.cookies.set({
    name: CONSOLE_SESSION_COOKIE,
    value: access,
    ...sessionCookieOptions(expires),
  });
  // 엔진이 갱신 토큰을 회전시키면 새것으로 바꾼다. 옛것을 두면 다음 갱신에서 거절당한다.
  const rotated = data['refresh_token'];
  if (typeof rotated === 'string' && rotated !== '') {
    next.cookies.set({
      name: CONSOLE_REFRESH_COOKIE,
      value: rotated,
      ...refreshCookieOptions(),
    });
  }
  return next;
}

export const config = {
  matcher: ['/console/:path*'],
};
