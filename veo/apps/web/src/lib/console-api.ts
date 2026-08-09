import 'server-only';

import { cookies } from 'next/headers';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';
import { CONSOLE_SESSION_COOKIE } from '@/lib/session-cookie';
import { record } from '@/lib/json';

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
  | {
      readonly ok: true;
      readonly data: T;
      readonly meta: Record<string, unknown>;
      /**
       * 목록 응답이 함께 준 쪽 정보 — 전체가 몇 건이고 지금 몇 건을 받았는가.
       *
       * 이 값을 버리던 동안 화면은 "받은 것이 전부" 라고 가정했고, 200건을 넘는 목록은
       * **경고도 없이 잘렸다**. 없는 응답(목록이 아닌 것)에서는 `undefined` 다.
       */
      readonly pageInfo?: Record<string, unknown>;
    }
  | {
      readonly ok: false;
      readonly reason: ConsoleFailure;
      /** 엔진이 사람에게 보여도 되는 문장을 준 경우에만 채워진다. */
      readonly message: string | null;
      readonly retryAfterSeconds: number | null;
    };

/**
 * 진단은 대상 사이트를 실제로 가져오므로 목록 조회와 시간 감각이 다르다.
 *
 * 240초인 이유: 크롤 상한이 200장이고, 느린 사이트 실측이 100장에 크롤 약 50초 +
 * 성능 측정 약 30초였다. 200장이면 최악 ~130초라 120초 제한으로는 느린 사이트의
 * 진단이 완주 직전에 끊긴다 — 서버는 일을 다 했는데 화면만 실패하는 형태라
 * 원인을 찾기 어렵다.
 */
const SCAN_TIMEOUT_MS = 240_000;
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


/**
 * 엔진이 준 한국어 오류 문장만 통과시킨다.
 *
 * 실패를 조용히 "오류가 발생했습니다"로 덮으면 원인을 아는 사람이 아무도 없게 된다.
 * 반대로 엔진 내부 메시지를 그대로 흘리면 내부 구조가 새어 나간다 — 그래서 계약이
 * `message` 로 명시한 값만 쓰고, 그 밖의 필드는 보지 않는다.
 */
function safeMessage(envelope: unknown): string | null {
  const error = record(record(envelope)['error']);
  const message = error['message'];
  return typeof message === 'string' && message !== '' ? message : null;
}

export async function callConsoleApi<T = unknown>(
  path: string,
  init: {
    method?: string;
    body?: unknown;
    timeoutMs?: number;
    /** 계약이 정한 헤더만. `Authorization` 은 여기서 덮을 수 없다 — 아래 순서를 볼 것. */
    headers?: Readonly<Record<string, string>>;
  } = {},
): Promise<ConsoleOutcome<T>> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return failed('NOT_CONFIGURED');
  }

  const token = (await cookies()).get(CONSOLE_SESSION_COOKIE)?.value ?? '';
  if (token === '') {
    return failed('SIGNED_OUT');
  }

  // 호출자 헤더를 먼저 깔고 우리 것으로 덮는다. 순서가 반대면 호출자가 `Authorization`
  // 을 갈아끼울 수 있고, 그러면 이 통로가 토큰을 지켜 주지 못한다.
  const headers: Record<string, string> = {
    ...(init.headers ?? {}),
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

  const body = record(envelope);
  const pageInfo = body['page_info'];
  return {
    ok: true,
    data: body['data'] as T,
    meta: record(body['meta']),
    ...(pageInfo === undefined || pageInfo === null
      ? {}
      : { pageInfo: record(pageInfo) }),
  };
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

/** 한 쪽에 담기는 최대치. 서버가 200 을 넘겨 주지 않는다(MAX_PAGE_SIZE). */
const PAGE_SIZE = 200;

/**
 * 목록을 **끝까지** 읽는다.
 *
 * 예전에는 `?page_size=200` 한 번만 부르고 그것을 전부라고 여겼다. 거래처가 200곳을
 * 넘는 날 목록은 **경고도 없이 잘리고**, 화면은 여전히 "전부" 라고 말한다. 지금 12곳이라
 * 당장 문제가 없다는 것이 이 결함의 위험한 점이다 — 넘는 날 아무도 모른다.
 *
 * 서버가 한 쪽에 200개까지만 주므로(더 큰 쪽은 서비스 거부의 지렛대다) 여러 번 부른다.
 * 총 개수는 서버가 `page_info.total_items` 로 알려 준다 — 화면이 세지 않는다.
 *
 * **끝을 못 찾으면 멈춘다.** 서버가 이상한 값을 주더라도 무한히 부르지 않는다. 그때는
 * 받은 만큼만 돌려주되, 그것이 전부인 척하지 않도록 `pageInfo` 를 함께 넘긴다.
 */
export async function readAllPages(
  path: string,
  {
    maxPages = 25,
    fetchPage = callConsoleApi,
  }: {
    maxPages?: number;
    /**
     * 한 쪽을 가져오는 방법. 시험이 여기를 바꾼다 — 모듈 안에서 곧바로 부르면 밖에서
     * 가로챌 수 없고, 그러면 이 함수의 규칙을 시험할 방법이 없다.
     */
    fetchPage?: (path: string) => Promise<ConsoleOutcome<unknown>>;
  } = {},
): Promise<ConsoleOutcome<unknown[]>> {
  const separator = path.includes('?') ? '&' : '?';
  const collected: unknown[] = [];
  let page = 1;
  let lastPageInfo: Record<string, unknown> | undefined;

  while (page <= maxPages) {
    const outcome = await fetchPage(`${path}${separator}page=${page}&page_size=${PAGE_SIZE}`);
    if (!outcome.ok) return outcome;

    const rows = Array.isArray(outcome.data) ? outcome.data : [];
    collected.push(...rows);
    lastPageInfo = outcome.pageInfo;

    const total = Number(lastPageInfo?.['total_items']);
    // 총계를 모르면 한 쪽이 덜 찬 것을 끝으로 본다 — 그 이상 물어볼 근거가 없다.
    const done = Number.isFinite(total) ? collected.length >= total : rows.length < PAGE_SIZE;
    if (done) break;
    page += 1;
  }

  return {
    ok: true,
    data: collected,
    meta: {},
    ...(lastPageInfo === undefined ? {} : { pageInfo: lastPageInfo }),
  };
}
