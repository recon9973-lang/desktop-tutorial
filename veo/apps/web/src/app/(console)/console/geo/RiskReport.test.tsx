import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { GatedItem, RiskFindings } from '@/lib/observations';

import { RiskReport } from './RiskReport';

/**
 * 이 화면에서 가장 비싼 실수는 **0 을 "문제 없음" 으로 읽히게 두는 것**이다.
 *
 * 방법론이 정의한 위험은 8종인데 지금 재는 것은 1종(동명 업체 혼동)뿐이다. 목록이
 * 비었을 때 그 사실을 함께 말하지 않으면, 우리가 안 재는 것을 없다고 보고하는 셈이
 * 된다(마스터 0-A).
 */

const GAPS = [
  { kind: 'CITATION_ENTAILMENT', reason_ko: '언어모델 판정이 필요합니다.' },
  { kind: 'CLAIM_ACCURACY', reason_ko: '고객 사이트 대조가 필요합니다.' },
];

function item(over: Partial<GatedItem> = {}): GatedItem {
  return {
    assessment_id: 'a-1',
    outcome: 'EXCLUDED_NOT_MEASURED',
    explanation_ko: '자동 판정이 미확인이라 위험 지적으로 집계하지 않습니다.',
    assessment: {
      kind: 'ENTITY_DISAMBIGUATION',
      band_label_ko: '높음',
      claim_text: '온담한의원',
      automated: {
        verdict: 'UNKNOWN',
        rationale_ko: '상호가 답변에 나왔지만 같은 이름의 다른 업체와 갈리지 않았습니다.',
      },
    },
    review: { stage_label_ko: '검수 대기', is_reviewed: false },
    ...over,
  };
}

function findings(over: Partial<RiskFindings> = {}): RiskFindings {
  return {
    customer: {
      findings: [],
      withheld: { total: 0, explanation_ko: '' },
      not_measured: { total: 1, explanation_ko: '' },
    },
    internal: { items: [item()] },
    kinds_not_yet_produced: GAPS,
    ...over,
  };
}

describe('0 의 뜻', () => {
  it('건이 없어도 "아직 재지 않는 항목" 을 함께 보여준다', () => {
    render(<RiskReport findings={findings({ internal: { items: [] } })} />);

    expect(screen.getByText(/아직 재지 않는 항목 2종/)).toBeInTheDocument();
    expect(screen.getByText(/동명 업체 혼동 하나/)).toBeInTheDocument();
  });

  it('재지 않는 유형마다 이유를 적는다', () => {
    render(<RiskReport findings={findings()} />);

    expect(screen.getByText('언어모델 판정이 필요합니다.')).toBeInTheDocument();
    expect(screen.getByText('고객 사이트 대조가 필요합니다.')).toBeInTheDocument();
  });
});

describe('검수자가 보는 것', () => {
  it('기계가 실제로 본 글자를 그대로 보여준다', () => {
    // 요약하면 "백세온담한의원" 과 "온담한의원" 의 차이가 사라지고, 그 차이가 이
    // 판정의 전부다.
    render(<RiskReport findings={findings()} />);

    expect(screen.getByText(/온담한의원/)).toBeInTheDocument();
    expect(screen.getByText(/갈리지 않았습니다/)).toBeInTheDocument();
  });

  it('심각도와 검수 단계를 함께 보여준다', () => {
    render(<RiskReport findings={findings()} />);

    expect(screen.getByText('높음')).toBeInTheDocument();
    expect(screen.getByText('검수 대기')).toBeInTheDocument();
  });

  it('게이트가 왜 그렇게 판단했는지 적는다', () => {
    render(<RiskReport findings={findings()} />);

    expect(screen.getByText(/위험 지적으로 집계하지 않습니다/)).toBeInTheDocument();
  });
});

describe('종합 점수', () => {
  it('위험을 한 숫자로 접지 않는다', () => {
    // 치명 1건과 낮음 10건이 같은 값이 될 수 있고, 그 둘은 대응이 전혀 다르다.
    render(<RiskReport findings={findings()} />);

    expect(screen.getByText(/종합 점수가 없습니다/)).toBeInTheDocument();
  });
});
