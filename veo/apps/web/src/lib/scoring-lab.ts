import 'server-only';

import { callConsoleApi, readAllPages, type ConsoleOutcome } from '@/lib/console-api';
import { record, textOrNull } from '@/lib/json';

/**
 * 채점 명세의 수명주기 — 초안에서 발행까지.
 *
 * **왜 화면이 필요한가.** 채점 기준을 바꾸려면 지금까지는 개발자가 파일을 고치고 배포해야
 * 했다. 그런데 그 일을 하는 기능은 처음부터 완성돼 있었다 — 검증·골든 대조·승인·발행·
 * 폐기·과거 재계산까지 API 11개와 시험 83개. 부를 화면이 없어서 "없는 기능" 이었다(0-E).
 *
 * **화면은 무엇이 허용되는지 스스로 판단하지 않는다.** 서버가 `allowed_transitions` 로
 * 알려주고, 화면은 그것만 그린다. 상태 기계를 두 벌로 두면 화면이 "발행" 을 보여주는데
 * 서버가 거절하는 날이 오고, 그때 사람은 자기가 뭘 잘못했는지 알 수 없다.
 */

export interface SpecVersion {
  readonly id: string;
  readonly specId: string;
  readonly domain: string;
  readonly version: string;
  readonly status: string;
  readonly statusLabel: string;
  readonly checksum: string;
  readonly changelog: string | null;
  readonly effectiveAt: string | null;
  readonly createdAt: string;
  /** 골든 픽스처 대조 결과. **아직 안 돌렸으면 `null`** — 통과와 구분해야 한다. */
  readonly goldenPassed: boolean | null;
  readonly goldenSummary: string | null;
}

export interface SpecVersionDetail extends SpecVersion {
  /** 지금 이 버전에서 서버가 허락하는 다음 동작. 화면은 이것만 그린다. */
  readonly allowedTransitions: readonly string[];
  readonly validationSummary: string | null;
  readonly validationPassed: boolean | null;
  readonly diffSummary: string | null;
}


function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}


/** 참·거짓·모름 셋을 구분한다. 안 돌린 검증을 실패로 접으면 안 된다. */
function boolOrNull(source: Record<string, unknown>, key: string): boolean | null {
  const value = source[key];
  return typeof value === 'boolean' ? value : null;
}

function toVersion(source: Record<string, unknown>): SpecVersion {
  return {
    id: text(source, 'id'),
    specId: text(source, 'spec_id'),
    domain: text(source, 'domain'),
    version: text(source, 'semantic_version'),
    status: text(source, 'status'),
    statusLabel: text(source, 'status_label_ko'),
    checksum: text(source, 'checksum'),
    changelog: textOrNull(source, 'changelog'),
    effectiveAt: textOrNull(source, 'effective_at'),
    createdAt: text(source, 'created_at'),
    goldenPassed: boolOrNull(source, 'golden_passed'),
    goldenSummary: textOrNull(source, 'golden_summary_ko'),
  };
}

export async function listSpecVersions(): Promise<ConsoleOutcome<readonly SpecVersion[]>> {
  const outcome = await readAllPages('/api/lab/scoring-versions');
  if (!outcome.ok) return outcome;
  return { ...outcome, data: outcome.data.map((raw) => toVersion(record(raw))) };
}

export async function readSpecVersion(
  versionId: string,
): Promise<ConsoleOutcome<SpecVersionDetail>> {
  const outcome = await callConsoleApi<unknown>(
    `/api/lab/scoring-versions/${encodeURIComponent(versionId)}`,
  );
  if (!outcome.ok) return outcome;

  const source = record(outcome.data);
  const validation = record(source['validation']);
  const diff = record(source['diff']);
  const transitions = source['allowed_transitions'];

  return {
    ...outcome,
    data: {
      ...toVersion(source),
      allowedTransitions: Array.isArray(transitions)
        ? transitions.filter((one): one is string => typeof one === 'string')
        : [],
      validationSummary: textOrNull(validation, 'summary_ko'),
      validationPassed: boolOrNull(validation, 'passed'),
      diffSummary: textOrNull(diff, 'summary_ko'),
    },
  };
}

/** 서버가 허락한 동작만 부른다. 화면이 목록을 지어내지 않는다. */
export type SpecAction = 'submit' | 'approve' | 'send-back' | 'publish' | 'retire' | 'golden-run';

export async function actOnSpecVersion(
  versionId: string,
  action: SpecAction,
): Promise<ConsoleOutcome<unknown>> {
  return callConsoleApi(
    `/api/lab/scoring-versions/${encodeURIComponent(versionId)}/${action}`,
    { method: 'POST' },
  );
}
