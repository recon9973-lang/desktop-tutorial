import { NextResponse } from 'next/server';

import { text } from '@/lib/json';
import { NO_STORE, refuse } from '@/lib/route-reply';
import { updateProject } from '@/lib/projects';

/**
 * 프로젝트 수정 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 서버에는 `PATCH /api/projects/{id}` 가 처음부터 있었다. 화면이 없어서 **만들면 이름
 * 오타 하나도 못 고치는** 상태였다(`audit/2026-08-08-server-ui-gap.md` §B). 브랜드에서
 * 같은 모양의 구멍이 이미 두 번 나왔다(v0.3.69).
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '프로젝트를 수정할 권한이 없습니다.',
  NOT_FOUND: '그 프로젝트를 찾을 수 없습니다.',
  CONFLICT: '같은 주소이름(slug)을 쓰는 프로젝트가 이미 있습니다.',
  INVALID: '입력 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '수정 중 문제가 발생했습니다.',
};

export async function PATCH(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.', MESSAGES);
  }

  const source = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const projectId = text(source, 'projectId');
  const name = text(source, 'name').trim();

  if (projectId === '' || name === '') {
    // **빈 이름을 보내지 않는다.** 서버는 빈 본문을 422 로 거절하지만, 그 전에 여기서
    // 막아야 사람에게 "무엇이 잘못됐는지" 를 우리 말로 말할 수 있다.
    return refuse('INVALID', '프로젝트 이름을 적어 주십시오.', MESSAGES);
  }

  const outcome = await updateProject(projectId, { name });
  if (!outcome.ok) {
    return refuse(outcome.reason ?? 'SERVER_ERROR', outcome.message, MESSAGES);
  }

  return NextResponse.json(
    { ok: true, name: outcome.data.name },
    { status: 200, headers: NO_STORE },
  );
}
