import 'server-only';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';

/**
 * 무료 진단 상담 요청 — 공개 화면이 접수 창구에 말을 거는 통로.
 *
 * 접수 창구는 처음부터 서버에 서 있었는데(`POST /public/v1/leads`) 화면에서 부르는
 * 곳이 없었다. 그래서 무료 진단을 받고 결과를 본 사람이 **"상담 받겠다" 를 누를 자리가
 * 없었다.**
 *
 * 받는 것은 회신에 필요한 최소한이다 — 이름과 연락처 하나, 선택으로 홈페이지 주소.
 * 그 외는 서버 스키마가 거부한다. **광고 수신 동의는 받지도 저장하지도 않는다.**
 * 무엇을 저장했는지는 서버가 한국어로 되돌려 주고, 화면은 그것을 그대로 보인다 —
 * 우리가 "이런 걸 저장했습니다" 라고 따로 적으면 실제 저장한 것과 갈라진다.
 */

export type LeadFailureReason =
  | 'INVALID'
  | 'RATE_LIMITED'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED'
  | 'SERVER_ERROR';

/** 접수 확인 — **서버가 실제로 적어 둔 것**만 들어 있다. */
export interface LeadReceipt {
  readonly leadId: string;
  readonly receivedAt: string;
  /** 저장한 항목을 한국어로. 화면은 이 목록을 그대로 보인다. */
  readonly storedFieldsKo: readonly string[];
  readonly retentionNoteKo: string;
  readonly consentNoteKo: string;
}

export type LeadOutcome =
  | { readonly ok: true; readonly receipt: LeadReceipt }
  | {
      readonly ok: false;
      readonly reason: LeadFailureReason;
      /** 엔진이 준 한국어 사유 — 있으면 우리가 지어낸 일반 문구보다 우선한다. */
      readonly message: string | null;
      readonly retryAfterSeconds: number | null;
    };

const SUBMIT_TIMEOUT_MS = 10_000;

export interface LeadInput {
  readonly name: string;
  readonly phone: string | null;
  readonly email: string | null;
  readonly siteUrl: string | null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function classify(status: number): LeadFailureReason {
  if (status === 422 || status === 400) return 'INVALID';
  if (status === 429) return 'RATE_LIMITED';
  if (status >= 500) return 'SERVER_ERROR';
  return 'SERVER_ERROR';
}

function retryAfterFrom(response: Response): number | null {
  const header = response.headers.get('retry-after');
  if (header === null) return null;
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

function failed(
  reason: LeadFailureReason,
  message: string | null = null,
  retryAfterSeconds: number | null = null,
): LeadOutcome {
  return { ok: false, reason, message, retryAfterSeconds };
}

function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}

export async function submitPublicLead(
  input: LeadInput,
  fetchImpl: typeof fetch = fetch,
): Promise<LeadOutcome> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return failed('NOT_CONFIGURED');
  }

  // 비어 있는 항목은 **보내지 않는다.** 빈 문자열을 보내면 서버가 "형식이 틀렸다" 로
  // 거절하는데, 실제로는 사람이 안 적은 것뿐이다.
  const body: Record<string, string> = { name: input.name };
  if (input.phone !== null && input.phone !== '') body['phone'] = input.phone;
  if (input.email !== null && input.email !== '') body['email'] = input.email;
  if (input.siteUrl !== null && input.siteUrl !== '') body['site_url'] = input.siteUrl;

  let response: Response;
  try {
    response = await fetchImpl(`${baseUrl}/public/v1/leads`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(SUBMIT_TIMEOUT_MS),
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

  const record = asRecord(envelope);
  if (!response.ok || record === null) {
    const error = asRecord(record?.['error']);
    const message = typeof error?.['message'] === 'string' ? error['message'] : null;
    return failed(classify(response.status), message, retryAfterFrom(response));
  }

  const data = asRecord(record['data']);
  if (data === null) return failed('SERVER_ERROR');

  const stored = data['stored_fields_ko'];
  return {
    ok: true,
    receipt: {
      leadId: text(data, 'lead_id'),
      receivedAt: text(data, 'received_at'),
      storedFieldsKo: Array.isArray(stored)
        ? stored.filter((one): one is string => typeof one === 'string')
        : [],
      retentionNoteKo: text(data, 'retention_note_ko'),
      consentNoteKo: text(data, 'consent_note_ko'),
    },
  };
}
