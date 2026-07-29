import 'server-only';

/**
 * 콘솔 진단 결과의 형태.
 *
 * 서버가 돌려주는 한 벌의 원시 결과를 그대로 받는다. 기획서 §12.3 은 **한 원시 결과에서
 * 보기만 다르게** 만들고 계산을 중복하지 말라고 못박는다 — 사업자용·분석가용·개발자용
 * 화면이 각자 다른 숫자를 계산하기 시작하면, 같은 진단인데 화면마다 값이 달라진다.
 *
 * 그래서 여기서는 이름만 우리 쪽 표기로 옮기고 **아무것도 계산하지 않는다.**
 */

/** 항목 하나의 판정. */
export type CheckStatus = 'PASS' | 'WARNING' | 'FAIL' | 'NOT_APPLICABLE' | 'UNKNOWN';

export interface CategoryScore {
  readonly categoryId: string;
  readonly name: string;
  /** 이 영역이 100점 만점에서 차지하는 몫. 여덟 영역의 합이 100이다. */
  readonly weight: number;
  readonly status: string;
  /** 영역 안에서의 100점 환산. 채점 불가면 `null` — 0점이 아니다. */
  readonly score: number | null;
  readonly coverage: number;
  readonly confidence: number;
  readonly failingCheckIds: readonly string[];
  readonly unknownCheckIds: readonly string[];
  readonly notApplicableCheckIds: readonly string[];
}

/** 이 항목을 재려면 누가 움직여야 하는가. 뒤의 둘은 배점에서 빠진다. */
export type Availability = 'SELF_SERVICE' | 'CUSTOMER_GRANTED' | 'PAID_PROVIDER';

export interface Outcome {
  readonly checkId: string;
  /** 명세가 정한 이름. 이것이 없으면 화면에 `seo.onpage.heading_hierarchy` 가 찍힌다. */
  readonly title: string;
  readonly categoryId: string;
  readonly categoryName: string;
  readonly severity: string;
  readonly remediationOwner: string;
  readonly availability: Availability;
  /** 왜 이 항목을 보는지. 명세의 근거 문장. */
  readonly reference: string | null;
  readonly status: CheckStatus;
  readonly confidenceLevel: string | null;
  readonly note: string | null;
  readonly evidenceIds: readonly string[];
  /** 수집기가 실제로 본 값. 화면의 "원인 상세" 가 여기서 나온다. */
  readonly observed: unknown;
}

/** 고쳐야 하는 것 하나 — 무엇을·왜·어떻게·어떻게 확인하는지까지. */
export interface Issue {
  readonly checkId: string;
  readonly title: string;
  readonly summary: string;
  readonly affectedUrls: readonly string[];
  readonly evidenceIds: readonly string[];
  readonly remediation: string;
  readonly remediationOwner: string;
  readonly businessImpact: string;
  readonly fixExample: string | null;
  readonly reverificationNote: string;
}

/** 판정의 근거. 감사할 수 없는 지적은 소문이다. */
export interface Evidence {
  readonly evidenceId: string;
  readonly kind: string;
  readonly url: string | null;
  readonly collectedAt: string;
  readonly contentHash: string;
  readonly excerpt: string;
}

export interface UnknownCheck {
  readonly checkId: string;
  readonly categoryId: string;
  readonly title: string;
  /** 왜 못 쟀는지. "측정 불가" 만 띄우면 고장으로 읽힌다. */
  readonly reason: string;
}

export interface Improvement {
  readonly checkId: string;
  readonly categoryId: string;
  readonly title: string;
  /** 고쳤을 때 전체 점수가 오르는 폭. 채점기가 실제 산식으로 계산한 값이다. */
  readonly gainPoints: number;
  /** 상한에 걸려 지금은 고쳐도 오르지 않는다. 이때 `gainPoints` 는 0이다. */
  readonly blockedByCap: boolean;
  readonly severity: string;
  readonly remediationOwner: string;
}

export interface AppliedCap {
  readonly capId: string;
  readonly maxOverallScore: number;
  readonly reason: string;
  readonly releaseCondition: string;
  readonly triggeredBy: readonly string[];
}

export interface ConsoleScanResult {
  readonly targetUrl: string;
  readonly summary: string;
  readonly specId: string;
  readonly specVersion: string;
  readonly specChecksum: string;
  readonly status: string;
  readonly score: number | null;
  /** 상한이 걸리기 전 점수. 상한이 왜 아픈지 보여줄 때만 쓴다. */
  readonly scoreBeforeCaps: number | null;
  readonly bandId: string | null;
  readonly coverage: number;
  readonly confidence: number;
  readonly categories: readonly CategoryScore[];
  readonly appliedCaps: readonly AppliedCap[];
  readonly outcomes: readonly Outcome[];
  readonly issues: readonly Issue[];
  /** 조치 우선순위. 이득이 큰 것부터. */
  readonly improvements: readonly Improvement[];
  readonly evidence: readonly Evidence[];
  readonly unknownChecks: readonly UnknownCheck[];
  readonly notes: readonly string[];
  readonly generatedAt: string;
}

