/**
 * 발행된 채점 명세 — 서버에서 실시간으로 읽는다.
 *
 * 이 파일이 생기기 전, 콘솔의 "채점 기준 버전" 화면은 **하드코딩된 1.0.0 목록**을
 * 그리고 있었다(lib/scoring.ts). 실제 발행본이 1.9.0 까지 갔는데 화면은 계속
 * 1.0.0 이라고 말했다 — 같은 값을 두 곳이 들고 있으면 한쪽만 고쳐도 나머지가
 * 조용히 틀린다는 그 결함이다. 이제 버전·숫자는 전부 API(=발행 명세)에서 온다.
 */

import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';
import { record } from '@/lib/json';

export interface SpecStageRow {
  readonly id: string;
  readonly nameKo: string;
  readonly weight: number;
  readonly isGate: boolean;
  readonly contributesToScore: boolean;
  readonly checkCount: number;
  readonly urlCheckCount: number;
}

export interface SpecCapRow {
  readonly id: string;
  readonly maxOverallScore: number;
  readonly reasonKo: string;
}

export interface SpecBandRow {
  readonly id: string;
  readonly min: number;
  readonly max: number;
  readonly labelKo: string;
}

export interface SpecChangelogRow {
  readonly version: string;
  readonly date: string;
  readonly summary: string;
}

export interface SpecDesign {
  readonly specId: string;
  readonly version: string;
  readonly status: string;
  readonly effectiveAt: string;
  readonly methodologyOwner: string;
  readonly implementationOwner: string;
  readonly meaningKo: string;
  readonly stages: readonly SpecStageRow[];
  readonly breadthExponent: number;
  readonly warningPenaltyMultiplier: number;
  readonly hasNotSampled: boolean;
  readonly measurementScope: {
    readonly maxPages: number;
    readonly maxDepth: number;
    readonly templateGroupSample: number;
    readonly rationaleKo: string | null;
  } | null;
  readonly sampling: {
    readonly perfLabMaxUrls: number | null;
    readonly perfLabCheckCount: number;
    readonly perfFieldCheckCount: number;
    readonly rationaleKo: string | null;
  } | null;
  readonly caps: readonly SpecCapRow[];
  readonly bands: readonly SpecBandRow[];
  readonly changelog: readonly SpecChangelogRow[];
}


function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function str(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}

function num(source: Record<string, unknown>, key: string): number {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

/** "1.10.0" 과 "1.9.0" 을 문자열로 비교하면 진다 — 숫자 조각으로 비교한다. */
export function compareVersions(a: string, b: string): number {
  const left = a.split('.').map((piece) => Number.parseInt(piece, 10) || 0);
  const right = b.split('.').map((piece) => Number.parseInt(piece, 10) || 0);
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const diff = (left[index] ?? 0) - (right[index] ?? 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

export function toSpecDesign(raw: unknown): SpecDesign {
  const source = record(raw);
  const policy = record(source['status_policy']);
  const scopeRaw = source['measurement_scope'];
  const scope = record(scopeRaw);
  const samplingRaw = source['sampling'];
  const sampling = record(samplingRaw);
  return {
    specId: str(source, 'spec_id'),
    version: str(source, 'version'),
    status: str(source, 'status'),
    effectiveAt: str(source, 'effective_at'),
    methodologyOwner: str(source, 'methodology_owner'),
    implementationOwner: str(source, 'implementation_owner'),
    meaningKo: str(source, 'score_meaning_ko'),
    stages: list(source['categories']).map((entry) => {
      const item = record(entry);
      const checks = list(item['checks']);
      return {
        id: str(item, 'id'),
        nameKo: str(item, 'name_ko'),
        weight: num(item, 'weight'),
        isGate: item['is_gate'] === true,
        contributesToScore: item['contributes_to_score'] !== false,
        checkCount: checks.length,
        urlCheckCount: checks.filter((check) => record(check)['scope'] === 'URL').length,
      };
    }),
    breadthExponent: num(policy, 'breadth_exponent') || 1.0,
    warningPenaltyMultiplier: num(policy, 'warning_penalty_multiplier'),
    hasNotSampled: typeof policy['not_sampled'] === 'string',
    measurementScope:
      scopeRaw === null || scopeRaw === undefined
        ? null
        : {
            maxPages: num(scope, 'max_pages'),
            maxDepth: num(scope, 'max_depth'),
            templateGroupSample: num(scope, 'template_group_sample'),
            rationaleKo: str(scope, 'rationale_ko') || null,
          },
    sampling:
      samplingRaw === null || samplingRaw === undefined
        ? null
        : {
            perfLabMaxUrls:
              typeof sampling['perf_lab_max_urls'] === 'number'
                ? (sampling['perf_lab_max_urls'] as number)
                : null,
            perfLabCheckCount: list(sampling['perf_lab_check_ids']).length,
            perfFieldCheckCount: list(sampling['perf_field_check_ids']).length,
            rationaleKo: str(sampling, 'perf_lab_rationale_ko') || null,
          },
    caps: list(source['caps']).map((entry) => {
      const item = record(entry);
      return {
        id: str(item, 'id'),
        maxOverallScore: num(item, 'max_overall_score'),
        reasonKo: str(item, 'reason_ko'),
      };
    }),
    bands: list(source['bands'])
      .map((entry) => {
        const item = record(entry);
        return {
          id: str(item, 'id'),
          min: num(item, 'min'),
          max: num(item, 'max'),
          labelKo: str(item, 'label_ko'),
        };
      })
      .sort((a, b) => b.min - a.min),
    changelog: list(source['changelog']).map((entry) => {
      const item = record(entry);
      return {
        version: str(item, 'version'),
        date: str(item, 'date'),
        summary: str(item, 'summary'),
      };
    }),
  };
}

/** 명세마다 가장 최신의 발행 버전 하나씩, 상세 전문으로. */
export async function readLatestSpecDesigns(): Promise<
  ConsoleOutcome<readonly SpecDesign[]>
> {
  const listing = await callConsoleApi('/api/scoring/specs');
  if (!listing.ok) return listing;

  const latest = new Map<string, string>();
  for (const entry of list(record(listing.data)['specs'])) {
    const item = record(entry);
    if (str(item, 'status') !== 'PUBLISHED') continue;
    const specId = str(item, 'spec_id');
    const version = str(item, 'version');
    const known = latest.get(specId);
    if (known === undefined || compareVersions(version, known) > 0) {
      latest.set(specId, version);
    }
  }

  const designs: SpecDesign[] = [];
  for (const [specId, version] of [...latest.entries()].sort()) {
    const detail = await callConsoleApi(
      `/api/scoring/specs/${encodeURIComponent(specId)}/${encodeURIComponent(version)}`,
    );
    if (!detail.ok) return detail;
    designs.push(toSpecDesign(detail.data));
  }
  return { ok: true, data: designs, meta: listing.meta };
}
