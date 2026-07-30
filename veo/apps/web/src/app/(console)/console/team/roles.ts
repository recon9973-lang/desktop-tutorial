/**
 * 역할 목록과 그 역할이 실제로 할 수 있는 일.
 *
 * `lib/team.ts` 가 아니라 여기 두는 이유: 저쪽은 `server-only` 라 세션 쿠키를 읽는
 * 서버 코드이고, 브라우저에서 불러오면 빌드가 깨진다. 초대 화면의 역할 선택은
 * 브라우저에서 도는 코드이므로 상수만 따로 둔다.
 *
 * 목록 자체는 엔진이 정한다(`Role` 열거형). 화면이 임의로 늘리거나 줄이면, 여기서만
 * 고를 수 있는 역할이 생기거나 엔진이 아는 역할이 화면에서 사라진다.
 */

export const ROLES = [
  'SUPER_ADMIN',
  'LAB_ADMIN',
  'ANALYST',
  'DEVELOPER',
  'SALES_VIEWER',
  'CLIENT_VIEWER',
] as const;

export type Role = (typeof ROLES)[number];

/**
 * 이름만 보고는 고를 수 없다 — `LAB_ADMIN` 과 `SUPER_ADMIN` 의 차이가 이름에 없고,
 * 잘못 고르면 직원이 못 하는 일이 생기거나 하면 안 되는 일을 할 수 있게 된다.
 */
export const ROLE_LABELS: Record<Role, { readonly label: string; readonly note: string }> = {
  SUPER_ADMIN: {
    label: '최고 관리자',
    note: '팀원 초대와 역할 변경까지 모두 가능합니다. 꼭 필요한 사람에게만 주십시오.',
  },
  LAB_ADMIN: {
    label: '운영 관리자',
    note: '진단·리포트·업체를 관리합니다. 팀원 관리는 하지 못합니다.',
  },
  ANALYST: {
    label: '분석가',
    note: '진단을 돌리고 결과를 봅니다. 대부분의 직원이 여기 해당합니다.',
  },
  DEVELOPER: {
    label: '개발',
    note: '진단 결과와 연동 설정을 봅니다.',
  },
  SALES_VIEWER: {
    label: '영업',
    note: '결과를 보기만 합니다. 진단은 돌리지 못합니다.',
  },
  CLIENT_VIEWER: {
    label: '업체 열람',
    note: '배정된 업체의 결과만 봅니다.',
  },
};

export function isRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLES as readonly string[]).includes(value);
}
