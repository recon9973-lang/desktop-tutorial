import { NextResponse } from 'next/server';

import { transitionIssue } from '@/lib/issues-api';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 이슈 상태 변경 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 *
 * **409 는 덮지 않는다.** 엔진이 거부할 때 돌려주는 문장은 "안 됩니다" 가 아니라 *지금
 * 갈 수 있는 상태가 무엇인지* 를 이름으로 알려 준다. 그 문장을 우리 문장으로 갈아
 * 끼우면 담당자는 다음에 무엇을 눌러야 하는지 알 길이 없어진다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '이슈 상태를 바꿀 권한이 없습니다.',
  NOT_FOUND: '그 이슈를 찾을 수 없습니다.',
  CONFLICT: '지금 상태에서는 할 수 없는 변경입니다.',
  INVALID: '요청 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '상태를 바꾸는 중 문제가 발생했습니다.',
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
  const toState = text(input['toState']);
  if (issueId === null || toState === null) {
    return refuse('INVALID', null, MESSAGES, STATUS);
  }

  const outcome = await transitionIssue(issueId, toState);
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  }
  return NextResponse.json({ ok: true, issue: outcome.data }, { headers: NO_STORE });
}
