import { NextResponse } from 'next/server';

import { assignIssue } from '@/lib/issues-api';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 담당자 지정 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * `userId` 가 없으면 **지정 해제**다. 빈 문자열과 `null` 을 가르지 않으면 "해제" 가
 * "잘못된 요청" 으로 떨어져, 맡은 사람을 뗄 방법이 사라진다.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '담당자를 지정할 권한이 없습니다.',
  NOT_FOUND: '그 이슈 또는 사용자를 찾을 수 없습니다.',
  CONFLICT: '지금 상태에서는 할 수 없습니다.',
  INVALID: '요청 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '담당자를 지정하는 중 문제가 발생했습니다.',
};

const STATUS: Record<string, number> = {
  SIGNED_OUT: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  INVALID: 422,
  RATE_LIMITED: 429,
  UNREACHABLE: 502,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
  SERVER_ERROR: 500,
};


function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.', MESSAGES, STATUS);
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const issueId = text(input['issueId']);
  if (issueId === null) {
    return refuse('INVALID', null, MESSAGES, STATUS);
  }

  // 빈 값은 잘못된 요청이 아니라 **해제**다.
  const userId = text(input['userId']);

  const outcome = await assignIssue(issueId, userId);
  if (!outcome.ok) return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  return NextResponse.json({ ok: true }, { headers: NO_STORE });
}
