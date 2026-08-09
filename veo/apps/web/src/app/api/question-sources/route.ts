import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 질문 수집 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 *
 * **출처를 걸러서 넘기지 않는다.** 엔진은 아는 출처를 전부 돌려주고 각각의 상태를 함께
 * 준다. 여기서 "쓸 수 있는 것만" 추려 넘기면 화면은 열쇠만 넣으면 켜지는 출처가 있다는
 * 사실을 영영 모른다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '질문을 수집할 권한이 없습니다.',
  NOT_FOUND: '요청한 것을 찾을 수 없습니다.',
  INVALID: '찾을 말을 두 글자 이상 넣어 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '질문을 가져오는 중 문제가 발생했습니다.',
};

const STATUS: Record<string, number> = {
  SIGNED_OUT: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INVALID: 422,
  RATE_LIMITED: 429,
  UNREACHABLE: 502,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
  SERVER_ERROR: 500,
};


export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.', MESSAGES, STATUS);
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const query = typeof input['query'] === 'string' ? input['query'].trim() : '';
  if (query.length < 2) {
    return refuse('INVALID', null, MESSAGES, STATUS);
  }

  const outcome = await callConsoleApi('/api/observations/question-sources', {
    method: 'POST',
    body: { query },
  });

  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  }
  return NextResponse.json({ ok: true, harvest: outcome.data }, { headers: NO_STORE });
}
