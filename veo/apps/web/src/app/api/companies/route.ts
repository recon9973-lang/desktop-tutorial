import { randomUUID } from 'node:crypto';

import { NextResponse } from 'next/server';

import { addSite, createCompany } from '@/lib/companies';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 업체 등록 — 업체명과 측정 URL 한 벌.
 *
 * 세션 토큰은 httpOnly 쿠키에 있어 브라우저 스크립트가 읽지 못한다. 그래서 등록은
 * 브라우저가 엔진에 직접 말하지 않고 이 핸들러를 거친다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  INVALID_NAME: '업체명을 입력해 주십시오.',
  INVALID_URL: '주소를 확인해 주십시오. 예: ondam.co.kr 또는 https://ondam.co.kr',
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '이 작업을 할 권한이 없습니다.',
  CONFLICT: '이미 등록된 주소입니다.',
  INVALID: '입력값을 확인해 주십시오.',
  UNAVAILABLE: '서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '처리 중 문제가 발생했습니다.',
};

const STATUS: Record<string, number> = {
  INVALID_NAME: 422,
  INVALID_URL: 422,
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


export async function POST(request: Request): Promise<NextResponse> {
  let name = '';
  let url = '';
  let customerId = '';
  let address = '';
  try {
    const body: unknown = await request.json();
    const parsed = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
    name = typeof parsed['name'] === 'string' ? parsed['name'] : '';
    url = typeof parsed['url'] === 'string' ? parsed['url'] : '';
    customerId = typeof parsed['customerId'] === 'string' ? parsed['customerId'] : '';
    address = typeof parsed['address'] === 'string' ? parsed['address'] : '';
  } catch {
    return refuse('INVALID', null, MESSAGES, STATUS);
  }

  // 프로젝트 식별자에 붙일 접미사. 같은 이름의 업체가 둘 있어도 충돌하지 않게 한다.
  const suffix = randomUUID().slice(0, 8);
  const result =
    customerId === ''
      ? await createCompany(name, url, suffix, address)
      : await addSite(customerId, name, url, suffix);

  if (result.ok) {
    return NextResponse.json(
      { ok: true, customerId: result.customerId, siteId: result.siteId },
      { headers: NO_STORE },
    );
  }

  // 어디에 이미 있는지 말한다. "이미 등록된 주소입니다" 만으로는 어느 업체를 열어 봐야
  // 하는지 알 수 없어, 결국 목록을 눈으로 훑게 된다.
  if (result.reason === 'DUPLICATE') {
    return refuse('CONFLICT', `이미 "${result.owner}" 에 등록된 주소입니다.`, MESSAGES, STATUS);
  }

  if (result.reason === 'API') {
    // 엔진이 사람에게 보여도 되는 문장을 줬다면 그것을 쓴다. 우리 쪽 일반 문구로 덮으면
    // "이미 등록된 주소입니다" 같은 구체적인 이유가 사라진다.
    return refuse(result.outcome.ok ? 'SERVER_ERROR' : result.outcome.reason,
      result.outcome.ok ? null : result.outcome.message, MESSAGES, STATUS);
  }
  return refuse(result.reason, null, MESSAGES, STATUS);
}
