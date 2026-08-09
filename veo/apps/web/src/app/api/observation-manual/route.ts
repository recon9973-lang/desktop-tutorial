import { NextResponse } from 'next/server';

import { estimateObservation, startManualObservation } from '@/lib/observations';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 수동 측정 — 관리자가 그 자리에서 고른 검색어를 잰다.
 *
 * 정기 관측(`/api/observation`)과 갈라 둔 이유는 **둘이 다른 측정이기 때문**이다.
 * 정기 관측은 발행된 질문 집합을 돌리고, 이쪽은 사람이 그 순간 검색어를 고른다.
 * 여기로 만들어진 실행은 `kind=MANUAL` 로 남아 추이에 올라가지 않는다.
 *
 * `GET` 은 **누르기 전 예상 규모**다. 돈이 나가는 일이라, 몇 번 부르는지 먼저 보여준다.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다. 화면이 토큰을
 * 들고 다니기 시작하면 XSS 하나로 조직 전체가 열린다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '수동 측정을 실행할 권한이 없습니다.',
  NOT_FOUND: '프로젝트를 찾을 수 없습니다.',
  CONFLICT: '이미 처리 중입니다.',
  INVALID: '실행 조건을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: 'AI 엔진에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '수동 측정 중 문제가 발생했습니다.',
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

/** VEO 가 아는 검색 모드. `UNKNOWN` 은 측정을 **시작할 때** 고를 수 있는 값이 아니다. */
const SEARCH_MODES = new Set(['BROWSING', 'NO_BROWSING']);

/**
 * 고른 검색 모드들. 모르는 값이 섞이면 `null` 이다.
 *
 * 모르는 값을 조용히 `BROWSING` 으로 떨어뜨리지 않는다 — 그러면 화면이 끔을 보냈다고
 * 믿는데 실제로는 켬으로 돌아, 검색해서 나온 답이 "검색 끔" 자리에 앉는다.
 */
function readSearchModes(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const chosen = [...new Set(value.filter((one): one is string => typeof one === 'string'))];
  if (chosen.length === 0 || chosen.some((one) => !SEARCH_MODES.has(one))) return null;
  return chosen;
}

/** 최대 20개. 서버와 같은 상한이다 — 여기서 더 받아 봐야 서버가 거절한다. */
const MAX_QUESTIONS = 20;

function readQuestions(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const cleaned = value
    .filter((one): one is string => typeof one === 'string')
    .map((one) => one.trim())
    .filter((one) => one !== '');
  const unique = [...new Set(cleaned)];
  if (unique.length === 0 || unique.length > MAX_QUESTIONS) return null;
  return unique;
}

function readRepetitions(value: unknown): number | null {
  const repetitions = Number(value);
  if (!Number.isInteger(repetitions) || repetitions < 1 || repetitions > 20) return null;
  return repetitions;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return refuse('INVALID', '요청을 읽지 못했습니다.', MESSAGES, STATUS);
  }

  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const projectId = text(input['projectId']);
  const engine = text(input['engine']);
  const model = text(input['model']);
  const idempotencyKey = text(input['idempotencyKey']);

  if (projectId === null || engine === null || model === null || idempotencyKey === null) {
    return refuse('INVALID', '프로젝트와 엔진, 모델을 모두 고르셔야 합니다.', MESSAGES, STATUS);
  }

  const questions = readQuestions(input['questions']);
  if (questions === null) {
    return refuse('INVALID', `검색어를 1개에서 ${MAX_QUESTIONS}개 사이로 넣어 주십시오.`, MESSAGES, STATUS);
  }

  const repetitions = readRepetitions(input['repetitions']);
  if (repetitions === null) {
    return refuse('INVALID', '반복 횟수는 1에서 20 사이여야 합니다.', MESSAGES, STATUS);
  }

  const searchModes = readSearchModes(input['searchModes']);
  if (searchModes === null) {
    return refuse('INVALID', '검색 모드는 켬·끔 중 적어도 하나를 고르셔야 합니다.', MESSAGES, STATUS);
  }

  const outcome = await startManualObservation({
    projectId,
    questions,
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
  const params = new URL(request.url).searchParams;

  const engine = text(params.get('engine'));
  const model = text(params.get('model'));
  if (engine === null || model === null) {
    return refuse('INVALID', '엔진과 모델이 필요합니다.', MESSAGES, STATUS);
  }

  const questionCount = Number(params.get('questions'));
  if (!Number.isInteger(questionCount) || questionCount < 1 || questionCount > MAX_QUESTIONS) {
    return refuse('INVALID', '검색어 개수를 확인해 주십시오.', MESSAGES, STATUS);
  }

  const repetitions = readRepetitions(params.get('repetitions'));
  if (repetitions === null) {
    return refuse('INVALID', '반복 횟수는 1에서 20 사이여야 합니다.', MESSAGES, STATUS);
  }

  const searchModes = readSearchModes(params.getAll('mode'));
  if (searchModes === null) {
    return refuse('INVALID', '검색 모드는 켬·끔 중 적어도 하나를 고르셔야 합니다.', MESSAGES, STATUS);
  }

  const outcome = await estimateObservation({
    questionCount,
    engine,
    model,
    searchModes,
    repetitions,
  });

  if (!outcome.ok) {
    return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  }
  return NextResponse.json({ ok: true, estimate: outcome.data }, { headers: NO_STORE });
}
