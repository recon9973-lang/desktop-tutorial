/**
 * `/sitemap.xml` — 검색엔진에게 "이 사이트에 이런 페이지가 있다" 고 알린다.
 *
 * 2026-08-06 실측: 우리 진단이 우리 사이트에서 **"robots.txt와 관례 경로 어디에서도
 * 사이트맵을 찾지 못했습니다"** 를 잡아냈다. 우리가 파는 검사에 우리가 걸린 것이다.
 *
 * 여기 싣는 것은 **검색에 잡히라고 만든 주소뿐**이다(`PUBLIC_PATHS`). 거래처 결과
 * 링크나 초대 링크는 절대 들어가지 않는다 — robots 로 막아 놓고 사이트맵으로
 * 알려 주면 막은 의미가 없다. 두 파일이 같은 목록을 보는 이유다.
 */

import type { MetadataRoute } from 'next';

import { PUBLIC_PATHS, absoluteUrl } from '@/lib/site';

/** 홈이 가장 중요하고, 무료 도구가 그다음이다. 크롤러에게 주는 힌트일 뿐이다. */
const PRIORITY: Record<string, number> = {
  '/': 1.0,
  '/tools/seo': 0.8,
  '/tools/geo': 0.8,
  '/tools/naver-keyword': 0.8,
  '/bot': 0.3,
};

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.map((path) => ({
    url: absoluteUrl(path),
    priority: PRIORITY[path] ?? 0.5,
  }));
}
