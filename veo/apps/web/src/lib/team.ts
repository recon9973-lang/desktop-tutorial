import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';
// 역할 상수는 화면(브라우저)과 함께 쓰므로 server-only 가 아닌 자리에 둔다.
import type { Role } from '@/app/(console)/console/team/roles';
import { record, textOrNull } from '@/lib/json';

export { ROLES, ROLE_LABELS, isRole } from '@/app/(console)/console/team/roles';
export type { Role } from '@/app/(console)/console/team/roles';

/**
 * 한 조직의 사람들.
 *
 * 엔진에는 이미 전부 있다 — 초대·역할 변경·계정 비활성·초대 재발송. 없던 것은 화면뿐이라
 * 여기서 하는 일은 **이름만 우리 쪽 표기로 옮기는 것**이고, 아무것도 계산하지 않는다.
 *
 * 경로에 `/api` 를 반드시 붙인다. `callConsoleApi` 는 받은 경로를 엔진 주소 뒤에
 * 그대로 잇기만 하므로, 빠뜨리면 엔진의 404 가 화면에 "Not Found" 로 뜬다 — 화면은
 * 정상으로 보이고 목록만 비어, 무엇이 틀렸는지 알기 어려운 실패다.
 *
 * 초대 메일은 보내지 않는다. 엔진이 1회용 링크를 돌려주고, 관리자가 그것을 복사해
 * 카톡이든 메일이든 쓰던 방법으로 전달한다. 직원 몇 명을 들이는 데 메일 발송 인프라를
 * 세울 이유가 적고, 필요해지면 그때 이 자리에 붙이면 된다.
 */

export interface Member {
  readonly id: string;
  readonly displayName: string;
  readonly email: string;
  readonly roles: readonly string[];
  readonly isActive: boolean;
  /** 비밀번호를 아직 안 정한 사람 — 초대는 갔는데 수락하지 않은 상태다. */
  readonly hasPassword: boolean;
  readonly lastLoginAt: string | null;
}

/** 초대 링크. 1회용이고 만료가 있다. */
export interface Invitation {
  readonly inviteUrl: string;
  readonly expiresAt: string;
}


/**
 * 목록 응답의 본문.
 *
 * `callConsoleApi` 가 이미 `data` 를 벗겨 주므로 여기 들어오는 값이 곧 배열이다.
 * 한때 다른 화면에서 `data.items` 를 찾다가 **모든 목록이 조용히 비었던** 적이 있다 —
 * 등록은 성공하는데 화면에는 아무것도 안 나오는, 원인을 찾기 어려운 실패였다.
 */
function rows(data: unknown): readonly Record<string, unknown>[] {
  return Array.isArray(data) ? data.map(record) : [];
}

function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}


function toMember(source: Record<string, unknown>): Member {
  return {
    id: text(source, 'id'),
    displayName: text(source, 'display_name'),
    email: text(source, 'email'),
    roles: Array.isArray(source['roles'])
      ? source['roles'].filter((r): r is string => typeof r === 'string')
      : [],
    // 없는 값을 활성으로 접지 않는다. 비활성 계정을 활성으로 보여주면 위험한 쪽으로 틀린다.
    isActive: source['is_active'] === true,
    hasPassword: source['has_password'] === true,
    lastLoginAt: textOrNull(source, 'last_login_at'),
  };
}

function toInvitation(source: Record<string, unknown>): Invitation {
  return {
    inviteUrl: text(source, 'invite_url'),
    expiresAt: text(source, 'expires_at'),
  };
}


export async function listMembers(): Promise<ConsoleOutcome<readonly Member[]>> {
  const outcome = await callConsoleApi<unknown>('/api/users');
  if (!outcome.ok) return outcome;
  return { ...outcome, data: rows(outcome.data).map(toMember) };
}

export async function inviteMember(input: {
  readonly email: string;
  readonly displayName: string;
  readonly role: Role;
}): Promise<ConsoleOutcome<Invitation>> {
  const outcome = await callConsoleApi<unknown>('/api/users', {
    method: 'POST',
    body: {
      email: input.email.trim(),
      display_name: input.displayName.trim(),
      role: input.role,
    },
  });
  if (!outcome.ok) return outcome;
  // 응답은 `{ member, invitation }` 이다. 화면이 당장 필요한 것은 링크뿐이다.
  return { ...outcome, data: toInvitation(record(record(outcome.data)['invitation'])) };
}

export async function reinvite(userId: string): Promise<ConsoleOutcome<Invitation>> {
  const outcome = await callConsoleApi<unknown>(`/api/users/${userId}/invitations`, {
    method: 'POST',
  });
  if (!outcome.ok) return outcome;
  return { ...outcome, data: toInvitation(record(outcome.data)) };
}

export async function changeRole(
  userId: string,
  role: Role,
): Promise<ConsoleOutcome<Member>> {
  const outcome = await callConsoleApi<unknown>(`/api/users/${userId}/role`, {
    method: 'PATCH',
    body: { role },
  });
  if (!outcome.ok) return outcome;
  return { ...outcome, data: toMember(record(outcome.data)) };
}

export async function changeStatus(
  userId: string,
  isActive: boolean,
): Promise<ConsoleOutcome<Member>> {
  const outcome = await callConsoleApi<unknown>(`/api/users/${userId}/status`, {
    method: 'PATCH',
    body: { is_active: isActive },
  });
  if (!outcome.ok) return outcome;
  return { ...outcome, data: toMember(record(outcome.data)) };
}
