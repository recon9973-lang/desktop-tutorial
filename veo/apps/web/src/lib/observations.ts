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
  readonly mention_rate: Rate;
  readonly citation_rate: Rate;
  readonly prompt_coverage: Rate;
  readonly is_partial_measurement: boolean;
  readonly caveats_ko: readonly string[];
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
  readonly weight: number;
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
