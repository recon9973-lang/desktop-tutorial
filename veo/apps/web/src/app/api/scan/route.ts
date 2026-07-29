import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';

/**
 * 재측정 — 사람이 버튼을 눌렀을 때만.
 *
 * 대상 사이트를 실제로 가져오는 유일한 경로다. 화면을 여는 것만으로는 여기까지 오지
 * 않는다. 같은 주소를 하루에 여러 번 다시 재는 것은 대상 사이트에도 우리 비용에도
 * 부담이라, 저장된 결과를 여는 일과 새로 재는 일을 분명히 갈라 둔다.
 *
 * 서버에서 대신 부른다 — 접근 토큰은 httpOnly 쿠키에 있어 브라우저가 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

/** 진단은 대상 사이트를 여러 장 가져온다. 목록 조회와 시간 감각이 다르다. */
const SCAN_TIMEOUT_MS = 180_000;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '진단을 실행할 권한이 없습니다.',
  NOT_FOUND: '등록된 주소를 찾을 수 없습니다.',
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

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

export async function POST(request: Request): Promise<NextResponse> {
  let siteId = '';
  try {
    const body: unknown = await request.json();
    const parsed = asRecord(body);
    siteId = typeof parsed['siteId'] === 'string' ? parsed['siteId'] : '';
  } catch {
    return refuse('INVALID');
  }

  if (siteId === '') return refuse('INVALID', '진단할 주소가 없습니다.');

  // 잴 주소는 **등록된 값**에서 가져온다. 화면이 보낸 주소를 그대로 믿으면, 목록에
  // 보이는 주소와 실제로 잰 주소가 어긋난 채 이력에 쌓일 수 있다.
  const site = await callConsoleApi(`/api/sites/${encodeURIComponent(siteId)}`);
  if (!site.ok) return refuse(site.reason, site.message);

  const origin = asRecord(site.data)['origin'];
  if (typeof origin !== 'string' || origin === '') return refuse('NOT_FOUND');

  const outcome = await callConsoleApi('/api/seo/scans', {
    method: 'POST',
    body: { target_url: origin, site_id: siteId },
    timeoutMs: SCAN_TIMEOUT_MS,
  });
  if (!outcome.ok) return refuse(outcome.reason, outcome.message);

  return NextResponse.json({ ok: true }, { headers: NO_STORE });
}
