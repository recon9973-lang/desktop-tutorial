import { cx } from '../../utils/cx';
import styles from './DataSourceBadge.module.css';

/** Where a displayed value came from. Every number in VEO carries one. */
export const DATA_SOURCES = [
  'NAVER_SEARCH_AD',
  'NAVER_DATALAB',
  'CALCULATED',
  'VEO_CRAWLER',
] as const;

export type DataSourceKind = (typeof DATA_SOURCES)[number];

export const DATA_SOURCE_LABELS_KO: Readonly<Record<DataSourceKind, string>> = {
  NAVER_SEARCH_AD: '네이버 검색광고 API',
  NAVER_DATALAB: '네이버 데이터랩',
  CALCULATED: 'VEO 계산값',
  VEO_CRAWLER: 'VEO 수집기',
};

export const DATA_SOURCE_DESCRIPTIONS_KO: Readonly<Record<DataSourceKind, string>> = {
  NAVER_SEARCH_AD: '네이버 검색광고 API가 제공한 값을 그대로 표시합니다.',
  NAVER_DATALAB: '네이버 데이터랩의 상대 지수입니다. 절대 검색량이 아닙니다.',
  CALCULATED: '수집한 원본 값을 VEO 공식으로 계산한 파생 값입니다.',
  VEO_CRAWLER: 'VEO 수집기가 대상 페이지에서 직접 관측한 값입니다.',
};

/**
 * Fixed timezone so the server-rendered and client-rendered strings match.
 * VEO reports Korean market data, so KST is the reporting timezone.
 */
const COLLECTED_AT_FORMAT = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

function formatCollectedAt(iso: string): string | null {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return `${COLLECTED_AT_FORMAT.format(parsed)} KST`;
}

export interface DataSourceBadgeProps {
  source: DataSourceKind;
  /** ISO-8601 instant at which the value was collected. */
  collectedAt: string;
  className?: string;
}

export function DataSourceBadge({ source, collectedAt, className }: DataSourceBadgeProps) {
  const formatted = formatCollectedAt(collectedAt);

  return (
    <span
      className={cx(styles.badge, className)}
      data-source={source}
      title={DATA_SOURCE_DESCRIPTIONS_KO[source]}
    >
      <svg
        className={styles.icon}
        viewBox="0 0 16 16"
        aria-hidden="true"
        focusable="false"
        role="presentation"
      >
        <ellipse cx="8" cy="4" rx="5.4" ry="2.3" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path
          d="M2.6 4v8c0 1.27 2.42 2.3 5.4 2.3s5.4-1.03 5.4-2.3V4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.3"
        />
        <path
          d="M2.6 8c0 1.27 2.42 2.3 5.4 2.3s5.4-1.03 5.4-2.3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.3"
        />
      </svg>
      <span className={styles.source}>{DATA_SOURCE_LABELS_KO[source]}</span>
      <span className={styles.separator} aria-hidden="true">
        ·
      </span>
      <span className={styles.collectedLabel}>수집 시각</span>
      {formatted === null ? (
        <span className={styles.time}>확인 불가</span>
      ) : (
        <time className={styles.time} dateTime={collectedAt}>
          {formatted}
        </time>
      )}
    </span>
  );
}
