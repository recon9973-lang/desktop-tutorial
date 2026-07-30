import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';

/**
 * 네이버 키워드 — 엔진에서 읽어 오는 쪽.
 *
 * 이 파일에서 절대 하지 않는 것: **숫자 하나로 줄이기.**
 *
 * 엔진은 모든 수치를 `{value, quality, source, note_ko}` 로 준다. 그 네 개가 함께
 * 있어야 "3,200회" 와 "네이버가 값을 숨김" 과 "너무 적어 집계 안 됨" 이 구분된다.
 * 화면 편하자고 `number | null` 로 접으면 그 구분이 여기서 사라지고, 뒤에서 되살릴
 * 방법이 없다.
 *
 * 그리고 **검색량과 관심도 지수를 같은 타입으로 만들지 않는다.** 절대량(SearchAd)과
 * 상대지수(DataLab)는 단위가 다르다. 타입이 같으면 언젠가 같은 표에 들어간다.
 */

/** 값이 왜 그 모양인지. 0 과 "자료 없음" 은 다른 사실이다. */
export type ValueQuality =
  | 'EXACT'
  | 'ROUNDED'
  | 'RANGE'
  | 'SUPPRESSED_BY_PROVIDER'
  | 'BELOW_PROVIDER_THRESHOLD'
  | 'MISSING';

export type DataSource =
  | 'NAVER_SEARCH_AD'
  | 'NAVER_DATALAB'
  | 'NAVER_SEARCH_API'
  | 'CALCULATED'
  | 'VEO_INTERNAL';

/** 절대 건수. 맨 숫자로 오는 일이 없다. */
export interface MeasuredCount {
  readonly value: number | null;
  readonly quality: ValueQuality;
  readonly source: DataSource;
  readonly note_ko: string;
  readonly upper_bound_exclusive: number | null;
}

export interface MeasuredRatio {
  readonly value: number | null;
  readonly quality: ValueQuality;
  readonly source: DataSource;
  readonly note_ko: string;
}

export interface KeywordMetrics {
  readonly source: DataSource;
  readonly api_version: string | null;
  readonly collected_at: string;
  readonly age_seconds: number;
  readonly source_period: string | null;
  readonly cache_hit: boolean;

  readonly monthly_pc_searches: MeasuredCount;
  readonly monthly_mobile_searches: MeasuredCount;
  readonly monthly_total_searches: MeasuredCount;

  readonly avg_pc_clicks: MeasuredRatio;
  readonly avg_mobile_clicks: MeasuredRatio;
  readonly avg_pc_ctr: MeasuredRatio;
  readonly avg_mobile_ctr: MeasuredRatio;

  readonly competition_label: string | null;
  /** 네이버는 지수를 주지 않는다. 늘 `null` 이고, VEO 가 숫자를 지어내지 않는다. */
  readonly competition_index: number | null;
  readonly ad_depth: number | null;
  readonly partial_reason_ko: string | null;
}

export interface TrendPoint {
  readonly period_start: string;
  readonly relative_index: number;
}

/**
 * DataLab 관심도 추세.
 *
 * **검색 횟수가 아니다.** 필드 이름에 `count`·`searches` 가 없는 것은 의도된 것이고,
 * 화면에서도 "건" 을 붙이면 안 된다.
 */
export interface KeywordTrend {
  readonly source: DataSource;
  readonly unit: string;
  readonly note_ko: string;
  readonly time_unit: string;
  readonly device: string;
  readonly period_start: string;
  readonly period_end: string;
  readonly points: readonly TrendPoint[];
}

export interface OpportunityComponent {
  readonly name: string;
  readonly weight: number;
  readonly value: number | null;
  readonly contribution: number | null;
  readonly source: DataSource;
  readonly note_ko: string;
  readonly unavailable_reason_ko: string | null;
}

/** VEO 자체 산식. 네이버가 준 값이 아니라는 사실이 화면에 남아야 한다. */
export interface Opportunity {
  readonly source: DataSource;
  readonly formula_version: string;
  readonly score: number | null;
  readonly coverage: number;
  readonly freshness: number;
  readonly confidence: number;
  readonly components: readonly OpportunityComponent[];
  readonly missing_components: readonly string[];
  readonly disclosure_ko: string;
  readonly unavailable_reason_ko: string | null;
}

export interface RelatedKeyword {
  readonly seed_keyword: string;
  readonly related_keyword: string;
  readonly source: DataSource;
  readonly source_rank: number | null;
  readonly monthly_total_searches: MeasuredCount;
}

export interface KeywordSnapshot {
  readonly original_keyword: string;
  readonly normalized_keyword: string;
  readonly metrics: KeywordMetrics | null;
  readonly trend: KeywordTrend | null;
  readonly opportunity: Opportunity | null;
  readonly related: readonly RelatedKeyword[];
}

/** 쓸 수 없는 공급자도 이유와 함께 돌려준다 — 빼면 "여기 있는 게 전부" 로 읽힌다. */
export interface ProviderBadge {
  readonly provider: string;
  readonly state: string;
  readonly reason_ko: string;
}

export interface KeywordLookup {
  readonly query_id: string | null;
  readonly project_id: string | null;
  readonly requested_at: string;
  readonly locale: string;
  readonly providers: readonly ProviderBadge[];
  readonly keywords: readonly KeywordSnapshot[];
  readonly notices_ko: readonly string[];
}

export interface RecentKeywords {
  readonly title_ko: string;
  readonly source: DataSource;
  readonly window_hours: number;
  readonly period_start: string;
  readonly period_end: string;
  readonly entries: readonly {
    readonly normalized_keyword: string;
    readonly lookup_count: number;
    readonly last_requested_at: string;
  }[];
  readonly disclosure_ko?: string;
}

/** 조회는 네이버를 실제로 부른다. 목록 조회와 시간 감각이 다르다. */
export async function lookUpKeywords(
  keywords: readonly string[],
): Promise<ConsoleOutcome<KeywordLookup>> {
  return callConsoleApi('/api/keywords/lookups', {
    method: 'POST',
    body: { keywords },
    timeoutMs: 60_000,
  });
}

export async function readRecentKeywords(): Promise<ConsoleOutcome<RecentKeywords>> {
  return callConsoleApi('/api/keywords/recent');
}
