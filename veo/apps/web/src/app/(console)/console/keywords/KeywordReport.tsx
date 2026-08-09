'use client';

import { Card, formatPercent, formatScore } from '@veo/ui';

import type {
  KeywordLookup,
  KeywordSnapshot,
  KeywordTrend,
  MeasuredCount,
  MeasuredRatio,
  Opportunity,
} from '@/lib/keywords';

import styles from './keywords.module.css';

/**
 * 키워드 조회 결과.
 *
 * ## 이 화면이 절대 하지 않는 것
 *
 * **검색량과 관심도 지수를 같은 표에 넣지 않는다.**
 *
 * 네이버 검색광고가 주는 것은 **월간 검색 건수**(절대량)이고, 데이터랩이 주는 것은
 * **상대 관심도 지수**다. 지수는 그 기간의 최댓값을 100 으로 놓은 비율이라 "건" 이
 * 아니다. 두 숫자를 나란히 놓으면 읽는 사람은 같은 단위로 이해하고, 그 순간 "이 달에
 * 87건 검색됐다" 같은 없는 사실이 만들어진다. 마스터 §8 원칙 7 이 금지하는 것이 정확히
 * 이것이라 여기서는 **구역 자체를 갈라 놓았다.**
 *
 * ## 숫자가 없을 때
 *
 * 엔진은 모든 수치를 `{value, quality, note_ko}` 로 준다. `value` 가 없으면 0 이 아니라
 * **왜 없는지**를 그 자리에 쓴다 — 네이버가 값을 숨겼는지, 너무 적어 집계가 안 됐는지,
 * 아예 못 받았는지는 광고주에게 서로 다른 이야기다.
 */
