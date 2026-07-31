import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { ObservationRun, Rate, VisibilityMetrics } from '@/lib/observations';

import { VisibilityReport } from './VisibilityReport';

/**
 * 백엔드가 애써 나눠 둔 것을 화면이 도로 뭉개지 않는지.
 *
 * 이 제품에서 가장 비싸게 배운 것들이 전부 **구분**이었다 — 잴 수 없었던 것과 0%,
 * 한 일과 못 한 일, 모르는 비용과 0원. 그 구분은 마지막에 화면에서 사라진다. 어느
 * 백엔드 검사도 그것을 잡지 못한다.
 */

function rate(over: Partial<Rate> = {}): Rate {
  return {
    label_ko: '언급률',
    numerator: 3,
    denominator: 5,
    value: 0.6,
    percent_text_ko: '60.0%',
    low: 0.23,
    high: 0.88,
    adequacy: 'ADEQUATE',
    is_comparison_grade: true,
    note_ko: '',
    summary_ko: '언급률: 60.0% (5회 중 3회)',
    ...over,
  };
}

function run(over: Partial<ObservationRun> = {}): ObservationRun {
  return {
    id: 'run-1',
    project_id: 'p-1',
    prompt_set_id: 'ps-1',
    status: 'SUCCEEDED',
    is_complete: true,
    engines: ['OPENAI'],
    repetitions_per_prompt: 5,
    executions_planned: 40,
    executions_attempted: 40,
    executions_valid: 40,
    executions_skipped: 0,
    stopped_reason: null,
    summary_ko: '질문 8개를 5번씩 물었습니다.',
    unpriced_calls: 0,
    total_cost_usd: 0.1234,
    started_at: null,
    finished_at: null,
    ...over,
  };
}

function metrics(over: Partial<VisibilityMetrics> = {}): VisibilityMetrics {
  return {
    answers_recorded: 40,
    answers_valid: 40,
    answers_with_visible_citations: 40,
    answers_pending_disambiguation: 0,
    mention_rate: rate(),
    citation_rate: rate({ label_ko: '인용률' }),
    prompt_coverage: rate({ label_ko: '질문 도달률' }),
    is_partial_measurement: false,
    caveats_ko: [],
    ...over,
  };
}

describe('잴 수 없었던 값과 0%', () => {
  it('측정 불가에는 퍼센트를 찍지 않는다', () => {
    render(
      <VisibilityReport
        run={run()}
        metrics={metrics({
          citation_rate: rate({
            label_ko: '인용률',
            numerator: 0,
            denominator: 0,
            value: null,
            percent_text_ko: '데이터 없음',
            low: null,
            high: null,
            adequacy: 'NO_DATA',
            is_comparison_grade: false,
            note_ko: '출처를 확인할 수 있었던 응답이 없습니다.',
            summary_ko: '인용률: 데이터 없음 (관측 실행 0회)',
          }),
        })}
      />,
    );

    expect(screen.getByText('데이터 없음')).toBeInTheDocument();
    // 0% 라고 쓰면 "쟀는데 한 번도 인용되지 않았다" 가 되고, 그것은 사이트 탓으로 읽힌다.
    expect(screen.queryByText('0.0%')).toBeNull();
    expect(screen.queryByText('0%')).toBeNull();
  });

  it('0%는 그대로 0%로 보여준다 — 이쪽은 실제로 잰 값이다', () => {
    render(
      <VisibilityReport
        run={run()}
        metrics={metrics({
          citation_rate: rate({
            label_ko: '인용률',
            numerator: 0,
            denominator: 12,
            value: 0,
            percent_text_ko: '0.0%',
          }),
        })}
      />,
    );

    expect(screen.getByText('0.0%')).toBeInTheDocument();
    expect(screen.getByText('12회 중 0회')).toBeInTheDocument();
  });

  it('두 경우를 서로 다른 모양으로 그린다', () => {
    const { container } = render(
      <VisibilityReport
        run={run()}
        metrics={metrics({
          mention_rate: rate({ value: 0, percent_text_ko: '0.0%', numerator: 0 }),
          citation_rate: rate({
            label_ko: '인용률',
            value: null,
            denominator: 0,
            numerator: 0,
            percent_text_ko: '데이터 없음',
            low: null,
            high: null,
            adequacy: 'NO_DATA',
          }),
        })}
      />,
    );

    // 같은 클래스로 그리면 화면에서 구분이 사라진다.
    const classes = [...container.querySelectorAll('p')].map((node) => node.className);
    const measured = classes.filter((name) => /rateValue(?!Unmeasured)/.test(name));
    const unmeasured = classes.filter((name) => /rateValueUnmeasured/.test(name));
    expect(measured.length).toBeGreaterThan(0);
    expect(unmeasured.length).toBeGreaterThan(0);
  });

  it('분모가 없으면 그렇다고 말한다', () => {
    render(
      <VisibilityReport
        run={run()}
        metrics={metrics({
          citation_rate: rate({
            label_ko: '인용률',
            denominator: 0,
            numerator: 0,
            value: null,
            percent_text_ko: '데이터 없음',
            adequacy: 'NO_DATA',
          }),
        })}
      />,
    );

    expect(screen.getByText('분모가 없습니다')).toBeInTheDocument();
  });
});

