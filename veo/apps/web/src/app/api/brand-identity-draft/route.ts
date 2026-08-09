import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 홈페이지에서 식별 정보를 읽어 **후보로** 돌려주는 통로.
 *
 * 저장하지 않는다. 사람이 고른 값을 `/api/brand` 로 다시 보내야 저장된다.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다. 그래서
 * 브라우저가 엔진에 직접 말을 걸지 않고 여기를 거친다 — 다른 콘솔 통로와 같은 모양.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '이 프로젝트를 볼 권한이 없습니다.',
  NOT_FOUND: '프로젝트를 찾을 수 없습니다.',
  INVALID: '홈페이지 주소를 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '홈페이지를 읽는 중 문제가 발생했습니다.',
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
  const projectId = text(input['projectId']);
  const url = text(input['url']);
  if (projectId === null) return refuse('INVALID', '프로젝트를 선택해 주십시오.', MESSAGES, STATUS);
  if (url === null) return refuse('INVALID', '홈페이지 주소를 입력해 주십시오.', MESSAGES, STATUS);

  const outcome = await callConsoleApi(
    `/api/projects/${encodeURIComponent(projectId)}/brands/identity-draft`,
    { method: 'POST', body: { url } },
  );

  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  }
  return NextResponse.json({ ok: true, draft: outcome.data }, { headers: NO_STORE });
}
