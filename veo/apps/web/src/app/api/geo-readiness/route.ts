import { NextResponse } from 'next/server';

import { scanGeoReadiness } from '@/lib/observations';

/**
 * GEO 준비도 진단 — 사람이 버튼을 눌렀을 때만.
 *
 * 대상 사이트를 실제로 가져오는 경로다. 화면을 여는 것만으로는 여기까지 오지 않는다.
 * 서버에서 대신 부른다 — 접근 토큰은 httpOnly 쿠키에 있어 브라우저가 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '진단을 실행할 권한이 없습니다.',
  NOT_FOUND: '주소를 찾을 수 없습니다.',
  CONFLICT: '이미 처리 중입니다.',
  INVALID: '주소를 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '대상 사이트에서 응답을 받지 못했습니다. 사이트 상태를 확인해 주십시오.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '진단 중 문제가 발생했습니다.',
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

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.');
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const url = typeof input['url'] === 'string' ? input['url'].trim() : '';
  if (url === '') {
    return refuse('INVALID', '주소를 입력해 주십시오.');
  }

  const outcome = await scanGeoReadiness(url);
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  // 보고서를 그대로 돌려준다. GEO 준비도는 아직 저장되지 않으므로, 결과를 주소창
  // 파라미터로 넘기면 화면을 열 때마다 대상 사이트를 다시 가져오게 된다. 화면을 여는
  // 것과 새로 재는 것은 갈라 두어야 한다.
  return NextResponse.json({ ok: true, report: outcome.data }, { headers: NO_STORE });
}