const STATUSES: readonly CheckStatus[] = [
  'PASS',
  'WARNING',
  'FAIL',
  'NOT_APPLICABLE',
  'UNKNOWN',
];

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function list(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

function str(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}

function strOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function num(source: Record<string, unknown>, key: string): number {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

/** 없는 점수는 `null` 로 남긴다. 0 으로 채우면 "0점" 으로 읽힌다. */
function numOrNull(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function strings(source: Record<string, unknown>, key: string): readonly string[] {
  return list(source[key]).filter((item): item is string => typeof item === 'string');
}

function status(value: unknown): CheckStatus {
  // 모르는 판정을 통과로 접지 않는다. 모르면 모른다고 한다.
  return STATUSES.includes(value as CheckStatus) ? (value as CheckStatus) : 'UNKNOWN';
}

const AVAILABILITIES: readonly Availability[] = [
  'SELF_SERVICE',
  'CUSTOMER_GRANTED',
  'PAID_PROVIDER',
];

function availability(value: unknown): Availability {
  // 모르는 값이면 우리가 재는 항목으로 본다 — 배점에서 조용히 빼는 쪽이 위험하다.
  return AVAILABILITIES.includes(value as Availability)
    ? (value as Availability)
    : 'SELF_SERVICE';
}

export function toConsoleScanResult(
  envelope: unknown,
  targetUrl: string,
): ConsoleScanResult | null {
  const body = record(envelope);
  const data = record(body['data']);
  const meta = record(body['meta']);
  const score = record(data['score']);
  if (Object.keys(score).length === 0) {
    return null;
  }

  return {
    targetUrl,
    summary: str(data, 'summary_ko'),
    specId: str(score, 'spec_id'),
    specVersion: str(score, 'spec_version'),
    specChecksum: str(score, 'spec_checksum'),
    status: str(score, 'status'),
    score: numOrNull(score, 'score'),
    scoreBeforeCaps: numOrNull(score, 'score_before_caps'),
    bandId: strOrNull(score, 'band_id'),
    coverage: num(score, 'coverage'),
    confidence: num(score, 'confidence'),
    categories: list(score['categories']).map((raw) => {
      const item = record(raw);
      return {
        categoryId: str(item, 'category_id'),
        name: str(item, 'name_ko'),
        weight: num(item, 'weight'),
        status: str(item, 'status'),
        score: numOrNull(item, 'score'),
        coverage: num(item, 'coverage'),
        confidence: num(item, 'confidence'),
        failingCheckIds: strings(item, 'failing_check_ids'),
        unknownCheckIds: strings(item, 'unknown_check_ids'),
        notApplicableCheckIds: strings(item, 'not_applicable_check_ids'),
      };
    }),
    appliedCaps: list(score['applied_caps']).map((raw) => {
      const item = record(raw);
      return {
        capId: str(item, 'cap_id'),
        maxOverallScore: num(item, 'max_overall_score'),
        reason: str(item, 'reason_ko'),
        releaseCondition: str(item, 'release_condition_ko'),
        triggeredBy: strings(item, 'triggered_by'),
      };
    }),
    outcomes: list(data['outcomes']).map((raw) => {
      const item = record(raw);
      return {
        checkId: str(item, 'check_id'),
        title: str(item, 'title_ko'),
        categoryId: str(item, 'category_id'),
        categoryName: str(item, 'category_name_ko'),
        severity: str(item, 'severity'),
        remediationOwner: str(item, 'remediation_owner'),
        availability: availability(item['availability']),
        reference: strOrNull(item, 'reference_ko'),
        status: status(item['status']),
        confidenceLevel: strOrNull(item, 'confidence_level'),
        note: strOrNull(item, 'note'),
        evidenceIds: strings(item, 'evidence_ids'),
        observed: item['observed'] ?? null,
      };
    }),
    improvements: list(data['improvements']).map((raw) => {
      const item = record(raw);
      return {
        checkId: str(item, 'check_id'),
        categoryId: str(item, 'category_id'),
        title: str(item, 'title_ko'),
        gainPoints: num(item, 'gain_points'),
        blockedByCap: item['blocked_by_cap'] === true,
        severity: str(item, 'severity'),
        remediationOwner: str(item, 'remediation_owner'),
      };
    }),
    issues: list(data['issues']).map((raw) => {
      const item = record(raw);
      return {
        checkId: str(item, 'check_id'),
        title: str(item, 'title_ko'),
        summary: str(item, 'summary_ko'),
        affectedUrls: strings(item, 'affected_urls'),
        evidenceIds: strings(item, 'evidence_ids'),
        remediation: str(item, 'remediation_ko'),
        remediationOwner: str(item, 'remediation_owner'),
        businessImpact: str(item, 'business_impact_ko'),
        fixExample: strOrNull(item, 'fix_example'),
        reverificationNote: str(item, 'reverification_note_ko'),
      };
    }),
    evidence: list(data['evidence']).map((raw) => {
      const item = record(raw);
      return {
        evidenceId: str(item, 'evidence_id'),
        kind: str(item, 'kind'),
        url: strOrNull(item, 'url'),
        collectedAt: str(item, 'collected_at'),
        contentHash: str(item, 'content_hash'),
        excerpt: str(item, 'excerpt'),
      };
    }),
    unknownChecks: list(data['unknown_checks']).map((raw) => {
      const item = record(raw);
      return {
        checkId: str(item, 'check_id'),
        categoryId: str(item, 'category_id'),
        title: str(item, 'title_ko'),
        reason: str(item, 'reason_ko'),
      };
    }),
    notes: strings(data, 'notes_ko'),
    generatedAt: str(meta, 'generated_at'),
  };
}
