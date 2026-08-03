import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';

/**
 * GEO 관측 — 엔진에서 읽어 오는 쪽.
 *
 * 여기 있는 타입은 화면이 오해할 수 없도록 **엔진이 준 모양 그대로** 옮긴다. 특히
 * 비율은 절대 `number` 하나로 줄이지 않는다. `value` 가 `null` 인 것과 `0.0` 인 것은
 * 정반대의 뜻이고, 그 둘을 한 필드로 접는 순간 화면은 구분할 방법을 잃는다.
 */

/** 표본이 감당하는 무게. 화면은 이 값에 따라 다르게 그려야 한다. */
export type SampleAdequacy = 'NO_DATA' | 'TOO_SMALL' | 'DIRECTIONAL' | 'ADEQUATE';

export interface Rate {
  readonly label_ko: string;
  readonly numerator: number;
  /** 0이면 잴 수 없었다는 뜻이다. "0번 됐다"가 아니다. */
  readonly denominator: number;
  /** 실행 3회 미만이면 `null`. 숫자를 내보내지 않는 것이 규칙이다. */
  readonly value: number | null;
  /** 화면에 그대로 쓰는 문자열. `value`를 직접 포맷하지 말 것. */
  readonly percent_text_ko: string;
  readonly low: number | null;
  readonly high: number | null;
  readonly adequacy: SampleAdequacy;
  /** 경쟁사 비교 보고에 실을 수 있는가. 실행 5회 이상이어야 참. */
  readonly is_comparison_grade: boolean;
  readonly note_ko: string;
  readonly summary_ko: string;
}

export interface VisibilityMetrics {
  readonly answers_recorded: number;
  readonly answers_valid: number;
  readonly answers_with_visible_citations: number;
  /** 상호는 나왔지만 같은 이름의 다른 업체와 갈리지 않아 판정을 보류한 응답 수.
   *  '언급 없음' 과 같은 칸에 두면 안 된다 — 사람이 보면 풀리는 건이다. */
  readonly answers_pending_disambiguation: number;
  /** 같은 질문의 반복이 **시간적으로** 얼마나 벌어져 있었나.
   *  붙어 있으면 위 신뢰구간은 실제보다 좁다 — 반복이 독립이라는 가정 위에서만
   *  성립하기 때문이다. */
  readonly repetition_spread: {
    readonly shortest_gap_seconds: number | null;
    readonly measured_pairs: number;
    readonly is_spread_out: boolean;
    readonly caveat_ko: string | null;
  };
  readonly mention_rate: Rate;
  readonly citation_rate: Rate;
  readonly prompt_coverage: Rate;
  /**
   * 추천을 묻는 질문에서 상호가 나온 비율.
   *
   * **AI 가 우리를 추천했는지가 아니다.** 그건 답변 문장을 읽어야 알 수 있고 아직
   * 재지 않는다. 화면에서 이름을 줄여 '추천률' 로 쓰면 재지 않은 것을 잰 것처럼
   * 보고하게 된다.
   */
  readonly recommendation_prompt_mention_rate: Rate;
  /**
   * 엔진이 이번 실행에서 몇 곳을 인용했나.
   *
   * 인용률을 읽는 방법을 바꾼다 — 두 곳만 인용하는 엔진에서의 20% 와 마흔 곳을
   * 인용하는 엔진에서의 20% 는 같은 뜻이 아니다.
   */
  readonly source_diversity: {
    readonly answers_with_visible_citations: number;
    readonly distinct_domains: number;
    readonly total_citations: number;
    readonly top_domains: readonly { readonly domain: string; readonly citations: number }[];
    /** 거짓이면 위 숫자는 0곳이 아니라 **측정 불가**다. */
    readonly is_measurable: boolean;
  };
  /** 같은 질문을 같은 엔진에 다시 물었을 때 답이 같았나. */
  readonly stability: {
    readonly repeated_groups: number;
    readonly consistent_groups: number;
    readonly unstable_group_count: number;
    /** 2회 이상 물은 조합이 없으면 거짓. 한 번 물은 답은 흔들렸는지 알 수 없다. */
    readonly is_measurable: boolean;
    readonly rate: Rate;
  };
  readonly is_partial_measurement: boolean;
  readonly caveats_ko: readonly string[];
}

