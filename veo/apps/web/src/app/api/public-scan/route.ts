import { NextResponse } from 'next/server';

import { runScan, type ScanKind } from '@/lib/scan-api';

/**
 * 공개 진단 — 사람이 버튼을 눌렀을 때만 대상 사이트에 요청이 나간다.
 *
 * 브라우저가 측정 엔진을 직접 부르지 않는 이유: 엔진 주소는 서버 설정이고, 속도
 * 제한·SSRF 차단은 엔진 쪽에 있다. 이 경로는 얇은 통로일 뿐 아무것도 판단하지 않는다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store' } as const;

const MESSAGES: Record<string, string> = {
  INVALID_URL: '주소를 확인해 주십시오. 예: https://example.co.kr',
  RATE_LIMITED: '무료 진단 한도에 도달했습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '대상 사이트에서 응답을 받지 못했습니다. 주소와 사이트 상태를 확인해 주십시오.',
  UNAVAILABLE: '측정 엔진에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.',
  NOT_CONFIGURED: '측정 엔진 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '진단 중 문제가 발생했습니다. 다시 시도해 주십시오.',
};

const STATUS: Record<string, number> = {
  INVALID_URL: 422,
  RATE_LIMITED: 429,
  UNREACHABLE: 502,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
  SERVER_ERROR: 500,
};

function scanKind(value: unknown): ScanKind | null {
  return value === 'SEO' || value === 'GEO' ? value : null;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { message: MESSAGES.INVALID_URL },
      { status: 422, headers: NO_STORE },
    );
  }

  const source = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const url = typeof source.url === 'string' ? source.url.trim() : '';
  const kind = scanKind(source.kind) ?? 'SEO';
  if (url === '') {
    return NextResponse.json(
      { message: MESSAGES.INVALID_URL },
      { status: 422, headers: NO_STORE },
    );
  }

  const outcome = await runScan(kind, url);
  if (!outcome.ok) {
    return NextResponse.json(
      {
        message: MESSAGES[outcome.reason] ?? MESSAGES.SERVER_ERROR,
        retryAfterSeconds: outcome.retryAfterSeconds,
      },
      { status: STATUS[outcome.reason] ?? 500, headers: NO_STORE },
    );
  }
  return NextResponse.json({ result: outcome.result }, { headers: NO_STORE });
}
