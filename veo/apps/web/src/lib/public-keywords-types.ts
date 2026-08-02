/**
 * 무료 키워드 조회의 화면 계약 — 클라이언트 컴포넌트가 안전하게 임포트할 타입만.
 *
 * 값 읽기·엔진 호출은 서버 전용 `public-keywords.ts` 에 있다(scan-api 와 같은 분리).
 */

export type KeywordValueQuality =
  | 'EXACT'
  | 'ROUNDED'
  | 'RANGE'
  | 'SUPPRESSED_BY_PROVIDER'
  | 'BELOW_PROVIDER_THRESHOLD'
  | 'MISSING';

export interface KeywordFigure {
  readonly value: number | null;
  readonly quality: KeywordValueQuality;
}

export interface PublicKeywordRow {
  readonly keyword: string;
  readonly normalizedKeyword: string;
  readonly total: KeywordFigure;
  readonly pc: KeywordFigure;
  readonly mobile: KeywordFigure;
  readonly competitionLabel: string | null;
}

export interface KeywordLookupResult {
  readonly searchadState: string;
  readonly rows: readonly PublicKeywordRow[];
  readonly noticesKo: readonly string[];
  readonly scopeNoticeKo: string;
}
