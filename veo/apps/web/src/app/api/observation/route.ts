import { NextResponse } from 'next/server';

import { readJob, startObservation } from '@/lib/observations';
import { NO_STORE, refuse } from '@/lib/route-reply';

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


function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
}

/** VEO 가 아는 검색 모드. `UNKNOWN` 은 관측을 **시작할 때** 고를 수 있는 값이 아니다. */
const SEARCH_MODES = new Set(['BROWSING', 'NO_BROWSING']);

/**
 * 고른 검색 모드들을 읽는다. 하나도 없거나 모르는 값이 섞이면 `null` 이다.
 *
 * 모르는 값을 조용히 `BROWSING` 으로 떨어뜨리지 않는다. 그러면 화면이 끔을 보냈다고
 * 믿는데 실제로는 켬으로 돌아, 검색해서 나온 답이 "검색 끔" 자리에 앉는다.
 */
function readSearchModes(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const chosen = [...new Set(value.filter((one): one is string => typeof one === 'string'))];
  if (chosen.length === 0 || chosen.some((one) => !SEARCH_MODES.has(one))) return null;
  return chosen;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.', MESSAGES, STATUS);
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const promptSetId = text(input['promptSetId']);
  const engine = text(input['engine']);
  const model = text(input['model']);
  const idempotencyKey = text(input['idempotencyKey']);

  if (promptSetId === null || engine === null || model === null || idempotencyKey === null) {
    return refuse('INVALID', '질문 집합과 엔진, 모델을 모두 고르셔야 합니다.', MESSAGES, STATUS);
  }

  const repetitions = Number(input['repetitions']);
  if (!Number.isInteger(repetitions) || repetitions < 1 || repetitions > 20) {
    return refuse('INVALID', '반복 횟수는 1에서 20 사이여야 합니다.', MESSAGES, STATUS);
  }

  const searchModes = readSearchModes(input['searchModes']);
  if (searchModes === null) {
    return refuse('INVALID', '검색 모드는 켬·끔 중 적어도 하나를 고르셔야 합니다.', MESSAGES, STATUS);
  }

  const outcome = await startObservation({
    promptSetId,
    engine,
    model,
    searchModes,
    repetitions,
    idempotencyKey,
  });

  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  }
  return NextResponse.json({ ok: true, job: outcome.data }, { headers: NO_STORE });
}

export async function GET(request: Request): Promise<NextResponse> {
  const jobId = new URL(request.url).searchParams.get('job');
  if (jobId === null || jobId === '') {
    return refuse('INVALID', '작업 번호가 없습니다.', MESSAGES, STATUS);
  }

  const outcome = await readJob(jobId);
  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  }
  return NextResponse.json({ ok: true, job: outcome.data }, { headers: NO_STORE });
}
