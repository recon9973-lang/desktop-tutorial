import { NextResponse } from 'next/server';

/**
 * 콘솔 프록시 라우트가 거절을 돌려주는 **한 가지 모양**.
 *
 * ## 무엇을 합쳤고 무엇을 안 합쳤나
 *
 * [실측 2026-08-09] 프록시 라우트를 전수로 재 봤다 —
 *
 * ```
 * refuse()    서로 다른 판 1종 / 14벌   → 합친다
 * NO_STORE    3종 / 23벌 (17 + 5 + 1)  → 17벌짜리만 합친다
 * STATUS      5종 / 17벌 (11 + 2+2+1+1) → 11벌짜리만 합친다
 * MESSAGES    라우트마다 다르다          → 합치지 않는다
 * ```
 *
 * **`MESSAGES` 는 일부러 남긴다.** 같은 `FORBIDDEN` 이라도 브랜드 화면은 "브랜드를
 * 등록할 권한이 없습니다", 리포트 화면은 "리포트를 발행할 권한이 없습니다" 라고 해야
 * 한다. 하나로 합치면 전부 "권한이 없습니다" 가 되고, 그것은 사람이 다음에 무엇을 할지
 * 모르게 만든다.
 *
 * **`STATUS` 도 다섯 종을 하나로 누르지 않았다.** 공개 라우트와 콘솔 라우트가 같은
 * 낱말에 다른 코드를 쓰는 자리가 있다. 다섯을 하나로 만들면 그 차이가 조용히
 * 사라지는데, 상태 코드는 **바깥이 보는 계약**이라 조용히 바뀌면 안 된다. 여기 있는
 * 것은 열한 벌이 똑같았던 콘솔용 하나뿐이고, 나머지 넷은 각자 자리에 남았다.
 */

/** 응답을 캐시에 남기지 않는다. 로그인 상태에 따라 내용이 달라지는 자리다. */
export const NO_STORE = { 'Cache-Control': 'no-store, private' } as const;

/**
 * 콘솔 프록시가 쓰는 사유 → HTTP 코드.
 *
 * 열한 라우트가 글자 하나까지 같은 표를 들고 있었다. 공개 라우트는 다른 표를 쓰므로
 * 여기 없다 — 가져다 쓰기 전에 그 라우트의 표와 같은지 보고 쓴다.
 */
export const CONSOLE_STATUS: Record<string, number> = {
  SIGNED_OUT: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  INVALID: 422,
  RATE_LIMITED: 429,
  UNREACHABLE: 502,
  UNAVAILABLE: 503,
  NOT_CONFIGURED: 503,
};

/**
 * 거절 응답 하나.
 *
 * `messages` 는 **부르는 라우트가 준다** — 그 화면의 말투다. 사유를 모르면
 * `SERVER_ERROR` 문구로 떨어지고, 그것도 없으면 문구 없이 나간다. 모르는 사유에
 * 그럴듯한 설명을 지어 붙이지 않는다.
 */
export function refuse(
  reason: string,
  message: string | null | undefined,
  messages: Record<string, string>,
  status: Record<string, number> = CONSOLE_STATUS,
): NextResponse {
  return NextResponse.json(
    { ok: false, reason, message: message ?? messages[reason] ?? messages['SERVER_ERROR'] },
    { status: status[reason] ?? 500, headers: NO_STORE },
  );
}
