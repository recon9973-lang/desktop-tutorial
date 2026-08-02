import { NextResponse } from 'next/server';

import { lookupPublicKeywords } from '@/lib/public-keywords';

/**
 * 무료 키워드 조회 — 사람이 버튼을 눌렀을 때만 제공자 호출이 나간다.
 *
 * 브라우저가 측정 엔진을 직접 부르지 않는 이유는 공개 진단과 같다: 엔진 주소는
 * 서버 설정이고, 속도 제한은 엔진 쪽에 있다. 이 경로는 얇은 통로일 뿐 아무것도
 * 판단하지 않는다. 조회 기록은 어디에도 저장하지 않는다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store' } as const;

const MESSAGES: Record<string, string> = {
  INVALID: '조회할 키워드를 확인해 주십시오.',
  RATE_LIMITED: '무료 조회 한도에 도달했습니다. 잠시 후 다시 시도해 주십시오.',
  UNAVAILABLE: '측정 엔진에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.',
  NOT_CONFIGURED: '측정 엔진 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '조회 중 문제가 발생했습니다. 다시 시도해 주십시오.',
};

const STATUS: Record<string, number> = {
  INVALID: 422,
  RATE_LIMITED: 429,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
  SERVER_ERROR: 500,
};

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { message: MESSAGES.INVALID },
      { status: 422, headers: NO_STORE },
    );
  }

  const source =
    typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const keywords = Array.isArray(source.keywords)
    ? source.keywords
        .filter((item): item is string => typeof item === 'string')
        .map((item) => item.trim())
        .filter((item) => item !== '')
    : [];
  if (keywords.length === 0) {
    return NextResponse.json(
      { message: '조회할 키워드를 입력해 주십시오.' },
      { status: 422, headers: NO_STORE },
    );
  }

  const outcome = await lookupPublicKeywords(keywords);
  if (!outcome.ok) {
    return NextResponse.json(
      {
        // 엔진이 사유를 말했으면 그 문장을 그대로 — "최대 5개" 같은 규칙은 엔진의 것이다.
        message: outcome.message ?? MESSAGES[outcome.reason] ?? MESSAGES.SERVER_ERROR,
        retryAfterSeconds: outcome.retryAfterSeconds,
      },
      { status: STATUS[outcome.reason] ?? 500, headers: NO_STORE },
    );
  }
  return NextResponse.json({ result: outcome.result }, { headers: NO_STORE });
}
