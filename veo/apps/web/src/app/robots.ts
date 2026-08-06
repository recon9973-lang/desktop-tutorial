/**
 * `/robots.txt` — 크롤러에게 어디를 봐도 되는지 알린다.
 *
 * 2026-08-06 실측: 이 주소가 **HTTP 404** 였다. SEO 진단 도구를 파는 사이트에
 * robots.txt 가 없었다.
 *
 * ## 막는 쪽이 더 중요하다
 *
 * 이 앱에는 **로그인 없이 열리지만 색인되면 안 되는** 주소가 있다.
 * `/results/[token]` 은 거래처에게 보낸 진단 결과이고 **고객사 데이터가 들어 있다.**
 * `/invite/[token]` 은 초대 링크다. 토큰을 아는 사람만 보라고 만든 주소가 검색결과에
 * 뜨면, 우리가 거래처 데이터를 검색엔진에 넘긴 것이 된다.
 *
 * 공개 목록과 차단 목록은 `lib/site.ts` 한 곳에 있고 사이트맵도 같은 것을 본다 —
 * 한쪽만 고치면 사이트맵이 차단된 주소를 광고하는 상태가 된다.
 */

import type { MetadataRoute } from 'next';

import { DISALLOWED_PATHS, absoluteUrl } from '@/lib/site';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [...DISALLOWED_PATHS],
      },
    ],
    sitemap: absoluteUrl('/sitemap.xml'),
  };
}
