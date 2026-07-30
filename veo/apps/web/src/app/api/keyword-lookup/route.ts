import { NextResponse } from 'next/server';

import { lookUpKeywords } from '@/lib/keywords';

/**
 * 키워드 조회 — 사람이 버튼을 눌렀을 때만.
 *
 * 네이버 공식 API 를 실제로 부르는 경로다. 화면을 여는 것만으로는 여기까지 오지 않는다.
 * 서버에서 대신 부른다 — 접근 토큰은 httpOnly 쿠키에 있어 브라우저가 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '키워드를 조회할 권한이 없습니다.',
  NOT_FOUND: '요청을 처리할 수 없습니다.',
  CONFLICT: '이미 처리 중입니다.',
  INVALID: '키워드를 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '네이버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '조회 중 문제가 발생했습니다.',
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

/** 한 번에 부를 수 있는 키워드 수. 네이버에 보내는 요청 수를 그대로 정하는 값이다. */
const MAX_KEYWORDS = 20;

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.');
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const raw = typeof input['keywords'] === 'string' ? input['keywords'] : '';
  const keywords = raw
    .split(/[\n,]/)
    .map((one) => one.trim())
    .filter((one) => one !== '');

  if (keywords.length === 0) {
    return refuse('INVALID', '키워드를 하나 이상 입력해 주십시오.');
  }
  if (keywords.length > MAX_KEYWORDS) {
    return refuse('INVALID', `한 번에 최대 ${MAX_KEYWORDS}개까지 조회합니다.`);
  }

  const outcome = await lookUpKeywords(keywords);
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, lookup: outcome.data }, { headers: NO_STORE });
}
