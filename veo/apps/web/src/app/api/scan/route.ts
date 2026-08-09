import { randomUUID } from 'node:crypto';

import { NextResponse } from 'next/server';

import { callConsoleApi } from '@/lib/console-api';
import { findOrCreateSiteByOrigin } from '@/lib/companies';
import { readJob } from '@/lib/observations';
import { record } from '@/lib/json';
import { NO_STORE, refuse } from '@/lib/route-reply';

/**
 * 재측정 — 사람이 버튼을 눌렀을 때만.
 *
 * 대상 사이트를 실제로 가져오는 유일한 경로다. 화면을 여는 것만으로는 여기까지 오지
 * 않는다. 같은 주소를 하루에 여러 번 다시 재는 것은 대상 사이트에도 우리 비용에도
 * 부담이라, 저장된 결과를 여는 일과 새로 재는 일을 분명히 갈라 둔다.
 *
 * 서버에서 대신 부른다 — 접근 토큰은 httpOnly 쿠키에 있어 브라우저가 읽지 못한다.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';


const MESSAGES: Record<string, string> = {
  SIGNED_OUT: '로그인이 만료되었습니다. 다시 로그인해 주십시오.',
  FORBIDDEN: '진단을 실행할 권한이 없습니다.',
  NOT_FOUND: '등록된 주소를 찾을 수 없습니다.',
  CONFLICT: '이미 처리 중입니다.',
  INVALID: '주소를 확인해 주십시오.',
  RATE_LIMITED: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.',
  UNREACHABLE: '대상 사이트에서 응답을 받지 못했습니다. 사이트 상태를 확인해 주십시오.',
  UNAVAILABLE: '서버에 연결하지 못했습니다.',
  NOT_CONFIGURED: '서버 주소가 설정되지 않았습니다.',
  SERVER_ERROR: '진단 중 문제가 발생했습니다.',
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



export async function POST(request: Request): Promise<NextResponse> {
  let siteId = '';
  let url = '';
  try {
    const body: unknown = await request.json();
    const parsed = record(body);
    siteId = typeof parsed['siteId'] === 'string' ? parsed['siteId'] : '';
    url = typeof parsed['url'] === 'string' ? parsed['url'] : '';
  } catch {
    return refuse('INVALID', null, MESSAGES, STATUS);
  }

  // 주소만 온 경우: 등록을 먼저 시키지 않는다. 잴 자리를 여기서 만들어 준다.
  if (siteId === '' && url !== '') {
    const created = await findOrCreateSiteByOrigin(url, randomUUID().slice(0, 8));
    if (!created.ok) {
      if (created.reason !== 'API') {
        return refuse('INVALID', '주소를 확인해 주십시오. 예: ondam.co.kr', MESSAGES, STATUS);
      }
      const failed = created.outcome;
      return refuse(
        failed.ok ? 'SERVER_ERROR' : failed.reason,
        failed.ok ? null : failed.message,
        MESSAGES,
        STATUS,
      );
    }
    siteId = created.siteId;
  }

  if (siteId === '') return refuse('INVALID', '진단할 주소가 없습니다.', MESSAGES, STATUS);

  // 잴 주소는 **등록된 값**에서 가져온다. 화면이 보낸 주소를 그대로 믿으면, 목록에
  // 보이는 주소와 실제로 잰 주소가 어긋난 채 이력에 쌓일 수 있다.
  const site = await callConsoleApi(`/api/sites/${encodeURIComponent(siteId)}`);
  if (!site.ok) return refuse(site.reason, site.message, MESSAGES, STATUS);

  const origin = record(site.data)['origin'];
  if (typeof origin !== 'string' || origin === '') return refuse('NOT_FOUND', null, MESSAGES, STATUS);

  // 진단은 **작업**으로 돈다(P1-6) — 이 요청은 작업 표만 받고 즉시 돌아가고,
  // 화면이 아래 GET 으로 진행을 물어본다. 240초짜리 HTTP 요청에 기대던 시절의
  // 타임아웃 문제(느린 사이트가 완주 직전에 끊김)가 여기서 사라진다.
  const outcome = await callConsoleApi('/api/seo/scan-jobs', {
    method: 'POST',
    body: { target_url: origin, site_id: siteId },
  });
  if (!outcome.ok) return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);

  const jobId = record(outcome.data)['id'];
  return NextResponse.json(
    { ok: true, siteId, jobId: typeof jobId === 'string' ? jobId : null },
    { headers: NO_STORE },
  );
}

/** 도는 진단의 진행 조회 — 폴링 한 번이 잡 표 한 장이다. */
export async function GET(request: Request): Promise<NextResponse> {
  const jobId = new URL(request.url).searchParams.get('job') ?? '';
  if (jobId === '') return refuse('INVALID', '조회할 작업이 없습니다.', MESSAGES, STATUS);

  const outcome = await readJob(jobId);
  if (!outcome.ok) return refuse(outcome.reason, outcome.message, MESSAGES, STATUS);
  return NextResponse.json({ job: outcome.data }, { headers: NO_STORE });
}
