import { NextResponse } from 'next/server';

import { reviewStep } from '@/lib/observations';

/**
 * 검수 한 걸음 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 *
 * **409 와 422 를 합치지 않는다.** 전자는 "다른 검수자가 맡고 있다" — 지금은 안 되지만
 * 나중엔 된다. 후자는 "맡지도 않고 판정하려 한다" — 이 순서로는 영영 안 된다. 둘을 같은
 * 문장으로 덮으면 검수자가 새로고침만 반복하게 된다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '위험 지적을 검수할 권한이 없습니다.',
  NOT_FOUND: '그 판정을 찾을 수 없습니다. 이미 처리되었을 수 있습니다.',
  CONFLICT: '다른 검수자가 맡고 있는 건입니다.',
  INVALID: '이 순서로는 처리할 수 없습니다. 먼저 착수해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '검수 중 문제가 발생했습니다.',
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

const STEPS = new Set(['claim', 'release', 'decide']);
const DECISIONS = new Set(['CONFIRMED', 'REJECTED', 'NEEDS_MORE_EVIDENCE']);

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
  const assessmentId = text(input['assessmentId']);
  const step = text(input['step']);
  if (assessmentId === null || step === null || !STEPS.has(step)) {
    return refuse('INVALID', '요청 내용을 확인해 주십시오.');
  }

  let payload:
    | {
        readonly decision: 'CONFIRMED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE';
        readonly rejection_reason?: string | null;
        readonly note_ko?: string | null;
      }
    | undefined;

  if (step === 'decide') {
    const decision = text(input['decision']);
    if (decision === null || !DECISIONS.has(decision)) {
      return refuse('INVALID', '검수 결론을 선택해 주십시오.');
    }
    const reason = text(input['rejectionReason']);
    // 기각에 사유가 없으면 엔진이 422 로 막지만, 여기서 먼저 막는 편이 낫다. 왕복 한 번을
    // 아끼자는 것이 아니라, 사유 없는 기각은 자동 판정이 어디서 빗나가는지 세는 데
    // 아무 도움이 안 되기 때문이다.
    if (decision === 'REJECTED' && reason === null) {
      return refuse('INVALID', '기각에는 사유가 필요합니다.');
    }
    payload = {
      decision: decision as 'CONFIRMED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE',
      rejection_reason: reason,
      note_ko: text(input['note']),
    };
  }

  const outcome = await reviewStep(
    assessmentId,
    step as 'claim' | 'release' | 'decide',
    payload,
  );
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, item: outcome.data }, { headers: NO_STORE });
}
