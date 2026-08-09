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
  kind: 'SEO' | 'GEO' = 'SEO',
): Promise<ConsoleOutcome<readonly HistoryEntry[]>> {
  // 한 번의 진단이 두 눈금을 **각각** 저장하므로 이력도 눈금마다 따로다. 이 인자가
  // 없던 동안 GEO 탭은 SEO 이력과 SEO 증감을 그렸다 — 화면이 GEO 라고 말하면서
  // SEO 숫자를 보여주는 상태였다.
  const outcome = await callConsoleApi(
    `/api/seo/scans/history?site_id=${encodeURIComponent(siteId)}&kind=${kind}`,
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

/**
 * 이 진단이 **실제로 받은 응답** — 판정이 아니라 원자료.
 *
 * ## 왜 화면이 필요했나
 *
 * 점수가 이상할 때 열어 볼 자리가 없었다. 서버는 처음부터 이 값을 남기고 있었고
 * (`GET /api/seo/scans/{id}/captures`), 그 자리가 없어서 venomad 진단의 원인을
 * 확정하는 데 하루가 들었다(`seo/schemas.py:250`). 화면만 안 붙어 있었다
 * (`audit/2026-08-08-server-ui-gap.md` §B — *"판정은 보이는데 무엇을 받아서 그렇게
 * 판정했는지는 화면에서 못 본다"*).
 *
 * 새로 재지 않는다. **저장된 것만 읽는다** — 거래처 서버에 요청이 나가지 않는다.
 */
export interface FetchCapture {
  readonly url: string;
  readonly finalUrl: string;
  readonly status: number;
  readonly headers: Readonly<Record<string, string>>;
  /** 우리가 **보낸** 헤더. 봇 차단을 만났을 때 무엇을 보내서 그랬는지 알아야 한다. */
  readonly requestHeaders: Readonly<Record<string, string>>;
  /** 받은 본문. 상한을 넘으면 앞부분만이고 `truncated` 가 참이다. */
  readonly body: string;
  readonly byteSize: number;
  readonly truncated: boolean;
  readonly contentHash: string;
  readonly fetchedAt: string;
  /** 문서로 읽지 못했으면 그 사유. 읽었으면 `null`. */
  readonly readFailureKo: string | null;
}

export interface ScanCaptures {
  readonly scanRunId: string;
  readonly captures: readonly FetchCapture[];
  readonly noteKo: string;
}

export async function readCaptures(
  scanRunId: string,
): Promise<ConsoleOutcome<ScanCaptures>> {
  const outcome = await callConsoleApi(
    `/api/seo/scans/${encodeURIComponent(scanRunId)}/captures`,
  );
  if (!outcome.ok) return outcome;

  const data = record(outcome.data);
  return {
    ok: true,
    data: {
      scanRunId: str(data, 'scan_run_id'),
      noteKo: str(data, 'note_ko'),
      captures: list(data['captures']).map((raw) => {
        const item = record(raw);
        return {
          url: str(item, 'url'),
          finalUrl: str(item, 'final_url'),
          status: num(item, 'status'),
          headers: headerMap(item['headers']),
          requestHeaders: headerMap(item['request_headers']),
          body: str(item, 'body'),
          byteSize: num(item, 'byte_size'),
          truncated: item['truncated'] === true,
          contentHash: str(item, 'content_hash'),
          fetchedAt: str(item, 'fetched_at'),
          readFailureKo: strOrNull(item, 'read_failure_ko'),
        };
      }),
    },
    meta: outcome.meta,
  };
}

/** 헤더는 문자열 짝만 남긴다. 모양이 다른 값을 화면으로 흘리지 않는다. */
function headerMap(value: unknown): Record<string, string> {
  const source = record(value);
  const out: Record<string, string> = {};
  for (const [key, item] of Object.entries(source)) {
    if (typeof item === 'string') out[key] = item;
  }
  return out;
}
