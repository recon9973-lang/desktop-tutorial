import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { KeywordLookup, KeywordSnapshot, MeasuredCount } from '@/lib/keywords';

import { KeywordReport } from './KeywordReport';

/**
 * 이 화면에서 가장 비싼 실수는 **단위를 섞는 것**이다.
 *
 * 검색광고가 주는 것은 월간 검색 **건수**(절대량)이고, 데이터랩이 주는 것은 상대
 * **관심도 지수**다. 지수는 기간 최댓값을 100 으로 놓은 비율이라 "건" 이 아니다.
 * 나란히 놓으면 광고주는 같은 단위로 읽고, "이 달에 87건 검색됐다" 같은 없는 사실이
 * 만들어진다. 마스터 §8 원칙 7 이 금지하는 것이 정확히 이것이다.
 */

function count(over: Partial<MeasuredCount> = {}): MeasuredCount {
  return {
    value: 3200,
    quality: 'EXACT',
    source: 'NAVER_SEARCH_AD',
    note_ko: '',
    upper_bound_exclusive: null,
    ...over,
  };
}

function snapshot(over: Partial<KeywordSnapshot> = {}): KeywordSnapshot {
  return {
    original_keyword: '강남 한의원',
    normalized_keyword: '강남한의원',
    metrics: {
      source: 'NAVER_SEARCH_AD',
      api_version: 'v1',
      collected_at: '2026-07-31T04:00:00+09:00',
      age_seconds: 60,
      source_period: '2026-06',
      cache_hit: false,
      monthly_pc_searches: count({ value: 1200 }),
      monthly_mobile_searches: count({ value: 2000 }),
      monthly_total_searches: count({ value: 3200 }),
      avg_pc_clicks: { value: 2.4, quality: 'EXACT', source: 'NAVER_SEARCH_AD', note_ko: '' },
      avg_mobile_clicks: { value: 8.1, quality: 'EXACT', source: 'NAVER_SEARCH_AD', note_ko: '' },
      avg_pc_ctr: { value: 0.42, quality: 'EXACT', source: 'NAVER_SEARCH_AD', note_ko: '' },
      avg_mobile_ctr: { value: 0.63, quality: 'EXACT', source: 'NAVER_SEARCH_AD', note_ko: '' },
      competition_label: '높음',
      competition_index: null,
      ad_depth: 5,
      partial_reason_ko: null,
    },
    trend: null,
    opportunity: null,
    related: [],
    ...over,
  };
}

function lookup(over: Partial<KeywordLookup> = {}): KeywordLookup {
  return {
    query_id: 'q-1',
    project_id: null,
    requested_at: '2026-07-31T04:00:00+09:00',
    locale: 'ko-KR',
    providers: [],
    keywords: [snapshot()],
    notices_ko: [],
    ...over,
  };
}

const TREND = {
  source: 'NAVER_DATALAB' as const,
  unit: '상대 지수',
  note_ko: '기간 내 최댓값을 100으로 둔 상대값입니다.',
  time_unit: 'month',
  device: 'ALL',
  period_start: '2026-01-01',
  period_end: '2026-06-30',
  points: [
    { period_start: '2026-05-01', relative_index: 62.5 },
    { period_start: '2026-06-01', relative_index: 87.3 },
  ],
};

describe('검색 건수와 관심도 지수', () => {
  it('지수 옆에 "검색 횟수가 아니다" 를 붙인다', () => {
    render(<KeywordReport lookup={lookup({ keywords: [snapshot({ trend: TREND })] })} />);

    expect(screen.getByText(/검색 횟수가 아닙니다/)).toBeInTheDocument();
    expect(screen.getByText(/단위가 다릅니다/)).toBeInTheDocument();
  });

  it('지수에 "회" 를 붙이지 않는다', () => {
    const { container } = render(
      <KeywordReport lookup={lookup({ keywords: [snapshot({ trend: TREND })] })} />,
    );

    // 87.3 은 지수다. "87.3회" 가 되면 그 순간 건수로 읽힌다.
    expect(container.textContent).not.toContain('87.3회');
    expect(screen.getByText(/87\.3/)).toBeInTheDocument();
  });

  it('건수에는 "회" 를 붙인다', () => {
    render(<KeywordReport lookup={lookup()} />);

    expect(screen.getByText('3,200회')).toBeInTheDocument();
  });

  it('두 구역을 서로 다른 영역으로 갈라 놓는다', () => {
    render(<KeywordReport lookup={lookup({ keywords: [snapshot({ trend: TREND })] })} />);

    // 같은 목록에 섞이면 눈으로 구분할 방법이 없다.
    expect(screen.getByLabelText('월간 검색 건수')).toBeInTheDocument();
    expect(screen.getByLabelText('관심도 추세')).toBeInTheDocument();
  });
});

