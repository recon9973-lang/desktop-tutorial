import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';

/**
 * 의료광고 원고 검수 (P2-11) — 얇은 통로. 원고는 어디에도 저장되지 않는다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store' } as const;

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: '원고를 확인해 주십시오.' }, { status: 422 });
  }
  const source =
    typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const text = typeof source.text === 'string' ? source.text : '';
  if (text.trim() === '') {
    return NextResponse.json({ message: '검수할 원고를 입력해 주십시오.' }, { status: 422 });
  }

  const outcome = await callConsoleApi('/api/medical/copy-reviews', {
    method: 'POST',
    body: { text },
  });
  if (!outcome.ok) {
    return NextResponse.json(
      { message: outcome.message ?? '검수하지 못했습니다. 다시 시도해 주십시오.' },
      { status: 502, headers: NO_STORE },
    );
  }
  return NextResponse.json({ result: outcome.data }, { headers: NO_STORE });
}
