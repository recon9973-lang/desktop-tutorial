import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';
import { record, text } from '@/lib/json';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 경보 시험 발송 — 브라우저가 엔진에 직접 말을 걸지 않도록 하는 통로.
 *
 * 알림 주소를 넣고도 **맞는지 알 방법이 없었다.** 경보는 사고가 났을 때만 울리므로,
 * 설정한 사람이 확인할 길이 없다. 이 창구가 그 길이다.
 *
 * **주소는 오가지 않는다.** 응답에 들어 있는 것은 닿았는지 여부와 사람이 읽을 한 문장
 * 뿐이다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '경보를 시험할 권한이 없습니다.',
  NOT_FOUND: '창구를 찾을 수 없습니다.',
  CONFLICT: '지금 상태에서는 할 수 없습니다.',
  INVALID: '요청 내용을 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '서버에서 응답을 받지 못했습니다.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '시험 발송 중 문제가 발생했습니다.',
};

export async function POST(): Promise<NextResponse> {
  const outcome = await callConsoleApi('/api/usage/alert-test', { method: 'POST' });
  if (!outcome.ok) {
    return refuse(outcome.reason ?? 'SERVER_ERROR', outcome.message, MESSAGES);
  }

  const body = record(outcome.data);
  return NextResponse.json(
    { ok: true, outcome: text(body, 'outcome'), messageKo: text(body, 'message_ko') },
    { status: 200, headers: NO_STORE },
  );
}
