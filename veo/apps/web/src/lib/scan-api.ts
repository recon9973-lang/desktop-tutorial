import 'server-only';

import { resolveAuthApiBaseUrl } from '@/lib/auth-api';

/**
 * 진단 실행 — 콘솔이 측정 엔진에 말을 거는 유일한 통로.
 *
 * 화면은 이 모듈이 돌려주는 타입만 안다. 엔진 응답이 바뀌면 여기서 흡수하고, 화면은
 * 그대로 둔다. 반대로 하면 응답 필드 이름이 JSX 안에 흩어져서 바꿀 수가 없어진다.
 *
 * 값을 지어내지 않는다. 엔진이 "측정하지 못했다"고 하면 화면도 그렇게 말한다 —
 * 빈 값을 0점으로 바꾸는 순간, 사이트가 나쁜 것인지 우리가 못 잰 것인지 구분이 사라진다.
 */

/** 한 항목의 판정. 엔진의 `status` 와 같은 어휘를 쓴다. */
export type ScanVerdict = 'PASS' | 'WARNING' | 'FAIL' | 'NOT_APPLICABLE' | 'UNKNOWN';

export type ScanKind = 'SEO' | 'GEO';

export interface ScanFinding {
  readonly checkId: string;
  readonly title: string;
  readonly categoryId: string;
  readonly categoryName: string;
  readonly severity: string;
  /** 누가 고치는 항목인가 — 개발자 몫과 마케터 몫을 섞으면 아무도 안 고친다. */
  readonly owner: string;
  readonly verdict: ScanVerdict;
}

export interface ScanScore {
  readonly specId: string;
  readonly specVersion: string;
  readonly specChecksum: string;
  /** 채점되지 않았으면 `null`. 0 이 아니다. */
  readonly value: number | null;
  readonly bandLabel: string | null;
  readonly coverage: number;
  readonly confidence: number;
  readonly meaning: string;
}

export interface ScanResult {
  readonly kind: ScanKind;
  readonly targetUrl: string;
  readonly summary: string;
  readonly scopeNotice: string;
  readonly score: ScanScore;
  readonly findings: readonly ScanFinding[];
  readonly findingCount: number;
  /** 판정에 필요한 근거를 못 모은 항목 수. 감점이 아니라 측정 범위에 반영된다. */
  readonly unmeasuredCount: number;
  /** 결과 공유 링크의 토큰. 만료된다. */
  readonly resultToken: string;
  readonly resultExpiresAt: string;
}

export type ScanFailureReason =
  | 'INVALID_URL'
  | 'RATE_LIMITED'
  | 'UNREACHABLE'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED'
  | 'SERVER_ERROR';

export type ScanOutcome =
  | { readonly ok: true; readonly result: ScanResult }
  | {
      readonly ok: false;
      readonly reason: ScanFailureReason;
      readonly retryAfterSeconds: number | null;
    };

const ENDPOINTS: Record<ScanKind, string> = {
  SEO: '/public/v1/seo-scans',
  GEO: '/public/v1/geo-readiness-scans',
};

/** 진단은 외부 사이트를 실제로 가져오므로 로그인보다 훨씬 오래 걸린다. */
const SCAN_TIMEOUT_MS = 60_000;

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function readString(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}

