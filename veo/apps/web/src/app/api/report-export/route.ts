import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';
import { CONSOLE_SESSION_COOKIE } from '@/lib/session-cookie';

/**
 * 리포트 버전 내보내기 통로 — 파일이 지나가는 길일 뿐 아무것도 판단하지 않는다.
 *
 * `callConsoleApi` 를 쓰지 않는 이유: 그 통로는 JSON 봉투 전용이고, 여기는 HTML·CSV·
 * XLSX 바이트가 그대로 지나가야 한다. 토큰이 httpOnly 쿠키에 있어 브라우저가 엔진을
 * 직접 부를 수 없으므로(콘솔 전체의 경계), 이 서버 경로가 대신 부른다.
 *
 * HTML 은 첨부가 아니라 브라우저에서 바로 열리게 한다 — "발행한 문서를 본다"가 이
 * 경로의 존재 이유다. 세 형식은 같은 스냅샷의 같은 표기이므로(엔진 계약), 화면이
 * 문서를 다시 그리지 않는다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const FORMATS = new Set(['html', 'csv', 'xlsx']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const reportId = url.searchParams.get('report') ?? '';
  const version = url.searchParams.get('version') ?? '';
  const format = url.searchParams.get('format') ?? 'html';

  if (!UUID.test(reportId) || !/^\d{1,6}$/.test(version) || !FORMATS.has(format)) {
    return NextResponse.json({ message: '요청 주소가 올바르지 않습니다.' }, { status: 422 });
  }

  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return NextResponse.json(
      { message: '측정 엔진 주소가 설정되지 않았습니다.' },
      { status: 503 },
    );
  }
  const token = (await cookies()).get(CONSOLE_SESSION_COOKIE)?.value ?? '';
  if (token === '') {
    return NextResponse.json({ message: '로그인이 필요합니다.' }, { status: 401 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(
      `${baseUrl}/api/reports/${reportId}/versions/${version}/export?format=${format}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
        signal: AbortSignal.timeout(30_000),
      },
    );
  } catch {
    return NextResponse.json(
      { message: '측정 엔진에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.' },
      { status: 503 },
    );
  }

  if (!upstream.ok) {
    // 엔진의 상태 코드를 그대로 — 404(없는 버전)와 403(권한 없음)은 다른 사실이다.
    return NextResponse.json(
      { message: '문서를 가져오지 못했습니다.' },
      { status: upstream.status },
    );
  }

  const headers = new Headers();
  headers.set('Content-Type', upstream.headers.get('content-type') ?? 'application/octet-stream');
  headers.set('Cache-Control', 'no-store');
  const disposition = upstream.headers.get('content-disposition');
  if (format === 'html') {
    // 열람이 목적이므로 첨부 강제를 풀어 브라우저 안에서 바로 보이게 한다.
    headers.set('Content-Disposition', 'inline');
    // 문서는 외부 자원 없는 단일 파일 계약이다(엔진 명세). 스크립트·폼까지 잠가
    // 콘솔 원점에서 열려도 문서가 문서 이상이 되지 못하게 한다.
    headers.set('Content-Security-Policy', 'sandbox');
  } else if (disposition !== null) {
    headers.set('Content-Disposition', disposition);
  }
  return new Response(upstream.body, { status: 200, headers });
}
