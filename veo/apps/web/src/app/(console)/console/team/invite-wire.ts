/**
 * 초대 링크 응답의 모양 — 브라우저와 `/api/team` 이 함께 쓰는 **단 하나의** 정의.
 *
 * 이 파일이 없던 동안, 경로는 `inviteUrl` 을 돌려주는데 화면은 `invite_url` 을 읽었다.
 * 양쪽 다 타입 없이 `as` 로 단언해서 컴파일 오류도 나지 않았고, 값이 `undefined` 가 되면
 * 화면이 그것을 빈 문자열로 접었다. 결과는 **발급은 성공하고 링크 칸만 비는** 실패였다 —
 * 성공 문구와 복사 버튼까지 정상으로 보여서, 무엇이 틀렸는지 알 수 없는 종류였다.
 *
 * 그래서 이름을 여기 한 번만 적는다. `route.ts` 는 이 타입으로 응답을 못 박고, 화면은
 * `readInvite` 로만 읽는다. 엔진 쪽 이름이 바뀌면 경로에서 컴파일이 깨지지, 화면이
 * 조용히 비지 않는다.
 *
 * server-only 를 붙이지 않는다 — 브라우저에서 도는 화면이 함께 쓰는 파일이다.
 */

export interface InviteWire {
  readonly inviteUrl: string;
  readonly expiresAt: string;
}

/**
 * 응답 본문에서 초대 링크를 꺼낸다.
 *
 * 없는 값은 빈 문자열이 된다. 화면은 빈 링크를 그리지 않고 "받지 못했다" 고 말해야
 * 하므로, 판단은 부르는 쪽에 맡긴다.
 */
export function readInvite(body: unknown): InviteWire {
  const source =
    typeof body === 'object' && body !== null && !Array.isArray(body)
      ? (body as Record<string, unknown>)
      : {};
  const text = (key: keyof InviteWire): string =>
    typeof source[key] === 'string' ? (source[key] as string) : '';

  return { inviteUrl: text('inviteUrl'), expiresAt: text('expiresAt') };
}
