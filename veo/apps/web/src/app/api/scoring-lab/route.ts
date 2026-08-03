import { NextResponse } from 'next/server';

import { actOnSpecVersion, type SpecAction } from '@/lib/scoring-lab';

/**
 * 채점 명세 수명주기 동작 — 브라우저와 엔진 사이.
 *
 * 화면에서 엔진을 직접 부르지 않는다. 세션 쿠키가 httpOnly 라 브라우저의 자바스크립트가
 * 읽을 수 없고, 그게 요점이다. 그래서 이 경로가 쿠키를 들고 대신 부른다.
 *
 * **권한은 여기서 흉내내지 않는다.** 발행은 `scoring_spec:publish`, 초안 수정은
 * `scoring_spec:author` 를 엔진이 확인한다. 여기서 다시 판단하면 두 벌이 되고, 두 벌은
 * 언젠가 서로 다르게 답한다 — 그날 화면은 되는데 엔진은 거절하거나, 더 나쁘게는 그 반대다.
 */

/** 서버가 허락하는 동작 이름. 여기 없는 값은 엔진까지 보내지 않는다. */
const ACTIONS: readonly SpecAction[] = [
  'submit',
  'approve',
  'send-back',
  'publish',
  'retire',
  'golden-run',
];

function isAction(value: unknown): value is SpecAction {
  return typeof value === 'string' && (ACTIONS as readonly string[]).includes(value);
}

export async function POST(request: Request) {
  const body: unknown = await request.json().catch(() => null);
  const input = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

  const versionId = typeof input['versionId'] === 'string' ? input['versionId'] : '';
  const action = input['action'];

  if (versionId === '') {
    return NextResponse.json({ message: '대상 버전을 찾지 못했습니다.' }, { status: 400 });
  }
  if (!isAction(action)) {
    // 모르는 동작을 엔진에 그대로 보내면 404 가 돌아온다. 그 전에 여기서 막아야
    // 사람이 읽을 수 있는 문장을 받는다.
    return NextResponse.json({ message: '알 수 없는 동작입니다.' }, { status: 400 });
  }

  const outcome = await actOnSpecVersion(versionId, action);
  if (outcome.ok) return NextResponse.json({ ok: true });

  const status = outcome.reason === 'SIGNED_OUT' ? 401 : 400;
  return NextResponse.json(
    { message: outcome.message ?? '처리하지 못했습니다.' },
    { status },
  );
}