function readNumber(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

const VERDICTS: readonly ScanVerdict[] = [
  'PASS',
  'WARNING',
  'FAIL',
  'NOT_APPLICABLE',
  'UNKNOWN',
];

/** 모르는 판정은 UNKNOWN 으로 접는다 — 임의로 통과시키지 않는다. */
function readVerdict(value: unknown): ScanVerdict {
  return VERDICTS.includes(value as ScanVerdict) ? (value as ScanVerdict) : 'UNKNOWN';
}

function toFinding(raw: unknown): ScanFinding | null {
  const source = asRecord(raw);
  if (source === null) {
    return null;
  }
  const checkId = readString(source, 'check_id');
  if (checkId === '') {
    return null;
  }
  return {
    checkId,
    title: readString(source, 'title_ko'),
    categoryId: readString(source, 'category_id'),
    categoryName: readString(source, 'category_name_ko'),
    severity: readString(source, 'severity'),
    owner: readString(source, 'remediation_owner'),
    verdict: readVerdict(source['status']),
  };
}

function toScore(raw: Record<string, unknown>): ScanScore {
  return {
    specId: readString(raw, 'spec_id'),
    specVersion: readString(raw, 'spec_version'),
    specChecksum: readString(raw, 'spec_checksum'),
    // status 가 SCORED 가 아니면 점수는 없다. 0 으로 채우면 "0점"으로 읽힌다.
    value: readString(raw, 'status') === 'SCORED' ? readNumber(raw, 'score') : null,
    bandLabel: readString(raw, 'band_label_ko') || null,
    coverage: readNumber(raw, 'coverage') ?? 0,
    confidence: readNumber(raw, 'confidence') ?? 0,
    meaning: readString(raw, 'meaning_ko'),
  };
}

function toResult(raw: Record<string, unknown>, kind: ScanKind): ScanResult | null {
  const score = asRecord(raw['score']);
  if (score === null) {
    return null;
  }
  const findings = Array.isArray(raw['top_findings'])
    ? raw['top_findings'].map(toFinding).filter((item): item is ScanFinding => item !== null)
    : [];

  return {
    kind,
    targetUrl: readString(raw, 'target_url'),
    summary: readString(raw, 'summary_ko'),
    scopeNotice: readString(raw, 'scope_notice_ko'),
    score: toScore(score),
    findings,
    findingCount: readNumber(raw, 'total_finding_count') ?? findings.length,
    unmeasuredCount: readNumber(raw, 'unmeasured_check_count') ?? 0,
    resultToken: readString(raw, 'result_token'),
    resultExpiresAt: readString(raw, 'result_expires_at'),
  };
}

function failed(
  reason: ScanFailureReason,
  retryAfterSeconds: number | null = null,
): ScanOutcome {
  return { ok: false, reason, retryAfterSeconds };
}

function classify(status: number): ScanFailureReason {
  if (status === 422 || status === 400) {
    return 'INVALID_URL';
  }
  if (status === 429) {
    return 'RATE_LIMITED';
  }
  if (status === 502 || status === 504) {
    return 'UNREACHABLE';
  }
  if (status === 503) {
    return 'UNAVAILABLE';
  }
  return 'SERVER_ERROR';
}

function retryAfterFrom(response: Response): number | null {
  const header = response.headers.get('retry-after');
  if (header === null) {
    return null;
  }
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

export async function runScan(
  kind: ScanKind,
  url: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ScanOutcome> {
  const baseUrl = resolveAuthApiBaseUrl();
  if (baseUrl === null) {
    return failed('NOT_CONFIGURED');
  }

  let response: Response;
  try {
    response = await fetchImpl(`${baseUrl}${ENDPOINTS[kind]}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ urls: [url] }),
      cache: 'no-store',
      signal: AbortSignal.timeout(SCAN_TIMEOUT_MS),
    });
  } catch {
    // 엔진에 닿지도 못한 경우와, 엔진이 대상 사이트에 닿지 못한 경우는 다르다.
    // 여기는 앞쪽 — 사용자가 할 수 있는 일이 없으므로 그렇게 말해야 한다.
    return failed('UNAVAILABLE');
  }

  if (!response.ok) {
    return failed(classify(response.status), retryAfterFrom(response));
  }

  let envelope: unknown;
  try {
    envelope = await response.json();
  } catch {
    return failed('SERVER_ERROR');
  }

  const body = asRecord(envelope);
  const data = body === null ? null : asRecord(body['data']);
  if (data === null) {
    return failed('SERVER_ERROR');
  }

  const result = toResult(data, kind);
  return result === null ? failed('SERVER_ERROR') : { ok: true, result };
}
