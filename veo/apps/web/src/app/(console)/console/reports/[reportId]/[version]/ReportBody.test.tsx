/**
 * 발행본 본문 화면.
 *
 * 이 문서는 **거래처에 나간다.** 그래서 다른 화면보다 지킬 것이 하나 더 있다 —
 * 화면과 내려받은 파일이 같은 것을 말해야 한다.
 *
 * 지키는 것 다섯 —
 *
 * 1. **값을 직접 포맷하지 않는다.** 서버가 준 `display` 를 그대로 낸다. 화면이 따로
 *    포맷하면 같은 버전이 화면과 파일에서 다르게 보인다.
 * 2. **못 잰 값을 0 처럼 그리지 않는다.** `null` 은 "못 쟀다", `0` 은 "쟀는데 없었다".
 *    정반대의 사실이라 모양이 달라야 하고, 왜 못 쟀는지가 함께 보여야 한다.
 * 3. **판정하지 못한 검사를 접지 않는다.** 빼면 문서가 실제보다 튼튼해 보인다.
 * 4. **측정 조건이 숫자와 함께 나간다.** 숫자만 남은 문서는 실제보다 세게 읽힌다.
 * 5. 독자 셋이 **각자 다른 내용**을 낸다. 하나를 셋으로 보여 주면 안 된다.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type {
  ReportAudienceView,
  ReportValue,
  ReportVersionDetail,
} from '@/lib/reports';

import { ReportBody, readAudience } from './ReportBody';

function value(over: Partial<ReportValue> = {}): ReportValue {
  return {
    display: '71.8점',
    value: 71.8,
    unit: 'point',
    status: 'MEASURED',
    status_ko: '측정됨',
    reason_ko: null,
    source: 'scan',
    ...over,
  };
}

function view(over: Partial<ReportAudienceView> = {}): ReportAudienceView {
  return {
    audience: 'executive',
    audience_ko: '경영진',
    title_ko: '경영진 요약',
    summary_ko: '색인은 되지만 대표 URL 정리가 필요합니다.',
    status_ko: null,
    metrics: [],
    top_actions: [],
    unmeasured_checks: [],
    changes_ko: [],
    reverification_ko: [],
    disclosure: {
      scope_ko: '172장 수집',
      coverage_ko: '전체 크롤',
      confidence_ko: '높음',
      measured_at_ko: '2026-08-08',
      methodology_ko: 'VEO-LAB SEO 1.9.0',
      rank_prediction_notice_ko: '이 점수는 검색 순위 예측이 아닙니다.',
      lines_ko: [],
    },
    ...over,
  };
}

function detail(over: Partial<ReportVersionDetail> = {}): ReportVersionDetail {
  return {
    report_id: 'r-1',
    version_number: 2,
    title_ko: '참사랑한의원 8월 진단',
    generated_at: '2026-08-08T05:00:00Z',
    content_hash: 'a'.repeat(64),
    measurement_window_start: null,
    measurement_window_end: null,
    disclosures_ko: [],
    views: {
      executive: view(),
      marketing: view({ audience: 'marketing', title_ko: '마케팅 요약', summary_ko: '마케팅 쪽 말' }),
      developer: view({ audience: 'developer', title_ko: '개발자 요약', summary_ko: '개발자 쪽 말' }),
    },
    ...over,
  };
}

describe('독자 고르기', () => {
  it('아는 값은 그대로 쓴다', () => {
    expect(readAudience('marketing')).toBe('marketing');
    expect(readAudience('developer')).toBe('developer');
  });

  it('모르는 값이나 빈 값은 경영진으로 본다 — 빈 화면을 내지 않는다', () => {
    expect(readAudience('아무거나')).toBe('executive');
    expect(readAudience(undefined)).toBe('executive');
  });
});

describe('발행본 본문', () => {
  it('고른 독자의 내용을 낸다 — 셋이 각자 다르다', () => {
    const { rerender } = render(<ReportBody detail={detail()} audience="executive" />);
    expect(screen.getByText('색인은 되지만 대표 URL 정리가 필요합니다.')).toBeInTheDocument();

    rerender(<ReportBody detail={detail()} audience="developer" />);
    expect(screen.getByText('개발자 쪽 말')).toBeInTheDocument();
    expect(screen.queryByText('색인은 되지만 대표 URL 정리가 필요합니다.')).not.toBeInTheDocument();
  });

  it('지금 보는 독자를 표시한다', () => {
    render(<ReportBody detail={detail()} audience="marketing" />);
    expect(screen.getByRole('link', { name: '마케팅' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: '경영진' })).not.toHaveAttribute('aria-current');
  });

  it('값을 서버가 준 표기 그대로 낸다 — 화면이 다시 포맷하지 않는다', () => {
    const one = detail({
      views: {
        ...detail().views,
        executive: view({
          metrics: [
            {
              metric_key: 'seo.score',
              label_ko: 'SEO 준비도',
              section: 'score',
              note_ko: '',
              value: value({ display: '71.8점', value: 71.8 }),
            },
          ],
        }),
      },
    });
    render(<ReportBody detail={one} audience="executive" />);

    expect(screen.getByText('71.8점')).toBeInTheDocument();
    // 화면이 반올림하거나 단위를 바꾸면 아래가 보일 것이다.
    expect(screen.queryByText('72점')).not.toBeInTheDocument();
    expect(screen.queryByText('71.8')).not.toBeInTheDocument();
  });

  it('못 잰 값과 0 을 다른 모양으로 그린다', () => {
    const one = detail({
      views: {
        ...detail().views,
        executive: view({
          metrics: [
            {
              metric_key: 'a.zero',
              label_ko: '쟀는데 0',
              section: 's',
              note_ko: '',
              value: value({ display: '0회', value: 0 }),
            },
            {
              metric_key: 'b.unknown',
              label_ko: '못 쟀다',
              section: 's',
              note_ko: '',
              value: value({
                display: '측정 불가',
                value: null,
                status: 'UNKNOWN',
                status_ko: '측정 불가',
                reason_ko: '자격증명이 없어 호출하지 못했습니다.',
              }),
            },
          ],
        }),
      },
    });
    render(<ReportBody detail={one} audience="executive" />);

    expect(screen.getByText('0회')).toHaveAttribute('data-measured', 'yes');
    expect(screen.getByText(/측정 불가/)).toHaveAttribute('data-measured', 'no');
    // 왜 못 쟀는지가 값 옆에 붙는다 — "측정 불가" 만 띄우면 고장으로 읽힌다.
    expect(screen.getByText('자격증명이 없어 호출하지 못했습니다.')).toBeInTheDocument();
  });

  it('판정하지 못한 검사를 접지 않고, 0점이 아니라고 말한다', () => {
    const one = detail({
      views: {
        ...detail().views,
        executive: view({
          unmeasured_checks: [
            {
              check_id: 'seo.sitemap.reachable',
              title_ko: '사이트맵 접근',
              status: 'UNKNOWN',
              status_ko: '측정 불가',
              reason_ko: '크롤이 상한에서 잘렸습니다.',
              domain: 'SEO',
            },
          ],
        }),
      },
    });
    render(<ReportBody detail={one} audience="executive" />);

    expect(screen.getByText('판정하지 못한 것 1개')).toBeInTheDocument();
    expect(screen.getByText(/문제가 없다는 뜻이 아니라/)).toBeInTheDocument();
    expect(screen.getByText('크롤이 상한에서 잘렸습니다.')).toBeInTheDocument();
  });

  it('측정 조건과 순위 예측 아님 고지가 함께 나간다', () => {
    render(<ReportBody detail={detail()} audience="executive" />);

    expect(screen.getByText('이 숫자를 읽는 법')).toBeInTheDocument();
    expect(screen.getByText('172장 수집')).toBeInTheDocument();
    expect(screen.getByText('이 점수는 검색 순위 예측이 아닙니다.')).toBeInTheDocument();
  });

  it('내용 해시를 보인다 — 나중에 같은 문서인지 대조할 근거다', () => {
    render(<ReportBody detail={detail()} audience="executive" />);
    expect(screen.getByText('a'.repeat(64))).toBeInTheDocument();
  });

  it('먼저 할 것이 없으면 그 칸을 아예 그리지 않는다', () => {
    render(<ReportBody detail={detail()} audience="executive" />);
    expect(screen.queryByText(/먼저 할 것/)).not.toBeInTheDocument();
  });
});
