import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';

/**
 * 브랜드 등록·수정 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '브랜드를 등록할 권한이 없습니다.',
  NOT_FOUND: '프로젝트를 찾을 수 없습니다.',
  CONFLICT: '이미 등록된 브랜드입니다.',
  INVALID: '입력 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '저장 중 문제가 발생했습니다.',
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

/** 줄바꿈이나 쉼표로 나눠 넣은 목록. 빈 줄은 버린다. */
function list(value: unknown): string[] {
  if (typeof value !== 'string') return [];
  return value
    .split(/[\n,]/)
    .map((one) => one.trim())
    .filter((one) => one !== '');
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.');
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const projectId = text(input['projectId']);
  const displayName = text(input['displayName']);
  if (projectId === null) {
    return refuse('INVALID', '프로젝트를 선택해 주십시오.');
  }

  const fields = {
    aliases: list(input['aliases']),
    own_domains: list(input['ownDomains']),
    address_terms: list(input['addressTerms']),
    phone_numbers: list(input['phoneNumbers']),
    distinguishing_terms: list(input['distinguishingTerms']),
  };

  const brandId = text(input['brandId']);
  const outcome =
    brandId === null
      ? await callConsoleApi(`/api/projects/${encodeURIComponent(projectId)}/brands`, {
          method: 'POST',
          body: {
            display_name: displayName ?? '',
            is_own_brand: input['isOwnBrand'] === true,
            homepage_url: text(input['homepageUrl']),
            ...fields,
          },
        })
      : await callConsoleApi(
          `/api/projects/${encodeURIComponent(projectId)}/brands/${encodeURIComponent(brandId)}`,
          {
            method: 'PATCH',
            // 상호도 함께 보낸다. 오타를 못 고치면 수정 화면이 반쪽이다.
            // 식별자(entity_key)는 서버가 바꾸지 않는다 — 지난 관측이 그 값으로 이
            // 브랜드를 가리키고 있어서, 바꾸면 추이가 조용히 끊긴다.
            body: { ...fields, ...(displayName === null ? {} : { display_name: displayName }) },
          },
        );

  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, brand: outcome.data }, { headers: NO_STORE });
}