describe('한 일과 못 한 일', () => {
  it('건너뛴 실행을 계획·응답과 같은 자리에 같은 무게로 둔다', () => {
    render(
      <VisibilityReport
        run={run({ executions_skipped: 12, executions_valid: 28 })}
        metrics={metrics()}
      />,
    );

    // 넷이 같은 목록 안에 나란히 있어야 한다. 건너뛴 것을 따로 빼서 각주로 밀면
    // 부분 측정이 완전한 측정처럼 읽힌다.
    const labels = [...document.querySelectorAll('dt')].map((node) => node.textContent);
    expect(labels).toContain('계획한 실행');
    expect(labels).toContain('응답을 받은 실행');
    expect(labels).toContain('건너뛴 실행');
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('중단 사유를 감추지 않는다', () => {
    render(
      <VisibilityReport run={run({ stopped_reason: 'BUDGET_EXHAUSTED' })} metrics={metrics()} />,
    );

    expect(screen.getByText(/BUDGET_EXHAUSTED/)).toBeInTheDocument();
  });

  it('부분 측정이면 비율이 계획 전체에 대한 답이 아니라고 말한다', () => {
    render(<VisibilityReport run={run({ is_complete: false })} metrics={metrics()} />);

    expect(screen.getByText(/계획 전체에 대한 답이 아닙니다/)).toBeInTheDocument();
  });
});

describe('주의사항', () => {
  it('접지 않고 그대로 보여준다', () => {
    const caveat = '이번 실행의 어떤 응답에서도 출처를 확인할 수 없었습니다.';
    const { container } = render(
      <VisibilityReport run={run()} metrics={metrics({ caveats_ko: [caveat] })} />,
    );

    expect(screen.getByText(caveat)).toBeInTheDocument();
    // details/summary 로 접으면 읽히지 않는다.
    expect(container.querySelector('details')).toBeNull();
  });
});

describe('표본이 얇을 때', () => {
  it('비교 보고에 쓰지 말라고 말한다', () => {
    render(
      <VisibilityReport
        run={run()}
        metrics={metrics({
          mention_rate: rate({ denominator: 3, numerator: 2, is_comparison_grade: false }),
        })}
      />,
    );

    expect(screen.getByText(/경쟁사와 나란히 놓지/)).toBeInTheDocument();
  });

  it('신뢰구간을 함께 보여준다', () => {
    render(<VisibilityReport run={run()} metrics={metrics()} />);

    expect(screen.getAllByText(/95% 신뢰구간/).length).toBeGreaterThan(0);
  });
});

describe('비용', () => {
  it('모르는 비용을 0원으로 적지 않는다', () => {
    render(<VisibilityReport run={run({ unpriced_calls: 7 })} metrics={metrics()} />);

    expect(screen.getByText(/0원이라는 뜻이 아니라 모른다는 뜻/)).toBeInTheDocument();
  });

  it('원화로 환산하지 않는다', () => {
    const { container } = render(<VisibilityReport run={run()} metrics={metrics()} />);

    expect(container.textContent).not.toMatch(/[0-9],[0-9]{3}원/);
  });
});

describe('같은 이름 때문에 보류한 응답', () => {
  it('보류 건수를 따로 센다', () => {
    // 보류를 "언급 없음" 과 같은 칸에 두면 언급률이 왜 낮은지 알 수 없다.
    // 전자는 등록 정보를 채우면 풀리고, 후자는 노출 작업이 필요하다 — 다른 조치다.
    render(
      <VisibilityReport
        run={run()}
        metrics={metrics({ answers_pending_disambiguation: 7 })}
      />,
    );

    expect(screen.getByText('같은 이름 때문에 보류')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });
});
