import { NextResponse } from 'next/server';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';
import { callConsoleApi } from '@/lib/console-api';

/**
 * 리포트 거래처 전달 링크 발급 (P2-10a) — 얇은 통로.
 *
 * 엔진이 돌려주는 share_path 는 API 원점 기준이므로, 여기서 절대 주소로 완성해
 * 화면에 준다 — 받는 사람이 로그인 없이 여는 주소는 API 서버의 것이다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NO_STORE = { 'Cache-Control': 'no-store' } as const;

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: '요청이 올바르지 않습니다.' }, { status: 422 });
  }
  const source =
    typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const reportId = typeof source.reportId === 'string' ? source.reportId : '';
  const version = typeof source.version === 'number' ? source.version : NaN;
  if (reportId === '' || !Number.isInteger(version) || version < 1) {
    return NextResponse.json({ message: '요청이 올바르지 않습니다.' }, { status: 422 });
  }

  const outcome = await callConsoleApi<{
    share_path?: unknown;
    expires_at?: unknown;
    note_ko?: unknown;
  }>(
    `/api/reports/${encodeURIComponent(reportId)}/versions/${version}/share`,
    { method: 'POST' },
  );
  if (!outcome.ok) {
    return NextResponse.json(
      { message: outcome.message ?? '공유 링크를 만들지 못했습니다.' },
      { status: 502, headers: NO_STORE },
    );
  }

  const sharePath = typeof outcome.data.share_path === 'string' ? outcome.data.share_path : null;
  const baseUrl = resolveAuthApiBaseUrl();
  if (sharePath === null || baseUrl === null) {
    return NextResponse.json(
      { message: '공유 링크를 만들지 못했습니다.' },
      { status: 500, headers: NO_STORE },
    );
  }

  return NextResponse.json(
    {
      url: `${baseUrl}${sharePath}`,
      expiresAt: typeof outcome.data.expires_at === 'string' ? outcome.data.expires_at : null,
      noteKo: typeof outcome.data.note_ko === 'string' ? outcome.data.note_ko : null,
    },
    { headers: NO_STORE },
  );
}