export interface GatedItem {
  readonly assessment_id: string;
  readonly outcome: string;
  readonly explanation_ko: string;
  readonly assessment: {
    readonly kind: string;
    readonly band_label_ko: string;
    readonly claim_text: string;
    readonly automated: { readonly rationale_ko: string; readonly verdict: string };
  };
  readonly review: { readonly stage_label_ko: string; readonly is_reviewed: boolean };
}

export interface RiskFindings {
  readonly customer: {
    readonly findings: readonly unknown[];
    readonly withheld: { readonly total: number; readonly explanation_ko: string };
    readonly not_measured: { readonly total: number; readonly explanation_ko: string };
  };
  readonly internal: { readonly items: readonly GatedItem[] };
  /** 아직 재지 않는 위험 유형과 그 이유. 이것 없이 "0건" 만 보이면 위험이 없다로 읽힌다. */
  readonly kinds_not_yet_produced: readonly { readonly kind: string; readonly reason_ko: string }[];
}

export interface ReviewQueueItem {
  readonly assessment_id: string;
  readonly kind: string;
  readonly band_label_ko: string;
  readonly severity: string;
  /** 기계가 답변에서 잘라낸 그 문장. 요약이 아니다 — 그 차이가 판정의 전부다. */
  readonly claim_text: string;
  readonly automated_verdict: string;
  readonly automated_rationale_ko: string;
  readonly stage: string;
  readonly stage_label_ko: string;
  /** 다른 검수자가 맡고 있는지. **누가**인지는 오지 않는다. */
  readonly is_held_by_someone: boolean;
  readonly is_mine: boolean;
}

export interface ReviewQueue {
  readonly items: readonly ReviewQueueItem[];
  readonly total: number;
  readonly rejection_reasons: readonly { readonly value: string; readonly label_ko: string }[];
}

export interface ReviewedItem {
  readonly assessment_id: string;
  readonly stage: string;
  readonly stage_label_ko: string;
  readonly stored_as: string;
  readonly is_reviewed: boolean;
  readonly disagrees_with_automation: boolean;
}

export interface ObservationRun {
  readonly id: string;
  readonly project_id: string;
  readonly prompt_set_id: string;
  readonly status: string;
  readonly is_complete: boolean;
  readonly engines: readonly string[];
  readonly repetitions_per_prompt: number;
  readonly executions_planned: number;
  readonly executions_attempted: number;
  readonly executions_valid: number;
  readonly executions_skipped: number;
  readonly stopped_reason: string | null;
  readonly summary_ko: string;
  readonly unpriced_calls: number;
  readonly total_cost_usd: number;
  readonly started_at: string | null;
  readonly finished_at: string | null;
}

export interface EngineStatus {
  readonly engine: string;
  readonly state: string;
  readonly state_label_ko: string;
  readonly usable: boolean;
}

export interface PromptSummary {
  readonly prompt_id: string;
  readonly text: string;
  readonly intent: string;
  readonly funnel: string;
}

export interface PromptSet {
  readonly id: string;
  readonly project_id: string;
  readonly name: string;
  readonly version: string;
  readonly locale: string;
  readonly checksum: string;
  readonly prompts: readonly PromptSummary[];
  readonly balance_warnings_ko: readonly string[];
}

export interface Job {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  /** 참이면 **끝났는지 아닌지 모른다**는 뜻. 실행 중과 같게 그리면 안 된다. */
  readonly is_stale: boolean;
  readonly progress: number;
  readonly current_stage: string | null;
  readonly stages: readonly string[];
  readonly error_code: string | null;
  readonly safe_error_message: string | null;
  readonly result_run_id: string | null;
  readonly partial_result_available: boolean;
  readonly note_ko: string;
  readonly finished_at: string | null;
}

