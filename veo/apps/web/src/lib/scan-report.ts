import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';
import { toConsoleScanResult, type ConsoleScanResult } from '@/lib/console-scan';

/**
 * 저장된 진단 결과와 이력을 읽는다.
 *
 * 화면을 열 때 **다시 재지 않는다.** 같은 주소를 하루에 여러 번 다시 재는 것은 대상
 * 사이트에도 우리 비용에도 부담이고, 변경을 확인하려는 것이 아니면 다시 잴 이유가 없다.
 * 재측정은 사람이 버튼을 눌렀을 때만 일어난다.
 */

export interface HistoryEntry {
  readonly scanRunId: string;
  readonly startedAt: string;
  readonly status: string;
  readonly urlsCollected: number;
  readonly score: number | null;
  readonly bandId: string | null;
  readonly coverage: number;
  readonly confidence: number;
  readonly specVersion: string;
  /** 실행한 사람. 계정이 지워졌거나 예약 실행이면 비어 있다. */
  readonly requestedByName: string | null;
  /**
   * 이 점을 가장 최근 실행과 나란히 놓아도 되는가.
   *
   * 이력 목록은 점을 세로로 늘어놓아 사람이 눈으로 잇게 만든다. 조건이 다른 두 점을
   * 이으면 그 선은 **사이트가 변했다** 는 뜻으로 읽히는데, 실제로 변한 것은 재는
   * 방법이다. 그래서 못 잇는 점에는 이유를 붙인다.
   */
  readonly comparableWithLatest: boolean;
  readonly incomparableReasonKo: string | null;
}

/** 명세가 정한 점수 구간. 화면에 적어 두지 않는다 — 명세가 바뀌면 화면이 거짓말을 한다. */
export interface Band {
  readonly id: string;
  readonly min: number;
  readonly max: number;
  readonly label: string;
  readonly description: string | null;
}

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

function numOrNull(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export async function readHistory(
  siteId: string,
): Promise<ConsoleOutcome<readonly HistoryEntry[]>> {
  const outcome = await callConsoleApi(
    `/api/seo/scans/history?site_id=${encodeURIComponent(siteId)}`,
  );
  if (!outcome.ok) return outcome;

  const entries = list(record(outcome.data)['entries']).map((raw) => {
    const item = record(raw);
    return {
      scanRunId: str(item, 'scan_run_id'),
      startedAt: str(item, 'started_at'),
      status: str(item, 'status'),
      urlsCollected: num(item, 'urls_collected'),
      score: numOrNull(item, 'score'),
      bandId: strOrNull(item, 'band_id'),
      coverage: num(item, 'coverage'),
      confidence: num(item, 'confidence'),
      specVersion: str(item, 'spec_version'),
      requestedByName: strOrNull(item, 'requested_by_name'),
      // 없으면 비교 불가로 읽는다. 모르는 것을 '같은 조건' 으로 바꾸지 않는다.
      comparableWithLatest: item['comparable_with_latest'] === true,
      incomparableReasonKo: strOrNull(item, 'incomparable_reason_ko'),
    };
  });

  return { ok: true, data: entries, meta: outcome.meta };
}

/** 저장된 보고서 그대로. 대상 사이트에 요청이 가지 않는다. */
export async function readSavedReport(
  scanRunId: string,
  targetUrl: string,
): Promise<ConsoleScanResult | null> {
  const outcome = await callConsoleApi(
    `/api/seo/scans/${encodeURIComponent(scanRunId)}`,
  );
  if (!outcome.ok) return null;
  return toConsoleScanResult({ data: outcome.data, meta: outcome.meta }, targetUrl);
}

export async function readBands(
  specId: string,
  version: string,
): Promise<readonly Band[]> {
  const outcome = await callConsoleApi(
    `/api/scoring/specs/${encodeURIComponent(specId)}/${encodeURIComponent(version)}`,
  );
  if (!outcome.ok) return [];

  return list(record(outcome.data)['bands']).map((raw) => {
    const item = record(raw);
    return {
      id: str(item, 'id'),
      min: num(item, 'min'),
      max: num(item, 'max'),
      label: str(item, 'label_ko'),
      description: strOrNull(item, 'description_ko'),
    };
  });
}

/**
 * 명세가 정한 검사별 심각도 — 발행 명세에서 그대로 읽어 온다.
 *
 * GEO 판정 응답에는 심각도가 없다. 일부러 없다: GEO 엔진은 **관측만 하고 점수를 정하지
 * 않는다**는 경계가 있고(`tests/geo/test_engine_boundaries.py`), 심각도는 채점 어휘라
 * 그 안에 둘 수 없다. 그렇다고 화면이 심각도를 지어내서도 안 된다.
 *
 * 그래서 **발행 명세를 직접 읽는다.** 심각도가 사는 곳은 처음부터 여기 하나뿐이고,
 * 화면은 그것을 옮겨 적기만 한다.
 */
export async function readCheckSeverities(
  specId: string,
  version: string,
): Promise<ReadonlyMap<string, string>> {
  const outcome = await callConsoleApi(
    `/api/scoring/specs/${encodeURIComponent(specId)}/${encodeURIComponent(version)}`,
  );
  if (!outcome.ok) return new Map();

  const pairs: [string, string][] = [];
  for (const rawCategory of list(record(outcome.data)['categories'])) {
    for (const rawCheck of list(record(rawCategory)['checks'])) {
      const check = record(rawCheck);
      const id = str(check, 'id');
      const severity = str(check, 'severity');
      // 명세에 심각도가 비어 있으면 넣지 않는다 — 없는 것을 기본값으로 채우면
      // 화면이 명세보다 많이 아는 척하게 된다.
      if (id !== '' && severity !== '') pairs.push([id, severity]);
    }
  }
  return new Map(pairs);
}
