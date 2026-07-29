import 'server-only';

import { cookies } from 'next/headers';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';
import { CONSOLE_SESSION_COOKIE } from '@/lib/session-cookie';

/**
 * 콘솔이 로그인한 상태로 엔진에 말을 거는 통로.
 *
 * 접근 토큰은 httpOnly 쿠키에 있고 브라우저 자바스크립트는 읽지 못한다. 그래서 호출은
 * 전부 서버에서 일어난다 — 화면이 토큰을 들고 다니기 시작하면 XSS 하나로 조직 전체가
 * 열린다.
 */

export type ConsoleFailure =
  | 'SIGNED_OUT'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'INVALID'
  | 'RATE_LIMITED'
  | 'UNREACHABLE'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED'
  | 'SERVER_ERROR';

export type ConsoleOutcome<T> =
  | { readonly ok: true; readonly data: T; readonly meta: Record<string, unknown> }
  | {
      readonly ok: false;
      readonly reason: ConsoleFailure;
      /** 엔진이 사람에게 보여도 되는 문장을 준 경우에만 채워진다. */
      readonly message: string | null;
      readonly retryAfterSeconds: number | null;
    };

/** 진단은 대상 사이트를 실제로 가져오므로 목록 조회와 시간 감각이 다르다. */
const SCAN_TIMEOUT_MS = 120_000;
const DEFAULT_TIMEOUT_MS = 15_000;

function classify(status: number): ConsoleFailure {
  if (status === 401) return 'SIGNED_OUT';
  if (status === 403) return 'FORBIDDEN';
  if (status === 404) return 'NOT_FOUND';
  if (status === 409) return 'CONFLICT';
  if (status === 400 || status === 422) return 'INVALID';
  if (status === 429) return 'RATE_LIMITED';
  if (status === 502 || status === 504) return 'UNREACHABLE';
  if (status === 503) return 'UNAVAILABLE';
  return 'SERVER_ERROR';
}

function failed<T>(
  reason: ConsoleFailure,
  message: string | null = null,
  retryAfterSeconds: number | null = null,
): ConsoleOutcome<T> {
  return { ok: false, reason, message, retryAfterSeconds };
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/**
 * 엔진이 준 한국어 오류 문장만 통과시킨다.
 *
 * 실패를 조용히 "오류가 발생했습니다"로 덮으면 원인을 아는 사람이 아무도 없게 된다.
 * 반대로 엔진 내부 메시지를 그대로 흘리면 내부 구조가 새어 나간다 — 그래서 계약이
 * `message` 로 명시한 값만 쓰고, 그 밖의 필드는 보지 않는다.
 */
function safeMessage(envelope: unknown): string | null {
  const error = asRecord(asRecord(envelope)['error']);
  const message = error['message'];
  return typeof message === 'string' && message !== '' ? message : null;
}

export async function callConsoleApi<T = unknown>(
  path: string,
  init: { method?: string; body?: unknown; timeoutMs?: number } = {},
): Promise<ConsoleOutcome<T>> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return failed('NOT_CONFIGURED');
  }

  const token = (await cookies()).get(CONSOLE_SESSION_COOKIE)?.value ?? '';
  if (token === '') {
    return failed('SIGNED_OUT');
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${token}`,
  };
  if (init.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: init.method ?? 'GET',
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: 'no-store',
      signal: AbortSignal.timeout(init.timeoutMs ?? DEFAULT_TIMEOUT_MS),
    });
  } catch {
    return failed('UNAVAILABLE');
  }

  let envelope: unknown = null;
  try {
    envelope = await response.json();
  } catch {
    // 본문이 없는 성공(204)은 정상이다. 실패인데 본문이 없으면 상태 코드만 남는다.
    if (response.ok) {
      return { ok: true, data: null as T, meta: {} };
    }
    return failed(classify(response.status));
  }

  if (!response.ok) {
    const retryAfter = Number.parseInt(response.headers.get('retry-after') ?? '', 10);
    return failed(
      classify(response.status),
      safeMessage(envelope),
      Number.isFinite(retryAfter) ? retryAfter : null,
    );
  }

  const body = asRecord(envelope);
  return { ok: true, data: body['data'] as T, meta: asRecord(body['meta']) };
}

/** 진단 실행. 목록 조회보다 훨씬 오래 걸리므로 제한 시간을 따로 준다. */
export async function runConsoleScan(
  targetUrl: string,
  urls: readonly string[] = [],
): Promise<ConsoleOutcome<unknown>> {
  return callConsoleApi('/api/seo/scans', {
    method: 'POST',
    body: { target_url: targetUrl, urls },
    timeoutMs: SCAN_TIMEOUT_MS,
  });
}