const TERMINAL = new Set([
  'SUCCEEDED',
  'PARTIAL_SUCCESS',
  'FAILED_FINAL',
  'FAILED_RETRYABLE',
  'CANCELLED',
  'EXPIRED',
]);

/** 더 기다릴 이유가 있는가. 소식이 끊긴 작업은 **기다리지 않는다.** */
export function isSettled(job: Job): boolean {
  return TERMINAL.has(job.status) || job.is_stale;
}

export async function readEngines(): Promise<
  ConsoleOutcome<{ engines: EngineStatus[]; usable_count: number; note_ko: string }>
> {
  return callConsoleApi('/api/observations/engines');
}

export async function readPromptSets(): Promise<
  ConsoleOutcome<{ items: PromptSet[]; total: number }>
> {
  return callConsoleApi('/api/observations/prompt-sets');
}

export async function readRuns(): Promise<
  ConsoleOutcome<{ items: ObservationRun[]; total: number }>
> {
  return callConsoleApi('/api/observations/runs');
}

export async function readRun(
  runId: string,
): Promise<ConsoleOutcome<{ run: ObservationRun; metrics: VisibilityMetrics }>> {
  return callConsoleApi(`/api/observations/runs/${encodeURIComponent(runId)}`);
}

/**
 * 이 관측이 남긴 위험 판정 — **공개 게이트를 지난 뒤의 모습.**
 *
 * `customer` 는 고객 문서용, `internal` 은 내부 화면 전용이다. 후자에는 검수되지 않은
 * 지적의 원문이 들어 있으므로 공개 리포트 경로에서 부르면 안 된다.
 */
export async function readRunRisks(
  runId: string,
): Promise<ConsoleOutcome<RiskFindings>> {
  return callConsoleApi(`/api/observations/runs/${encodeURIComponent(runId)}/risks`);
}

export async function readReviewQueue(): Promise<ConsoleOutcome<ReviewQueue>> {
  return callConsoleApi('/api/observations/review-queue');
}

/**
 * 검수 한 걸음 — 착수·반납·판정.
 *
 * 셋을 한 함수로 두는 이유는 실패를 읽는 방식이 같아서다. **409 와 422 는 다르다** —
 * 전자는 지금은 안 되지만 나중엔 될 수 있고(다른 사람이 맡고 있다), 후자는 이 순서로는
 * 안 된다(맡지도 않고 판정하려 한다). 합치면 검수자가 새로고침만 반복하게 된다.
 */
export async function reviewStep(
  assessmentId: string,
  step: 'claim' | 'release' | 'decide',
  body?: {
    readonly decision: 'CONFIRMED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE';
    readonly rejection_reason?: string | null;
    readonly note_ko?: string | null;
  },
): Promise<ConsoleOutcome<ReviewedItem>> {
  return callConsoleApi(
    `/api/observations/review-queue/${encodeURIComponent(assessmentId)}/${step}`,
    { method: 'POST', ...(body === undefined ? {} : { body }) },
  );
}

