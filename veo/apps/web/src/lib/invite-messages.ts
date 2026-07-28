/**
 * Every sentence the invitation screen can show.
 *
 * `INVALID_TOKEN` covers unknown, expired, revoked and already-used links with one
 * message, because the API deliberately answers all four identically — telling them
 * apart would confirm that a particular link once existed. The wording therefore says
 * what to do next (ask for a new link) rather than guessing which of the four it was.
 */
export const INVITE_MESSAGES = {
  summary: '입력한 내용을 확인해 주세요.',
  passwordTooShort: '비밀번호는 12자 이상으로 정해 주세요.',
  confirmMismatch: '두 번 입력한 비밀번호가 서로 다릅니다.',
  INVALID_TOKEN:
    '이 초대 링크는 사용할 수 없습니다. 이미 사용했거나 기간이 지났을 수 있습니다. 관리자에게 새 링크를 요청해 주세요.',
  WEAK_PASSWORD: '비밀번호가 조건에 맞지 않습니다. 12자 이상으로 정해 주세요.',
  SERVER_ERROR: '지금은 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.',
  UNAVAILABLE: '서버에 연결할 수 없습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.',
  NOT_CONFIGURED: '서버가 아직 연결되지 않았습니다. 운영자에게 문의해 주세요.',
} as const;

/** Mirrors `MIN_MEMBER_PASSWORD_LENGTH` in the API. Checked by a contract test. */
export const MIN_INVITE_PASSWORD_LENGTH = 12;

const KNOWN = new Set<string>(['INVALID_TOKEN', 'WEAK_PASSWORD', 'SERVER_ERROR', 'UNAVAILABLE', 'NOT_CONFIGURED']);

/** A reason this build does not recognise reads as a server fault, never as a bad link. */
export function inviteMessageFor(reason: string): string {
  if (!KNOWN.has(reason)) return INVITE_MESSAGES.SERVER_ERROR;
  return INVITE_MESSAGES[reason as keyof typeof INVITE_MESSAGES] as string;
}
