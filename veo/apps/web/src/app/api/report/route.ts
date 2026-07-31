import { NextResponse } from 'next/server';

import { publishFromScan } from '@/lib/reports';

/**
 * 리포트 발행 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 본문에 **제목과 어느 진단이었는지밖에 없다.** 숫자가 여기를 지나가지 않는 것이
 * 요점이다. 지나갈 수 있으면 언젠가 지나간다.
 *
 * 409 문장은 덮지 않는다. 엔진은 왜 이 실행으로 문서를 만들 수 없는지를 한국어로
 * 알려 준다 — "발행하지 못했습니다" 로 갈아 끼우면 사용자는 다음에 뭘 해야 할지
 * 알 길이 없다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '리포트를 발행할 권한이 없습니다.',
  NOT_FOUND: '그 진단 실행을 찾을 수 없습니다.',
  CONFLICT: '이 진단으로는 리포트를 만들 수 없습니다.',
  INVALID: '요청 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '발행 중 문제가 발생했습니다.',
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

function refuse(reason: string, message?: string | null): NextResponse {
  return NextResponse.json(
    { ok: false, reason, message: message ?? MESSAGES[reason] ?? MESSAGES['SERVER_ERROR'] },
    { status: STATUS[reason] ?? 500, headers: NO_STORE },
  );
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.');
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const scanRunId = text(input['scanRunId']);
  const title = text(input['title']);
  if (scanRunId === null) {
    return refuse('INVALID', '어느 진단으로 만들지 골라 주십시오.');
  }
  if (title === null) {
    return refuse('INVALID', '리포트 제목을 입력해 주십시오.');
  }

  const outcome = await publishFromScan(scanRunId, title);
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, report: outcome.data }, { headers: NO_STORE });
}
