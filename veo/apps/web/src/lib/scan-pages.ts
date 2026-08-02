/**
 * 페이지별 판정·점수 — 저장된 진단에서, 재크롤 없이 (⑥ 콘솔 화면의 데이터층).
 *
 * 서버가 준 숫자를 그대로 나른다. 화면 쪽 규칙 셋은 API 문서와 같다:
 *
 * 1. 페이지 점수와 사이트 점수를 **나란히 비교하는 UI 를 만들지 않는다** — 분모가
 *    다른 두 숫자다(methodology §2.9).
 * 2. SITE 판정은 반드시 `measuredAt` 날짜와 함께 그린다 — 날짜 없이 섞으면 "이
 *    페이지의 문제" 로 잘못 읽힌다.
 * 3. 표본 밖(notSampled)은 감점이 아니다 — 서버가 준 문구(notSampledNoteKo)를
 *    그대로 단다.
 */

import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';

export interface PageRow {
  readonly url: string;
  readonly failed: readonly string[];
  readonly warned: readonly string[];
  readonly passedCount: number;
  readonly problemCount: number;
  readonly score: number | null;
  readonly scoreStatus: string | null;
}

export interface SiteCheckRow {
  readonly checkId: string;
  readonly status: string;
  readonly reasonKo: string | null;
}

export interface ScanPages {
  readonly measuredAt: string | null;
  readonly pages: readonly PageRow[];
  readonly siteChecks: readonly SiteCheckRow[];
  readonly recordedBeforePageLists: boolean;
  readonly notesKo: readonly string[];
}

export interface PageStage {
  readonly categoryId: string;
  readonly nameKo: string;
  readonly weight: number;
  readonly isGate: boolean;
  readonly score: number | null;
}

export interface PageLossRow {
  readonly checkId: string;
  readonly categoryId: string;
  readonly status: string;
  readonly lost: number;
}

export interface PageScoreDetail {
  readonly specId: string;
  readonly specVersion: string;
  readonly status: string;
  readonly score: number | null;
  readonly reach: number;
  readonly quality: number | null;
  readonly stages: readonly PageStage[];
  readonly losses: readonly PageLossRow[];
  readonly gateUnverified: readonly string[];
  readonly unmeasured: readonly string[];
  readonly notSampled: readonly string[];
  readonly notApplicable: readonly string[];
  readonly notSampledNoteKo: string;
}

export interface PageDetail {
  readonly url: string;
  readonly failed: readonly string[];
  readonly warned: readonly string[];
  readonly passed: readonly string[];
  readonly score: PageScoreDetail | null;
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function strings(value: unknown): string[] {
  return list(value).filter((item): item is string => typeof item === 'string');
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

/** 응답 → 페이지 목록. 파서를 분리해 둔 것은 시험 때문이다 — 통신 없이 검증한다. */
export function toScanPages(raw: unknown): ScanPages {
  const source = record(raw);
  return {
    measuredAt: strOrNull(source, 'measured_at'),
    pages: list(source['pages']).map((entry) => {
      const item = record(entry);
      return {
        url: str(item, 'url'),
        failed: strings(item['failed']),
        warned: strings(item['warned']),
        passedCount: num(item, 'passed_count'),
        problemCount: num(item, 'problem_count'),
        score: numOrNull(item, 'score'),
        scoreStatus: strOrNull(item, 'score_status'),
      };
    }),
    siteChecks: list(source['site_checks']).map((entry) => {
      const item = record(entry);
      return {
        checkId: str(item, 'check_id'),
        status: str(item, 'status'),
        reasonKo: strOrNull(item, 'reason_ko'),
      };
    }),
    recordedBeforePageLists: source['recorded_before_page_lists'] === true,
    notesKo: strings(source['notes_ko']),
  };
}

export function toPageDetail(raw: unknown): PageDetail {
  const source = record(raw);
  const scoreRaw = source['score'];
  const score = record(scoreRaw);
  return {
    url: str(source, 'url'),
    failed: strings(source['failed']),
    warned: strings(source['warned']),
    passed: strings(source['passed']),
    score:
      scoreRaw === null || scoreRaw === undefined
        ? null
        : {
            specId: str(score, 'spec_id'),
            specVersion: str(score, 'spec_version'),
            status: str(score, 'status'),
            score: numOrNull(score, 'score'),
            reach: num(score, 'reach'),
            quality: numOrNull(score, 'quality'),
            stages: list(score['stages']).map((entry) => {
              const item = record(entry);
              return {
                categoryId: str(item, 'category_id'),
                nameKo: str(item, 'name_ko'),
                weight: num(item, 'weight'),
                isGate: item['is_gate'] === true,
                score: numOrNull(item, 'score'),
              };
            }),
            losses: list(score['losses']).map((entry) => {
              const item = record(entry);
              return {
                checkId: str(item, 'check_id'),
                categoryId: str(item, 'category_id'),
                status: str(item, 'status'),
                lost: num(item, 'lost'),
              };
            }),
            gateUnverified: strings(score['gate_unverified']),
            unmeasured: strings(score['unmeasured']),
            notSampled: strings(score['not_sampled']),
            notApplicable: strings(score['not_applicable']),
            notSampledNoteKo: str(score, 'not_sampled_note_ko'),
          },
  };
}

export async function readScanPages(
  scanRunId: string,
): Promise<ConsoleOutcome<ScanPages>> {
  const outcome = await callConsoleApi(
    `/api/seo/scans/${encodeURIComponent(scanRunId)}/pages`,
  );
  if (!outcome.ok) return outcome;
  return { ok: true, data: toScanPages(outcome.data), meta: outcome.meta };
}

export async function readPageDetail(
  scanRunId: string,
  url: string,
): Promise<ConsoleOutcome<PageDetail>> {
  const outcome = await callConsoleApi(
    `/api/seo/scans/${encodeURIComponent(scanRunId)}/pages/detail?url=${encodeURIComponent(url)}`,
  );
  if (!outcome.ok) return outcome;
  return { ok: true, data: toPageDetail(outcome.data), meta: outcome.meta };
}

/** 검사 id → 한국어 제목. 페이지 화면이 id 를 그대로 보여주면 읽는 사람이 번역해야 한다. */
export async function readCheckTitles(): Promise<ReadonlyMap<string, string>> {
  const outcome = await callConsoleApi('/api/seo/checks');
  if (!outcome.ok) return new Map();
  const titles = new Map<string, string>();
  for (const entry of list(record(outcome.data)['checks'])) {
    const item = record(entry);
    const id = str(item, 'id');
    const title = str(item, 'title_ko');
    if (id !== '' && title !== '') {
      titles.set(id, title);
    }
  }
  return titles;
}
