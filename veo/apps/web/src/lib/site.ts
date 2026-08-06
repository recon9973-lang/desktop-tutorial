/**
 * 이 사이트가 **바깥에 알리는 자기 주소**, 그리고 어디를 공개하는가.
 *
 * ## 왜 한 곳에 모으나
 *
 * canonical · 사이트맵 · robots.txt · 오픈그래프는 전부 "이 페이지의 진짜 주소는
 * 무엇인가" 를 말한다. 네 곳이 각자 주소를 만들면 언젠가 서로 어긋나고, 어긋난
 * canonical 은 검색엔진에게 **우리가 우리 페이지를 부정하는** 신호가 된다.
 *
 * ## 공개와 비공개를 여기서 가른다
 *
 * 이 앱에는 **색인되면 안 되는 공개 주소**가 있다. 로그인 없이 열리지만 남에게
 * 보여서는 안 되는 것들이다:
 *
 * * `/results/[token]` — 거래처에게 보낸 진단 결과. **고객사 데이터가 들어 있다.**
 * * `/invite/[token]` — 초대 링크. 색인되면 초대가 새어 나간다.
 * * `/login` — 색인할 이유가 없다.
 *
 * 검색에 잡히라고 만든 것은 홈·크롤러 안내·무료 도구 셋뿐이다. 사이트맵과 robots 가
 * **같은 목록**을 보게 해서, 한쪽만 고치는 실수를 막는다.
 */

/**
 * 우리 자신의 주소. 배포 환경이 알려 주는 값을 우선하고, 없으면 운영 주소로 둔다.
 *
 * 기본값을 개발 주소(`localhost`)로 두지 않는 이유: 그러면 설정을 잊은 배포가
 * `http://localhost:3000/...` 을 canonical 로 내보낸다. 검색엔진에게 "이 페이지의
 * 진짜 주소는 당신이 닿을 수 없는 곳" 이라고 말하는 셈이라, 없느니만 못하다.
 */
export function siteUrl(env: Record<string, string | undefined> = process.env): string {
  const configured = (env['NEXT_PUBLIC_VEO_SITE_URL'] ?? '').trim();
  if (configured !== '') return configured.replace(/\/+$/, '');
  return 'https://veo.seokorea.org';
}

/** 검색에 잡히라고 만든 주소. 사이트맵에 실리는 것도 이것뿐이다. */
export const PUBLIC_PATHS = ['/', '/bot', '/tools/seo', '/tools/geo', '/tools/naver-keyword'] as const;

/**
 * 크롤러가 들어오면 안 되는 곳.
 *
 * `/results` 와 `/invite` 가 여기 있는 것이 핵심이다 — 열려 있다고 공개해도 되는
 * 것은 아니다. 토큰을 아는 사람만 보라고 만든 주소가 검색결과에 뜨면, 우리가
 * 거래처 데이터를 검색엔진에 넘긴 것이 된다.
 */
export const DISALLOWED_PATHS = ['/console', '/api', '/results', '/invite', '/login'] as const;

/** 절대 주소로 만든다. canonical·사이트맵·오픈그래프가 같은 함수를 쓴다. */
export function absoluteUrl(path: string, env?: Record<string, string | undefined>): string {
  const base = siteUrl(env);
  return path === '/' ? `${base}/` : `${base}${path}`;
}
