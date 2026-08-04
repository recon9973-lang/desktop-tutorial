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
  /**
   * The permission needed to open this area, or `null` for one that belongs to
   * every signed-in person.
   *
   * Account settings is the case that made this nullable: gating "change my own
   * password" behind a permission would hide it from exactly the accounts that
   * hold none, which are the ones most likely to need it.
   */
  readonly permission: Permission | null;
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
    href: '/console/customers',
    label: '업체 관리',
    description: '업체와 측정 URL',
    permission: 'customer:read',
  },
  // 프로젝트(측정 단위 설정)는 업체 관리의 하위 화면(/console/customers/projects)으로
  // 옮겼다 — 사용자에게 "업체 관리" 와 "프로젝트" 는 같은 일(측정 대상 등록)로 읽혀
  // 메뉴 둘이 서로를 가렸다(사용자 감사). 업체 관리 화면 안에서 연결한다.
  {
    href: '/console/seo',
    label: '진단',
    // 한 번 재면 SEO·GEO 두 눈금이 함께 나온다. 메뉴를 눈금별로 나누면 "두 번 재야
    // 하나" 로 읽히고, 실제로 그렇게 두 번 재던 화면이 있었다.
    description: 'SEO·GEO 준비도 — 한 번 측정, 두 눈금',
    permission: 'scan:read',
  },
  {
    href: '/console/geo',
    label: 'AI 가시성',
    // 준비도와 성격이 다르다: 밖에서 관측되고, 건당 비용이 나가고, 사람이 검수한다.
    description: 'AI 답변에 우리가 나오는지 관측',
    permission: 'observation:read',
  },
  {
    href: '/console/review',
    // "위험 검수" 와 "의료광고 검수" 는 이름이 비슷해 같은 일로 읽혔다(사용자 감사).
    // 대상을 이름에 넣는다 — 이쪽은 AI 답변, 저쪽은 우리 원고.
    label: 'AI 답변 검수',
    description: 'AI 답변 지적을 사람이 확인',
    permission: 'observation:review',
  },
  {
    href: '/console/keywords',
    label: '키워드',
    description: '네이버 키워드 인텔리전스',
    permission: 'keyword:read',
  },
  {
    href: '/console/competitors',
    // 화면의 실제 일은 경쟁사 분석이 아니라 "AI 답변 속 어느 상호가 이 고객인가" 의
    // 식별 정보 등록이다 — 화면 제목(브랜드 식별)은 먼저 바뀌었는데 메뉴만 옛 이름이었다.
    label: '브랜드 식별',
    description: 'AI 답변에서 우리 상호 가려내기',
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
    href: '/console/medical',
    label: '원고 표현 검수',
    description: '원고의 의료광고법 검토 필요 표현 표시',
    permission: 'scan:read',
  },
  {
    href: '/console/usage',
    label: '사용량·비용',
    description: 'AI 호출과 이번 달 지출',
    permission: 'usage:read',
  },
  {
    href: '/console/scoring-versions',
    label: '채점 기준 버전',
    description: '적용 중인 채점 명세',
    permission: 'scoring_spec:read',
  },
  {
    href: '/console/team',
    label: '팀원 관리',
    description: '초대와 역할',
    permission: 'user:read',
  },
  {
    href: '/console/changelog',
    label: '변경 이력',
    description: '버전별로 무엇이 바뀌었나',
    // 릴리스 노트는 콘솔에 들어온 모두가 본다 — 권한 게이트 없음(화면과 동일).
    permission: null,
  },
  {
    href: '/console/account',
    label: '내 계정',
    description: '비밀번호 변경',
    permission: null,
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
  // No identity means no console at all. A `null` permission means "every signed-in
  // person", not "everyone" — without this guard the account link would show to a
  // visitor who is not logged in, which is both wrong and confusing.
  if (identity === null || identity === undefined) return [];
  return CONSOLE_NAV.filter(
    (item) => item.permission === null || hasPermission(identity, item.permission),
  );
}