describe('값이 없을 때', () => {
  it('네이버가 숨긴 값을 0 으로 적지 않는다', () => {
    render(
      <KeywordReport
        lookup={lookup({
          keywords: [
            snapshot({
              metrics: {
                ...snapshot().metrics!,
                monthly_total_searches: count({
                  value: null,
                  quality: 'SUPPRESSED_BY_PROVIDER',
                }),
              },
            }),
          ],
        })}
      />,
    );

    expect(screen.getByText('네이버가 값을 공개하지 않음')).toBeInTheDocument();
    expect(screen.queryByText('0회')).toBeNull();
  });

  it('너무 적어 집계 안 된 것과 자료 없음을 구분한다', () => {
    render(
      <KeywordReport
        lookup={lookup({
          keywords: [
            snapshot({
              metrics: {
                ...snapshot().metrics!,
                monthly_pc_searches: count({
                  value: null,
                  quality: 'BELOW_PROVIDER_THRESHOLD',
                }),
                monthly_mobile_searches: count({ value: null, quality: 'MISSING' }),
              },
            }),
          ],
        })}
      />,
    );

    expect(screen.getByText('너무 적어 집계되지 않음')).toBeInTheDocument();
    expect(screen.getByText('자료 없음')).toBeInTheDocument();
  });
});

describe('경쟁 정도', () => {
  it('네이버가 주지 않는 0~100 지수를 만들어 내지 않는다', () => {
    render(<KeywordReport lookup={lookup()} />);

    expect(screen.getByText(/0~100 지수는 만들지 않습니다/)).toBeInTheDocument();
  });
});

describe('기회 점수', () => {
  const OPPORTUNITY = {
    source: 'CALCULATED' as const,
    formula_version: '1.0.0',
    score: 62.5,
    coverage: 0.8,
    freshness: 1,
    confidence: 0.8,
    components: [],
    missing_components: ['content_gap'],
    disclosure_ko: 'VEO가 자체 산식으로 계산한 값입니다.',
    unavailable_reason_ko: null,
  };

  it('네이버 값이 아니라 VEO 산식임을 밝힌다', () => {
    render(<KeywordReport lookup={lookup({ keywords: [snapshot({ opportunity: OPPORTUNITY })] })} />);

    expect(screen.getByText(/VEO 자체 산식 1\.0\.0/)).toBeInTheDocument();
    expect(screen.getByText(/VEO가 자체 산식으로 계산한 값입니다/)).toBeInTheDocument();
  });

  it('빠진 요소를 감추지 않는다', () => {
    render(<KeywordReport lookup={lookup({ keywords: [snapshot({ opportunity: OPPORTUNITY })] })} />);

    expect(screen.getByText(/빠진 요소: content_gap/)).toBeInTheDocument();
  });

  it('계산 못 했으면 0 점이라고 적지 않는다', () => {
    render(
      <KeywordReport
        lookup={lookup({
          keywords: [
            snapshot({
              opportunity: {
                ...OPPORTUNITY,
                score: null,
                unavailable_reason_ko: '검색량 자료가 없어 계산하지 못했습니다.',
              },
            }),
          ],
        })}
      />,
    );

    expect(screen.getByText('검색량 자료가 없어 계산하지 못했습니다.')).toBeInTheDocument();
    expect(screen.queryByText('0.0')).toBeNull();
  });
});

describe('공급자 상태', () => {
  it('쓸 수 없는 공급자도 이유와 함께 보여준다', () => {
    render(
      <KeywordReport
        lookup={lookup({
          providers: [
            {
              provider: 'NAVER_DATALAB',
              state: 'DISABLED_NO_CREDENTIAL',
              reason_ko: '자격증명이 없어 조회하지 않았습니다.',
            },
          ],
        })}
      />,
    );

    expect(screen.getByText(/네이버 데이터랩/)).toBeInTheDocument();
    expect(screen.getByText('자격증명이 없어 조회하지 않았습니다.')).toBeInTheDocument();
  });
});
