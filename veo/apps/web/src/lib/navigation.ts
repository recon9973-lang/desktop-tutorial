import { hasPermission } from './permissions';
import type { Permission, PermissionHolder } from './permissions';

export interface NavItem {
  readonly href: string;
  readonly label: string;
  readonly description: string;
}

/**
 * A console area, and the permission needed to open it.
 *
 * Only read permissions appear here: navigating somewhere is not an action, and
 * a link is never the thing that authorises one. What a role may *do* inside an
 * area is decided by the API, and gated in the page with `PermissionGate`.
 */
export interface ConsoleNavItem extends NavItem {
  readonly permission: Permission;
}

export const PUBLIC_NAV: readonly NavItem[] = [
  {
    href: '/tools/seo',
    label: 'SEO 점검',
    description: '검색엔진이 사이트를 발견·크롤링·해석할 수 있는지 확인합니다.',
  },
  {
    href: '/tools/geo',
    label: 'GEO 점검',
    description: 'AI 답변 엔진이 페이지를 읽고 검증할 수 있는지 확인합니다.',
  },
  {
    href: '/tools/naver-keyword',
    label: '네이버 키워드',
    description: '네이버 검색 수요와 경쟁 상황을 출처와 함께 확인합니다.',
  },
];

export const CONSOLE_NAV: readonly ConsoleNavItem[] = [
  {
    href: '/console/dashboard',
    label: '대시보드',
    description: '전체 현황 요약',
    permission: 'scan:read',
  },
  {
    href: '/console/projects',
    label: '프로젝트',
    description: '측정 대상 사이트 관리',
    permission: 'project:read',
  },
  {
    href: '/console/seo',
    label: 'SEO',
    description: 'SEO 기술 준비도',
    permission: 'scan:read',
  },
  {
    href: '/console/geo',
    label: 'GEO',
    description: 'GEO 준비도와 AI 가시성 관측',
    permission: 'observation:read',
  },
  {
    href: '/console/keywords',
    label: '키워드',
    description: '네이버 키워드 인텔리전스',
    permission: 'keyword:read',
  },
  {
    href: '/console/competitors',
    label: '경쟁사',
    description: '비교 대상 사이트',
    permission: 'competitor:read',
  },
  {
    href: '/console/issues',
    label: '이슈',
    description: '조치가 필요한 항목',
    permission: 'issue:read',
  },
  {
    href: '/console/reports',
    label: '리포트',
    description: '공유용 리포트',
    permission: 'report:read',
  },
  {
    href: '/console/scoring-versions',
    label: '채점 기준 버전',
    description: '적용 중인 채점 명세',
    permission: 'scoring_spec:read',
  },
];

/**
 * The console areas an identity may actually open.
 *
 * Hiding a link is a courtesy, not a control: every console page also gates its
 * own content, so a hand-typed URL lands on "권한이 없습니다" rather than on data.
 */
export function visibleConsoleNav(
  identity: PermissionHolder | null | undefined,
): readonly ConsoleNavItem[] {
  return CONSOLE_NAV.filter((item) => hasPermission(identity, item.permission));
}
