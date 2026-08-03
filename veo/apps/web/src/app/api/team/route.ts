import { NextResponse } from 'next/server';

import {
  changeRole,
  changeStatus,
  inviteMember,
  isRole,
  reinvite,
} from '@/lib/team';
import type { InviteWire } from '@/app/(console)/console/team/invite-wire';

/**
 * 팀원 관리 — 브라우저와 엔진 사이.
 *
 * 화면에서 엔진을 직접 부르지 않는다. 세션 쿠키가 httpOnly 라 브라우저의 자바스크립트가
 * 읽을 수 없고, 그게 요점이다 — 스크립트가 하나 끼어들어도 토큰을 가져가지 못한다.
 * 그래서 이 경로가 쿠키를 들고 대신 부른다.
 *
 * 권한은 여기서 흉내내지 않는다. 엔진이 `user:manage` 를 확인하고 없으면 거절하며,
 * 다른 조직 사람은 403 이 아니라 404 로 답한다 — 403 이면 그 사람이 존재한다는 사실을
 * 확인해 주는 셈이라, 한 번에 한 명씩 경쟁사 직원 명단을 캐낼 수 있다.
 */

function failure(outcome: { reason: string; message: string | null }) {
  const status = outcome.reason === 'SIGNED_OUT' ? 401 : 400;
  return NextResponse.json({ message: outcome.message ?? '처리하지 못했습니다.' }, { status });
}

export async function POST(request: Request) {
  const body: unknown = await request.json().catch(() => null);
  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

  // 재발송은 사람을 새로 만들지 않는다. 이미 있는 계정의 링크를 다시 낼 뿐이다.
  const userId = typeof input['userId'] === 'string' ? input['userId'] : '';
  if (userId !== '') {
    const outcome = await reinvite(userId);
    // 응답 모양을 타입으로 못 박는다 — 화면이 읽는 이름과 어긋나면 여기서 컴파일이 깨진다.
    return outcome.ok ? NextResponse.json<InviteWire>(outcome.data) : failure(outcome);
  }

  const email = typeof input['email'] === 'string' ? input['email'] : '';
  const displayName = typeof input['displayName'] === 'string' ? input['displayName'] : '';
  const role = input['role'];

  if (email.trim() === '' || displayName.trim() === '') {
    return NextResponse.json({ message: '이름과 이메일을 모두 넣어 주십시오.' }, { status: 400 });
  }
  if (!isRole(role)) {
    // 엔진이 모르는 역할을 보내면 422 가 돌아온다. 그 전에 여기서 막아야 사람이
    // 읽을 수 있는 문장을 받는다.
    return NextResponse.json({ message: '역할을 골라 주십시오.' }, { status: 400 });
  }

  const outcome = await inviteMember({ email, displayName, role });
  return outcome.ok ? NextResponse.json<InviteWire>(outcome.data) : failure(outcome);
}

export async function PATCH(request: Request) {
  const body: unknown = await request.json().catch(() => null);
  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

  const userId = typeof input['userId'] === 'string' ? input['userId'] : '';
  if (userId === '') {
    return NextResponse.json({ message: '대상을 찾지 못했습니다.' }, { status: 400 });
  }

  if (typeof input['isActive'] === 'boolean') {
    const outcome = await changeStatus(userId, input['isActive']);
    return outcome.ok ? NextResponse.json(outcome.data) : failure(outcome);
  }

  const role = input['role'];
  if (!isRole(role)) {
    return NextResponse.json({ message: '역할을 골라 주십시오.' }, { status: 400 });
  }

  const outcome = await changeRole(userId, role);
  return outcome.ok ? NextResponse.json(outcome.data) : failure(outcome);
}
