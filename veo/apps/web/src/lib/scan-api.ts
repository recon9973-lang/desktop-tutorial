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

export type {
  ScanVerdict,
  ScanKind,
  ScanFinding,
  ScanScore,
  ScanStage,
  ScanCheckRow,
  ScanCounts,
  ScanPreviews,
  ScanResult,
  ScanFailureReason,
  ScanOutcome,
} from '@/lib/scan-api-types';
import type {
  ScanVerdict,
  ScanKind,
  ScanFinding,
  ScanScore,
  ScanStage,
  ScanCheckRow,
  ScanCounts,
  ScanPreviews,
  ScanResult,
  ScanFailureReason,
  ScanOutcome,
} from '@/lib/scan-api-types';

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

function toStage(raw: unknown): ScanStage | null {
  const source = asRecord(raw);
  if (source === null) {
    return null;
  }
  return {
    categoryId: readString(source, 'category_id'),
    name: readString(source, 'name_ko'),
    score: readNumber(source, 'score'),
    weight: readNumber(source, 'weight') ?? 0,
    isGate: source['is_gate'] === true,
  };
}

function toCheckRow(raw: unknown): ScanCheckRow | null {
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
    note: readString(source, 'note_ko') || null,
    gainPoints: readNumber(source, 'gain_points'),
    blockedByCap: source['blocked_by_cap'] === true,
    outsideScore: source['outside_score'] === true,
    codeExample: readString(source, 'code_example') || null,
  };
}

function toCounts(raw: unknown): ScanCounts {
  const source = asRecord(raw) ?? {};
  return {
    failed: readNumber(source, 'failed') ?? 0,
    warned: readNumber(source, 'warned') ?? 0,
    passed: readNumber(source, 'passed') ?? 0,
    unknown: readNumber(source, 'unknown') ?? 0,
    notApplicable: readNumber(source, 'not_applicable') ?? 0,
  };
}

function toPreviews(raw: unknown): ScanPreviews | null {
  const source = asRecord(raw);
  if (source === null) {
    return null;
  }
  return {
    serpTitle: readString(source, 'serp_title') || null,
    serpDescription: readString(source, 'serp_description') || null,
    ogTitle: readString(source, 'og_title') || null,
    ogDescription: readString(source, 'og_description') || null,
    hasOgImage: source['has_og_image'] === true,
  };
}

function toExposure(raw: unknown): ScanResult['exposure'] {
  const source = asRecord(raw);
  if (source === null) {
    return null;
  }
  return {
    isBlocked: source['is_blocked'] === true,
    labels: Array.isArray(source['labels_ko'])
      ? source['labels_ko'].filter((item): item is string => typeof item === 'string')
      : [],
  };
}

function toResult(raw: Record<string, unknown>, kind: ScanKind): ScanResult | null {
  // SEO 는 score, GEO 는 readiness — 준비도와 노출 차단을 합치지 않는다는 서버
  // 설계가 키 이름에 그대로 있다.
  const score = asRecord(raw['score']) ?? asRecord(raw['readiness']);
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
    reach: readNumber(raw, 'reach') ?? 1,
    stages: Array.isArray(raw['stages'])
      ? raw['stages'].map(toStage).filter((item): item is ScanStage => item !== null)
      : [],
    checks: Array.isArray(raw['checks'])
      ? raw['checks'].map(toCheckRow).filter((item): item is ScanCheckRow => item !== null)
      : [],
    counts: toCounts(raw['counts']),
    previews: toPreviews(raw['previews']),
    exposure: toExposure(raw['exposure']),
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
