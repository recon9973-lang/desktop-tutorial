import { NextResponse } from 'next/server';

import { submitPublicLead } from '@/lib/public-leads';

/**
 * 무료 진단 상담 요청 — 사람이 버튼을 눌렀을 때만 접수된다.
 *
 * 브라우저가 측정 엔진을 직접 부르지 않는 이유는 공개 진단과 같다: 엔진 주소는 서버
 * 설정이고, 속도 제한은 엔진 쪽에 있다. 이 경로는 얇은 통로일 뿐 아무것도 판단하지
 * 않는다 — **무엇을 저장했는지도 엔진이 말하고 우리는 그대로 나른다.**
 *
 * 여기서 개인정보를 로그에 남기지 않는다. 이름·전화·이메일은 통로를 지나갈 뿐이다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store' } as const;

const MESSAGES: Record<string, string> = {
  INVALID: '이름과 연락처(전화 또는 이메일)를 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNAVAILABLE: '접수 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.',
  NOT_CONFIGURED: '접수 서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '접수 중 문제가 발생했습니다. 다시 시도해 주십시오.',
};

const STATUS: Record<string, number> = {
  INVALID: 422,
  RATE_LIMITED: 429,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
  SERVER_ERROR: 500,
};

function text(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: MESSAGES['INVALID'] }, { status: 422, headers: NO_STORE });
  }

  const source = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const name = text(source, 'name');
  const phone = text(source, 'phone');
  const email = text(source, 'email');

  if (name === null || (phone === null && email === null)) {
    return NextResponse.json({ message: MESSAGES['INVALID'] }, { status: 422, headers: NO_STORE });
  }

  const outcome = await submitPublicLead({
    name,
    phone,
    email,
    siteUrl: text(source, 'siteUrl'),
  });

  if (!outcome.ok) {
    return NextResponse.json(
      {
        // 엔진이 준 한국어 사유가 있으면 그것이 우선이다 — 무엇을 고쳐야 하는지 알려 준다.
        message: outcome.message ?? MESSAGES[outcome.reason] ?? MESSAGES['SERVER_ERROR'],
        retryAfterSeconds: outcome.retryAfterSeconds,
      },
      { status: STATUS[outcome.reason] ?? 500, headers: NO_STORE },
    );
  }

  return NextResponse.json({ receipt: outcome.receipt }, { headers: NO_STORE });
}
