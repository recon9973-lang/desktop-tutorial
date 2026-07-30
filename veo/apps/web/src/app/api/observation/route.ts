import { NextResponse } from 'next/server';

import { readJob, startObservation } from '@/lib/observations';

/**
 * 관측 시작과 진행 상황 조회 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다. 화면이 토큰을
 * 들고 다니기 시작하면 XSS 하나로 조직 전체가 열린다.
 *
 * `POST` 는 **즉시 돌아온다.** 엔진이 202와 작업 하나를 주고 실행은 뒤에서 돈다.
 * 화면은 `GET` 으로 물어본다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '관측을 실행할 권한이 없습니다.',
  NOT_FOUND: '질문 집합을 찾을 수 없습니다.',
  CONFLICT: '이미 처리 중입니다.',
  INVALID: '실행 조건을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: 'AI 엔진에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '관측 중 문제가 발생했습니다.',
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
  const promptSetId = text(input['promptSetId']);
  const engine = text(input['engine']);
  const model = text(input['model']);
  const idempotencyKey = text(input['idempotencyKey']);

  if (promptSetId === null || engine === null || model === null || idempotencyKey === null) {
    return refuse('INVALID', '질문 집합과 엔진, 모델을 모두 고르셔야 합니다.');
  }

  const repetitions = Number(input['repetitions']);
  if (!Number.isInteger(repetitions) || repetitions < 1 || repetitions > 20) {
    return refuse('INVALID', '반복 횟수는 1에서 20 사이여야 합니다.');
  }

  const outcome = await startObservation({
    promptSetId,
    engine,
    model,
    // 검색을 끄면 엔진이 출처를 밝히지 않아 인용률이 0%가 아니라 **측정 불가**가 된다.
    // 그래서 화면에서는 켠 상태만 보낸다.
    searchMode: 'BROWSING',
    repetitions,
    idempotencyKey,
  });

  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, job: outcome.data }, { headers: NO_STORE });
}

export async function GET(request: Request): Promise<NextResponse> {
  const jobId = new URL(request.url).searchParams.get('job');
  if (jobId === null || jobId === '') {
    return refuse('INVALID', '작업 번호가 없습니다.');
  }

  const outcome = await readJob(jobId);
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, job: outcome.data }, { headers: NO_STORE });
}
