import { NextResponse } from 'next/server';

import { recordVerificationResult, requestVerification } from '@/lib/issues-api';

/**
 * 재측정 — 이슈가 닫히는 **유일한 길**의 통로.
 *
 * 두 단계다.
 *
 * * `step=request` — 표적 재검사를 요청한다. 이슈가 `VERIFYING` 으로 가고, 서버가
 *   *무엇을 다시 재야 하는지*(검사 하나와 URL 목록)를 돌려준다.
 * * `step=result` — 재측정한 진단 실행 번호를 낸다. **판정은 보내지 않는다** — 그 실행이
 *   남긴 검사 결과에서 서버가 도출한다.
 *
 * 이 통로에 "해결로 표시" 를 받는 자리가 없는 것은 빠뜨린 것이 아니다. 받으면 아무것도
 * 안 고치고 대시보드만 깨끗해진다.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 *
 * **409 는 덮지 않는다.** 엔진의 거부 문장은 지금 갈 수 있는 상태를 이름으로 알려 준다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '재측정을 기록할 권한이 없습니다.',
  NOT_FOUND: '그 이슈 또는 진단을 찾을 수 없습니다.',
  CONFLICT: '지금 상태에서는 할 수 없습니다.',
  INVALID: '요청 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '재측정을 처리하는 중 문제가 발생했습니다.',
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
  const issueId = text(input['issueId']);
  const step = text(input['step']);
  if (issueId === null || (step !== 'request' && step !== 'result')) {
    return refuse('INVALID');
  }

  if (step === 'request') {
    const outcome = await requestVerification(issueId);
    if (!outcome.ok) return refuse(outcome.reason, outcome.message);
    return NextResponse.json({ ok: true, requested: outcome.data }, { headers: NO_STORE });
  }

  const scanRunId = text(input['scanRunId']);
  if (scanRunId === null) {
    return refuse('INVALID', '어느 진단으로 확인할지 골라 주십시오.');
  }

  const outcome = await recordVerificationResult(issueId, scanRunId);
  if (!outcome.ok) return refuse(outcome.reason, outcome.message);
  return NextResponse.json({ ok: true, recorded: outcome.data }, { headers: NO_STORE });
}
