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
