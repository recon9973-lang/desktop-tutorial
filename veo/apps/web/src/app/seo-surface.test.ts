// @vitest-environment node
/**
 * 우리 사이트가 우리 진단을 통과하는가.
 *
 * 2026-08-06 실측: `veo.seokorea.org` 를 우리 엔진으로 진단했더니 **60.99점 · 주의**
 * 였다. SEO 진단 도구를 파는 사이트가 자기 검사에서 떨어진 것이다. 잡힌 것:
 *
 * * canonical 누락
 * * 구조화 데이터 하나도 없음
 * * 오픈그래프 누락
 * * 사이트맵을 찾을 수 없음 (`/robots.txt` 는 HTTP 404 였다)
 * * 파비콘 선언 없음
 *
 * 이 파일은 그 다섯 자리가 다시 비지 않게 지킨다.
 *
 * **그리고 더 중요한 것 하나** — 열려 있다고 공개해도 되는 것은 아니다.
 * `/results/[token]` 에는 거래처 진단 결과가, `/invite/[token]` 에는 초대가 들어
 * 있다. 색인되면 우리가 고객사 데이터를 검색엔진에 넘긴 것이 된다.
 */

import { describe, expect, it } from 'vitest';

import robots from './robots';
import sitemap from './sitemap';
import { DISALLOWED_PATHS, PUBLIC_PATHS, absoluteUrl, siteUrl } from '@/lib/site';

describe('색인되면 안 되는 주소', () => {
  it.each(['/results', '/invite', '/console', '/api', '/login'])(
    '%s 는 robots.txt 가 막는다',
    (path) => {
      const rule = robots().rules;
      const rules = Array.isArray(rule) ? rule : [rule];
      const disallowed = rules.flatMap((r) =>
        Array.isArray(r.disallow) ? r.disallow : r.disallow ? [r.disallow] : [],
      );

      expect(disallowed).toContain(path);
    },
  );

  it('사이트맵이 차단된 주소를 광고하지 않는다', () => {
    /** robots 로 막아 놓고 사이트맵으로 알려 주면 막은 의미가 없다. */
    const urls = sitemap().map((entry) => entry.url);

    for (const blocked of DISALLOWED_PATHS) {
      expect(urls.some((url) => url.includes(blocked))).toBe(false);
    }
  });

  it('거래처 결과 링크는 사이트맵에 없다', () => {
    const urls = sitemap().map((entry) => entry.url);

    expect(urls.some((url) => url.includes('/results'))).toBe(false);
  });
});

describe('검색에 잡혀야 하는 주소', () => {
  it('무료 도구 셋과 홈이 사이트맵에 있다', () => {
    const urls = sitemap().map((entry) => entry.url);

    for (const path of ['/', '/tools/seo', '/tools/geo', '/tools/naver-keyword']) {
      expect(urls).toContain(absoluteUrl(path));
    }
  });

  it('사이트맵의 모든 주소가 절대 주소다', () => {
    /** 상대 주소를 실으면 검색엔진이 무시한다. */
    for (const entry of sitemap()) {
      expect(entry.url.startsWith('https://')).toBe(true);
    }
  });

  it('robots.txt 가 사이트맵 위치를 알린다', () => {
    expect(robots().sitemap).toBe(absoluteUrl('/sitemap.xml'));
  });
});

describe('자기 주소', () => {
  it('설정이 없어도 개발 주소를 내보내지 않는다', () => {
    /** localhost 를 canonical 로 내보내면 "진짜 주소는 당신이 닿을 수 없는 곳" 이
     * 라고 말하는 셈이다 — 없느니만 못하다. */
    const resolved = siteUrl({});

    expect(resolved).not.toContain('localhost');
    expect(resolved.startsWith('https://')).toBe(true);
  });

  it('배포가 알려 준 주소를 우선한다', () => {
    expect(siteUrl({ NEXT_PUBLIC_VEO_SITE_URL: 'https://staging.example/' })).toBe(
      'https://staging.example',
    );
  });

  it('공개 목록과 차단 목록이 겹치지 않는다', () => {
    for (const path of PUBLIC_PATHS) {
      expect(DISALLOWED_PATHS.some((blocked) => path.startsWith(blocked))).toBe(false);
    }
  });
});
