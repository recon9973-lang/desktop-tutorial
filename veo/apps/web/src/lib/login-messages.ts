/**
 * Every sentence the login form can show.
 *
 * `INVALID_CREDENTIALS` is one message for every rejected sign-in — unknown
 * account, wrong password, disabled account. The API refuses to say which, and
 * this form must not become the account-enumeration oracle the API avoided being.
 * Lockout and outage get their own wording because the user's next action really
 * is different: wait, or tell an operator.
 */
export const LOGIN_MESSAGES = {
  INVALID_CREDENTIALS: '이메일 또는 비밀번호가 올바르지 않습니다.',
  LOCKED_OUT: '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.',
  SERVER_ERROR: '지금은 로그인을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.',
  UNAVAILABLE: '인증 서버에 연결할 수 없습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.',
  NOT_CONFIGURED: '인증 서버가 아직 연결되지 않아 로그인할 수 없습니다. 운영자에게 문의해 주세요.',
} as const;

export type LoginMessageKey = keyof typeof LOGIN_MESSAGES;

/**
 * Client-side field checks. These say what to fix, never whether an account exists.
 *
 * `summary` heads the error summary the form focuses after a failed submit; the
 * individual messages are repeated inside it, so a screen-reader user hears
 * every problem at once instead of one per attempt.
 */
export const FIELD_MESSAGES = {
  summary: '입력한 내용을 확인해 주세요.',
  emailRequired: '이메일을 입력해 주세요.',
  emailFormat: '이메일 형식이 올바르지 않습니다.',
  passwordRequired: '비밀번호를 입력해 주세요.',
} as const;

const KNOWN_KEYS = new Set<string>(Object.keys(LOGIN_MESSAGES));

/**
 * Turns a reason from the session route handler into a sentence.
 *
 * A reason this build does not recognise reads as a server fault: better to
 * under-explain than to invent a cause.
 */
export function loginMessageFor(reason: unknown): string {
  if (typeof reason === 'string' && KNOWN_KEYS.has(reason)) {
    return LOGIN_MESSAGES[reason as LoginMessageKey];
  }
  return LOGIN_MESSAGES.SERVER_ERROR;
}

/** A pragmatic shape check — the real verdict on an address is the API's. */
export function looksLikeEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