export async function readJob(jobId: string): Promise<ConsoleOutcome<Job>> {
  return callConsoleApi(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export async function readObservationJobs(): Promise<
  ConsoleOutcome<{ items: Job[]; total: number }>
> {
  return callConsoleApi('/api/jobs?type=GEO_OBSERVATION_RUN&limit=10');
}

/**
 * 관측을 시작한다. 엔진은 202를 돌려주고 실행은 뒤에서 돈다.
 *
 * `idempotencyKey` 를 넘기면 같은 키로 다시 눌러도 두 번 실행되지 않는다. 관측은 돈이
 * 나가는 일이라, 새로고침 한 번이 두 번째 청구가 되면 안 된다.
 */
export async function startObservation(input: {
  readonly promptSetId: string;
  readonly engine: string;
  readonly model: string;
  readonly searchMode: string;
  readonly repetitions: number;
  readonly idempotencyKey: string;
}): Promise<ConsoleOutcome<Job>> {
  return callConsoleApi('/api/observations/runs', {
    method: 'POST',
    headers: { 'Idempotency-Key': input.idempotencyKey },
    body: {
      prompt_set_id: input.promptSetId,
      repetitions: input.repetitions,
      engines: [
        {
          engine: input.engine,
          model: input.model,
          search_mode: input.searchMode,
        },
      ],
    },
  });
}

/* ── GEO 준비도 ─────────────────────────────────────────────────────── */

export interface GeoCategory {
  readonly category_id: string;
  readonly name_ko: string;
  /** 이 영역의 배점. `contributes_to_score` 가 거짓이면 분모에 들어가지 않는다. */
  readonly weight: number;
  /** 점수에 반영되는 영역인가. 거짓이면 하단 참고 구역으로. */
  readonly contributes_to_score: boolean;
  /** 점수 밖인 이유. 점수 밖일 때만 채워진다. */
  readonly outside_score_reason_ko: string | null;
  readonly status: 'SCORED' | 'NOT_APPLICABLE' | 'UNKNOWN';
  readonly score: number | null;
  readonly coverage: number;
  readonly confidence: number;
  readonly failing_check_ids: readonly string[];
  readonly unknown_check_ids: readonly string[];
  readonly not_applicable_check_ids: readonly string[];
}

export interface GeoGate {
  readonly gate_id: string;
  readonly status_code: string;
  readonly label_ko: string;
  readonly description_ko: string | null;
  readonly triggered_by: readonly string[];
}

export interface GeoLookup {
  readonly engine: string;
  readonly totals: Readonly<Record<string, number>>;
  readonly considered: number;
  readonly accepted: number;
  /** 이름이 비슷한 다른 업체로 보여 제외한 건수. 감추면 "우리가 못 찾았다"로 읽힌다. */
  readonly rejected_as_another_business: number;
  readonly unavailable: Readonly<Record<string, string>>;
}

export interface GeoReadiness {
  readonly target_url: string;
  readonly readiness: {
    readonly spec_id: string;
    readonly spec_version: string;
    readonly status: 'SCORED' | 'NOT_APPLICABLE' | 'UNKNOWN';
    readonly score: number | null;
    readonly band_label_ko: string | null;
    readonly coverage: number;
    readonly confidence: number;
    readonly categories: readonly GeoCategory[];
  };
  /** 점수와 **분리된** 블록. 95점이면서 동시에 노출 차단일 수 있다. */
  readonly exposure: {
    readonly blocked: boolean;
    readonly status_codes: readonly string[];
    readonly gates: readonly GeoGate[];
  };
  readonly summary_ko: string;
  readonly scope_notice_ko: string;
  readonly notes_ko: readonly string[];
  /**
   * 항목별 판정 — 무엇을 보고 그렇게 판정했는지까지.
   *
   * 엔진은 처음부터 이것을 보내고 있었는데 화면이 읽지 않아, GEO 는 영역 점수만 보이고
   * "왜" 와 "어떻게 고치나" 가 없었다. SEO 와 같은 이름을 쓴다 — 같은 화면 부품이 읽는다.
   */
  readonly checks?: readonly GeoCheck[];
  /** 조치 우선순위 — 이득이 큰 것부터. 채점기가 낸 값이며 화면은 어림하지 않는다. */
  readonly improvements?: readonly GeoImprovement[];
  /**
   * 고칠 것과 고치는 법. 붙여넣을 코드까지 들어 있다.
   *
   * 선택 필드다 — 이 필드가 생기기 **전에 저장된 실행**에는 없다. 없는 것을 빈 목록으로
   * 꾸미지 않고, 화면이 "없다" 를 그대로 다루게 둔다.
   */
  readonly issues?: readonly GeoIssue[];
  /** 참고 조회 결과. 점수와 무관하며 하단 참고 구역에만 쓴다. */
  readonly lookup: GeoLookup | null;
}

export interface GeoCheck {
  readonly check_id: string;
  readonly title_ko: string;
  readonly category_id: string;
  readonly category_name_ko: string;
  readonly remediation_owner: string;
  readonly status: string;
  readonly confidence_level: string | null;
  readonly note_ko: string | null;
  readonly evidence_ids: readonly string[];
  /** 수집기가 실제로 본 값. 판정을 내리지 못했으면 `null`. */
  readonly observed: unknown;
}

export interface GeoImprovement {
  readonly check_id: string;
  readonly category_id: string;
  readonly title_ko: string;
  /** 이 항목을 통과로 바꿨을 때 전체 점수가 오르는 폭. */
  readonly gain_points: number;
  /** 상한에 걸려 지금은 고쳐도 점수가 오르지 않는 상태. 이때 `gain_points` 는 0이다. */
  readonly blocked_by_cap: boolean;
}

export interface GeoIssue {
  readonly check_id: string;
  readonly title_ko: string;
  readonly summary_ko: string;
  readonly remediation_ko: string;
  readonly remediation_owner: string;
  readonly business_impact_ko: string;
  readonly affected_urls: readonly string[];
  readonly evidence_ids: readonly string[];
  readonly fix_example: string | null;
  readonly reverification_note_ko: string;
}

/** 주소 하나로 GEO 준비도를 잰다. SEO 진단과 같은 수집 경로를 쓴다. */
export async function scanGeoReadiness(
  targetUrl: string,
): Promise<ConsoleOutcome<GeoReadiness>> {
  return callConsoleApi('/api/geo/readiness/scans', {
    method: 'POST',
    body: { target_url: targetUrl },
    // 사이트를 실제로 가져오므로 목록 조회와 시간 감각이 다르다.
    timeoutMs: 120_000,
  });
}

/**
 * 저장된 GEO 실행(동반 채점)을 그대로 다시 읽는다. 대상 사이트에 요청이 가지 않는다.
 * SEO 실행의 식별자를 넣으면 404 다 — 축이 다르면 스냅샷의 모양이 다르다.
 */
export async function readSavedGeoReadiness(
  scanRunId: string,
): Promise<ConsoleOutcome<GeoReadiness>> {
  return callConsoleApi(`/api/geo/readiness/scans/${encodeURIComponent(scanRunId)}`);
}

/**
 * 이번 달 AI 호출 사용량과 비용.
 *
 * `measured_cost_usd` 에 **금액을 못 낸 호출이 0원으로 더해져 있지 않다.** 더하면
 * 합계가 "예산 안" 처럼 보이는데 자료가 그것을 뒷받침하지 않는다. 그래서
 * `unmeasurable_calls` 와 `remedies_ko` 를 같은 무게로 함께 보인다.
 */
export interface EngineSpend {
  readonly engine: string;
  readonly calls: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly measured_cost_usd: number;
  readonly unmeasurable_calls: number;
}

export interface Spend {
  readonly month: string;
  readonly total_calls: number;
  readonly measured_calls: number;
  readonly unmeasurable_calls: number;
  readonly measured_cost_usd: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  /** COMPLETE | PARTIAL | NONE — 금액이 얼마나 실측인지. */
  readonly measurement: string;
  readonly engines: readonly EngineSpend[];
  readonly remedies_ko: readonly string[];
  readonly summary_ko: string;
}

export const MEASUREMENT_LABELS_KO: Record<string, string> = {
  COMPLETE: '모든 호출에 가격이 적용되었습니다',
  PARTIAL: '일부 호출만 금액을 낼 수 있었습니다',
  NONE: '금액을 낸 호출이 하나도 없습니다',
};

export function measurementLabel(value: string): string {
  return MEASUREMENT_LABELS_KO[value] ?? value;
}

export async function readSpend(month: string | null): Promise<ConsoleOutcome<Spend>> {
  const query = month === null ? '' : `?month=${encodeURIComponent(month)}`;
  return callConsoleApi(`/api/observations/spend${query}`);
}
