import 'server-only';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';

/**
 * 무료 네이버 키워드 조회 — 공개 화면이 측정 엔진에 말을 거는 유일한 통로.
 *
 * 엔진의 원칙을 화면까지 그대로 나른다: 값이 없는 것과 0 은 다른 사실이다.
 * 모든 숫자에는 품질(quality)이 붙어 오고, 제공자가 숨긴 값·최소 단위 미만·
 * 아예 못 받은 값을 각각 다르게 보여준다 — 빈 값을 0 으로 바꾸는 순간
 * "아무도 안 찾는 키워드"라는 거짓말이 된다.
 */

export type {
  KeywordFigure,
  KeywordLookupResult,
  KeywordValueQuality,
  PublicKeywordRow,
} from '@/lib/public-keywords-types';
import type {
  KeywordFigure,
  KeywordLookupResult,
  KeywordValueQuality,
  PublicKeywordRow,
} from '@/lib/public-keywords-types';

export type KeywordLookupFailureReason =
  | 'INVALID'
  | 'RATE_LIMITED'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED'
  | 'SERVER_ERROR';

export type KeywordLookupOutcome =
  | { readonly ok: true; readonly result: KeywordLookupResult }
  | {
      readonly ok: false;
      readonly reason: KeywordLookupFailureReason;
      /** 엔진이 준 한국어 사유 — 있으면 우리가 지어낸 일반 문구보다 우선한다. */
      readonly message: string | null;
      readonly retryAfterSeconds: number | null;
    };

/** 외부 제공자(네이버 검색광고)를 한 번 거치므로 로그인보다 여유 있게 기다린다. */
const LOOKUP_TIMEOUT_MS = 15_000;

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

const QUALITIES: readonly KeywordValueQuality[] = [
  'EXACT',
  'ROUNDED',
  'RANGE',
  'SUPPRESSED_BY_PROVIDER',
  'BELOW_PROVIDER_THRESHOLD',
  'MISSING',
];

/** 모르는 품질은 MISSING 으로 접는다 — 임의로 정확한 값 취급하지 않는다. */
function readQuality(value: unknown): KeywordValueQuality {
  return QUALITIES.includes(value as KeywordValueQuality)
    ? (value as KeywordValueQuality)
    : 'MISSING';
}

function figure(source: Record<string, unknown>, prefix: string): KeywordFigure {
  const raw = source[`monthly_${prefix}_searches`];
  return {
    value: typeof raw === 'number' && Number.isFinite(raw) ? raw : null,
    quality: readQuality(source[`monthly_${prefix}_quality`]),
  };
}

function toRow(value: unknown): PublicKeywordRow | null {
  const source = asRecord(value);
  if (source === null || typeof source['keyword'] !== 'string') {
    return null;
  }
  return {
    keyword: source['keyword'],
    normalizedKeyword:
      typeof source['normalized_keyword'] === 'string'
        ? source['normalized_keyword']
        : source['keyword'],
    total: figure(source, 'total'),
    pc: figure(source, 'pc'),
    mobile: figure(source, 'mobile'),
    competitionLabel:
      typeof source['competition_label'] === 'string' ? source['competition_label'] : null,
  };
}

function toResult(data: Record<string, unknown>): KeywordLookupResult | null {
  if (typeof data['searchad_state'] !== 'string') {
    return null;
  }
  const rows = Array.isArray(data['keywords'])
    ? data['keywords'].map(toRow).filter((row): row is PublicKeywordRow => row !== null)
    : [];
  const notices = Array.isArray(data['notices_ko'])
    ? data['notices_ko'].filter((item): item is string => typeof item === 'string')
    : [];
  return {
    searchadState: data['searchad_state'],
    rows,
    noticesKo: notices,
    scopeNoticeKo:
      typeof data['scope_notice_ko'] === 'string' ? data['scope_notice_ko'] : '',
  };
}

function classify(status: number): KeywordLookupFailureReason {
  if (status === 400 || status === 422) {
    return 'INVALID';
  }
  if (status === 429) {
    return 'RATE_LIMITED';
  }
  if (status === 503) {
    return 'UNAVAILABLE';
  }
  return 'SERVER_ERROR';
}

function failed(
  reason: KeywordLookupFailureReason,
  message: string | null = null,
  retryAfterSeconds: number | null = null,
): KeywordLookupOutcome {
  return { ok: false, reason, message, retryAfterSeconds };
}

function retryAfterFrom(response: Response): number | null {
  const header = response.headers.get('retry-after');
  if (header === null) {
    return null;
  }
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

export async function lookupPublicKeywords(
  keywords: readonly string[],
  fetchImpl: typeof fetch = fetch,
): Promise<KeywordLookupOutcome> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return failed('NOT_CONFIGURED');
  }

  let response: Response;
  try {
    response = await fetchImpl(`${baseUrl}/public/v1/keyword-lookups`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ keywords }),
      cache: 'no-store',
      signal: AbortSignal.timeout(LOOKUP_TIMEOUT_MS),
    });
  } catch {
    return failed('UNAVAILABLE');
  }

  let envelope: unknown;
  try {
    envelope = await response.json();
  } catch {
    return response.ok
      ? failed('SERVER_ERROR')
      : failed(classify(response.status), null, retryAfterFrom(response));
  }

  const body = asRecord(envelope);
  if (!response.ok) {
    // 엔진의 거절에는 사람이 읽을 사유가 실려 있다 ("최대 5개까지" 등) — 버리지 않는다.
    const error = body === null ? null : asRecord(body['error']);
    const message =
      error !== null && typeof error['message'] === 'string' ? error['message'] : null;
    return failed(classify(response.status), message, retryAfterFrom(response));
  }

  const data = body === null ? null : asRecord(body['data']);
  if (data === null) {
    return failed('SERVER_ERROR');
  }
  const result = toResult(data);
  return result === null ? failed('SERVER_ERROR') : { ok: true, result };
}
