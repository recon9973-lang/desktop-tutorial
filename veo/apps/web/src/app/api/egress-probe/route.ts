/**
 * 임시 점검 창구 — **확인이 끝나면 지운다.**
 *
 * 왜 필요한가. 2026-08-05, 운영 서버(싱가포르)가 거래처 4곳 중 2곳에서 759·760바이트
 * 짜리 껍데기만 받는다. 같은 주소를 한국에서 받으면 59,976·69,296바이트에 제목·설명이
 * 전부 있다. 두 곳이 **해외 IP 를 막고 있는 것**으로 보인다.
 *
 * 그렇다면 "한국 데이터센터로 옮기면 풀리는가" 가 다음 질문인데, 여기에 답하려면
 * **한국 데이터센터에서 실제로 받아 봐야** 한다. 사무실 회선(211.62.73.88, 대구 KT)은
 * 데이터센터가 아니라서 그 답이 되지 못한다. 이 앱은 Vercel `icn1`(서울)에서 도므로,
 * 여기서 나가는 요청이 정확히 그 관측점이다.
 *
 * **입력을 받지 않는다.** 주소는 아래 목록에 박혀 있다 — 임의 주소를 받는 창구는
 * 그대로 SSRF 통로가 된다. 진단 대상은 `veo.common.security.fetcher` 의 가드를 통과한
 * 것만 허용되며, 이 파일은 그 가드를 우회하는 자리가 아니다.
 */

import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/** 운영 서버(싱가포르)에서 잰 값. 같은 주소를 여기서 받아 대조한다. */
const TARGETS = [
  { url: 'https://ipinfo.io/json', fromSingapore: null },
  { url: 'https://venomad.com', fromSingapore: 759 },
  { url: 'https://good-tour.kr', fromSingapore: 760 },
  { url: 'https://chamsarang1075.com', fromSingapore: 248927 },
  { url: 'https://koreahhospital.com', fromSingapore: 333955 },
] as const;

/** 운영 크롤러와 **같은** 신원으로 나간다. 다르게 보내면 대조가 성립하지 않는다. */
const USER_AGENT =
  'VEO-Bot/1.0 (+https://veo.seokorea.org/bot; SEO/GEO diagnostics by VENOM)';

export async function GET(): Promise<NextResponse> {
  const results = await Promise.all(
    TARGETS.map(async (target) => {
      try {
        const response = await fetch(target.url, {
          headers: {
            'user-agent': USER_AGENT,
            accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.1',
          },
          redirect: 'follow',
          cache: 'no-store',
        });
        const body = await response.text();
        return {
          url: target.url,
          status: response.status,
          finalUrl: response.url,
          bytes: body.length,
          fromSingapore: target.fromSingapore,
          // 막힌 응답이 무엇이라고 말하는지 — 이 질문에 답이 없어서 여기까지 왔다.
          head: body.slice(0, 700),
        };
      } catch (error) {
        return { url: target.url, error: String(error) };
      }
    }),
  );

  return NextResponse.json(
    { region: process.env.VERCEL_REGION ?? null, results },
    { headers: { 'cache-control': 'no-store' } },
  );
}