export function KeywordReport({ lookup }: { readonly lookup: KeywordLookup }) {
  return (
    <div className={styles.report}>
      {lookup.notices_ko.length > 0 ? (
        <section className={styles.notices} aria-label="함께 알아야 하는 것">
          <ul className={styles.noticeList}>
            {lookup.notices_ko.map((notice) => (
              <li key={notice}>{notice}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <Providers lookup={lookup} />

      {lookup.keywords.map((snapshot) => (
        <KeywordCard key={snapshot.normalized_keyword} snapshot={snapshot} />
      ))}
    </div>
  );
}

/** 쓸 수 없는 공급자도 이유와 함께 보여준다. 빼면 "여기 있는 게 전부" 로 읽힌다. */
function Providers({ lookup }: { readonly lookup: KeywordLookup }) {
  if (lookup.providers.length === 0) return null;
  return (
    <Card title="자료 출처" headingLevel={3} tone="flat">
      <ul className={styles.providerList}>
        {lookup.providers.map((provider) => (
          <li key={provider.provider} className={styles.providerRow}>
            <span className={styles.providerName}>{PROVIDER_LABELS[provider.provider] ?? provider.provider}</span>
            <span className={styles.providerNote}>{provider.reason_ko}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

const PROVIDER_LABELS: Record<string, string> = {
  NAVER_SEARCH_AD: '네이버 검색광고 (검색 건수)',
  NAVER_DATALAB: '네이버 데이터랩 (관심도 지수)',
};

function KeywordCard({ snapshot }: { readonly snapshot: KeywordSnapshot }) {
  return (
    <Card title={snapshot.original_keyword} headingLevel={3}>
      {snapshot.metrics === null ? (
        <p className={styles.absent}>
          검색 건수를 받지 못했습니다. 위 자료 출처에서 검색광고 상태를 확인해 주십시오.
        </p>
      ) : (
        <section aria-label="월간 검색 건수">
          <p className={styles.sectionLabel}>
            월간 검색 건수 <span className={styles.badge}>네이버 검색광고</span>
          </p>
          <dl className={styles.counts}>
            <Count label="합계" measured={snapshot.metrics.monthly_total_searches} />
            <Count label="PC" measured={snapshot.metrics.monthly_pc_searches} />
            <Count label="모바일" measured={snapshot.metrics.monthly_mobile_searches} />
          </dl>

          <dl className={styles.counts}>
            <Ratio label="PC 평균 클릭" measured={snapshot.metrics.avg_pc_clicks} />
            <Ratio label="모바일 평균 클릭" measured={snapshot.metrics.avg_mobile_clicks} />
            <Ratio label="PC 클릭률" measured={snapshot.metrics.avg_pc_ctr} percent />
            <Ratio label="모바일 클릭률" measured={snapshot.metrics.avg_mobile_ctr} percent />
          </dl>

          <p className={styles.meta}>
            경쟁 정도 {snapshot.metrics.competition_label ?? '자료 없음'}
            {snapshot.metrics.ad_depth === null
              ? ''
              : ` · 광고 노출 ${snapshot.metrics.ad_depth}`}
            {' · 기준 '}
            {new Date(snapshot.metrics.collected_at).toLocaleString('ko-KR')}
            {snapshot.metrics.cache_hit ? ' (저장된 값)' : ''}
          </p>
          {/* 네이버는 0-100 경쟁 지수를 주지 않는다. 빈 눈금을 그리면 있는 것처럼 보인다. */}
          <p className={styles.meta}>
            경쟁 정도는 네이버가 라벨로만 제공합니다. 0~100 지수는 만들지 않습니다.
          </p>
          {snapshot.metrics.partial_reason_ko === null ? null : (
            <p className={styles.warning}>{snapshot.metrics.partial_reason_ko}</p>
          )}
        </section>
      )}

      {snapshot.trend === null ? null : <Trend trend={snapshot.trend} />}
      {snapshot.opportunity === null ? null : <Chance opportunity={snapshot.opportunity} />}

      {snapshot.related.length === 0 ? null : (
        <section aria-label="연관 키워드">
          <p className={styles.sectionLabel}>연관 키워드</p>
          <ul className={styles.relatedList}>
            {snapshot.related.map((one) => (
              <li key={one.related_keyword} className={styles.relatedRow}>
                <span>{one.related_keyword}</span>
                <span className={styles.relatedCount}>
                  {countText(one.monthly_total_searches)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Card>
  );
}

/**
 * 관심도 추세 — **검색 건수와 다른 구역에 둔다.**
 *
 * 단위를 매번 적는다. "87" 만 크게 띄우면 87건으로 읽힌다.
 */
function Trend({ trend }: { readonly trend: KeywordTrend }) {
  const latest = trend.points.at(-1);
  return (
    <section className={styles.trend} aria-label="관심도 추세">
      <p className={styles.sectionLabel}>
        관심도 추세 <span className={styles.badgeAlt}>네이버 데이터랩</span>
      </p>
      <p className={styles.trendNote}>{trend.note_ko}</p>
      {latest === undefined ? (
        <p className={styles.absent}>추세 자료를 받지 못했습니다.</p>
      ) : (
        <p className={styles.meta}>
          {trend.period_start} ~ {trend.period_end} · 마지막 지점{' '}
          <strong>{formatScore(latest.relative_index)}</strong> ({trend.unit})
        </p>
      )}
      <p className={styles.warning}>
        이 값은 <strong>검색 횟수가 아닙니다.</strong> 기간 안에서 가장 높았던 때를 기준으로
        한 상대적인 관심도이며, 위의 월간 검색 건수와 단위가 다릅니다.
      </p>
    </section>
  );
}

/** 기회 점수 — 네이버가 준 값이 아니라 VEO 가 계산한 값이다. */
function Chance({ opportunity }: { readonly opportunity: Opportunity }) {
  return (
    <section className={styles.chance} aria-label="기회 점수">
      <p className={styles.sectionLabel}>
        기회 점수 <span className={styles.badgeOwn}>VEO 자체 산식 {opportunity.formula_version}</span>
      </p>
      {opportunity.score === null ? (
        <p className={styles.absent}>
          {opportunity.unavailable_reason_ko ?? '계산에 필요한 자료가 부족합니다.'}
        </p>
      ) : (
        <p className={styles.chanceScore}>{formatScore(opportunity.score)}</p>
      )}
      <p className={styles.meta}>
        자료 충족 {formatPercent(opportunity.coverage)} · 최신성{' '}
        {formatPercent(opportunity.freshness)} · 신뢰도{' '}
        {formatPercent(opportunity.confidence)}
      </p>
      {opportunity.missing_components.length === 0 ? null : (
        <p className={styles.warning}>
          빠진 요소: {opportunity.missing_components.join(', ')} — 그만큼 이 점수는 덜 재고
          계산한 값입니다.
        </p>
      )}
      <p className={styles.disclosure}>{opportunity.disclosure_ko}</p>
    </section>
  );
}

function Count({ label, measured }: { readonly label: string; readonly measured: MeasuredCount }) {
  const missing = measured.value === null;
  return (
    <div className={styles.count}>
      <dt className={styles.countLabel}>{label}</dt>
      <dd className={missing ? styles.countAbsent : styles.countValue}>
        {countText(measured)}
      </dd>
      {measured.note_ko === '' ? null : <dd className={styles.countNote}>{measured.note_ko}</dd>}
    </div>
  );
}

function Ratio({
  label,
  measured,
  percent = false,
}: {
  readonly label: string;
  readonly measured: MeasuredRatio;
  readonly percent?: boolean;
}) {
  const missing = measured.value === null;
  return (
    <div className={styles.count}>
      <dt className={styles.countLabel}>{label}</dt>
      <dd className={missing ? styles.countAbsent : styles.countValue}>
        {missing
          ? qualityText(measured.quality)
          : percent
            ? `${formatScore(measured.value)}%`
            : formatScore(measured.value)}
      </dd>
    </div>
  );
}

/** 값이 없으면 0 이 아니라 **왜 없는지**를 쓴다. */
const QUALITY_TEXT: Record<string, string> = {
  SUPPRESSED_BY_PROVIDER: '네이버가 값을 공개하지 않음',
  BELOW_PROVIDER_THRESHOLD: '너무 적어 집계되지 않음',
  MISSING: '자료 없음',
  RANGE: '범위로만 제공',
};

function qualityText(quality: string): string {
  return QUALITY_TEXT[quality] ?? '자료 없음';
}

function countText(measured: MeasuredCount): string {
  if (measured.value === null) return qualityText(measured.quality);
  const formatted = measured.value.toLocaleString('ko-KR');
  if (measured.quality === 'RANGE' && measured.upper_bound_exclusive !== null) {
    return `${formatted}~${(measured.upper_bound_exclusive - 1).toLocaleString('ko-KR')}회`;
  }
  if (measured.quality === 'ROUNDED') return `약 ${formatted}회`;
  return `${formatted}회`;
}
