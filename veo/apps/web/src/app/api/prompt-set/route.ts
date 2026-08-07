import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';

/**
 * 질문 집합 만들기 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다.
 *
 * **422 를 뭉개지 않는다.** 엔진은 집합의 균형이 맞지 않으면 무엇이 부족한지 한국어로
 * 그대로 돌려준다("신뢰·안전 의도가 없습니다" 같은). 그것을 "입력을 확인해 주십시오"
 * 로 바꾸면 만드는 사람은 무엇을 고쳐야 하는지 알 수 없고, 결국 아무 질문이나 넣어
 * 통과할 때까지 눌러 보게 된다 — 그렇게 만든 집합으로 잰 노출률은 실제보다 높다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '질문 집합을 만들 권한이 없습니다.',
  NOT_FOUND: '프로젝트를 찾을 수 없습니다.',
  CONFLICT: '같은 이름과 판의 집합이 이미 있습니다. 판 번호를 올려 주십시오.',
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

interface PromptRow {
  readonly text: string;
  readonly intent: string;
  readonly funnel: string;
  readonly subject: string;
  readonly business_importance: number;
  readonly locale: string;
}

/** 화면이 보낸 질문 줄을 엔진 계약 모양으로 옮긴다. 모르는 값은 지어내지 않고 버린다. */
function prompts(value: unknown, locale: string): PromptRow[] {
  if (!Array.isArray(value)) return [];
  const rows: PromptRow[] = [];
  for (const item of value) {
    if (typeof item !== 'object' || item === null) continue;
    const record = item as Record<string, unknown>;
    const body = text(record['text']);
    const intent = text(record['intent']);
    const funnel = text(record['funnel']);
    const subject = text(record['subject']);
    if (body === null || intent === null || funnel === null || subject === null) continue;
    const weight = Number(record['businessImportance']);
    rows.push({
      text: body,
      intent,
      funnel,
      subject,
      // 담당자의 판단이지 검색량이 아니다. 값이 안 왔으면 한가운데(0.5)로 둔다 —
      // 0 으로 두면 "중요하지 않다" 는 판단을 지어내는 것이다.
      business_importance: Number.isFinite(weight) ? Math.min(1, Math.max(0, weight)) : 0.5,
      locale,
    });
  }
  return rows;
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
  const name = text(input['name']);
  const version = text(input['version']);
  if (projectId === null) return refuse('INVALID', '프로젝트를 선택해 주십시오.');
  if (name === null) return refuse('INVALID', '집합 이름을 적어 주십시오.');
  if (version === null) return refuse('INVALID', '판 번호를 적어 주십시오.');

  const locale = text(input['locale']) ?? 'ko-KR';
  const rows = prompts(input['prompts'], locale);
  if (rows.length === 0) {
    return refuse('INVALID', '질문을 한 개 이상 넣어 주십시오.');
  }

  const outcome = await callConsoleApi('/api/observations/prompt-sets', {
    method: 'POST',
    body: {
      project_id: projectId,
      name,
      version,
      locale,
      generation_rule_ko: text(input['generationRuleKo']),
      prompts: rows,
      exclusions: [],
    },
  });

  if (!outcome.ok) {
    // 엔진이 준 이유를 그대로 넘긴다 — 균형 거부는 고칠 수 있는 안내다.
    return refuse(outcome.reason, outcome.message);
  }
  return NextResponse.json({ ok: true, promptSet: outcome.data }, { headers: NO_STORE });
}
