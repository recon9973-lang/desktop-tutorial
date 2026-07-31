import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { ReviewQueueItem } from '@/lib/observations';

import { ReviewCard } from './ReviewCard';

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

/**
 * 이 화면에서 가장 비싼 실수 둘.
 *
 * 1. **인용 문장을 요약하는 것.** 검수자가 "백세온담한의원" 과 "온담한의원" 을 구별하지
 *    못하면 이 검수는 아무 의미가 없다. 그 차이가 판정의 전부다.
 * 2. **착수 없이 판정하게 두는 것.** 원문을 열어 보지 않은 확정이 고객 문서에 실린다.
 *    서버도 막지만, 서버가 막는 것을 화면이 권하면 안 된다.
 */

const REASONS = [
  { value: 'WRONG_ENTITY', label_ko: '고객이 아니라 동명의 다른 업체에 대한 내용입니다.' },
  { value: 'SPAN_MISREAD', label_ko: '원문에서 문장을 잘못 잘라내 판정했습니다.' },
];

function item(over: Partial<ReviewQueueItem> = {}): ReviewQueueItem {
  return {
    assessment_id: '11111111-1111-1111-1111-111111111111',
    kind: 'ENTITY_DISAMBIGUATION',
    band_label_ko: '높음',
    severity: 'CRITICAL',
    claim_text: '온담한의원',
    automated_verdict: 'UNKNOWN',
    automated_rationale_ko: '상호가 답변에 나왔지만 같은 이름의 다른 업체와 갈리지 않았습니다.',
    stage: 'PENDING_REVIEW',
    stage_label_ko: '검수 대기',
    is_held_by_someone: false,
    is_mine: false,
    ...over,
  };
}

describe('검수자가 보는 것', () => {
  it('기계가 잘라낸 문장을 그대로 보여준다', () => {
    render(<ReviewCard item={item()} reasons={REASONS} />);

    expect(screen.getByText(/온담한의원/)).toBeInTheDocument();
  });

  it('자동 판정이 뭐라고 했는지 계속 보여준다', () => {
    // 사람의 결론이 자동 판정을 덮지 않는다는 사실이 화면에서도 보여야 한다.
    render(<ReviewCard item={item()} reasons={REASONS} />);

    expect(screen.getByText(/자동 판정 UNKNOWN/)).toBeInTheDocument();
    expect(screen.getByText(/갈리지 않았습니다/)).toBeInTheDocument();
  });
});

describe('착수하지 않으면', () => {
  it('판정 버튼이 없다', () => {
    render(<ReviewCard item={item()} reasons={REASONS} />);

    expect(screen.getByRole('button', { name: '착수하기' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '결론 기록' })).toBeNull();
  });

  it('왜 착수해야 하는지 적는다', () => {
    render(<ReviewCard item={item()} reasons={REASONS} />);

    expect(screen.getByText(/원문을 열어 보지 않은 확정/)).toBeInTheDocument();
  });
});

describe('내가 맡은 건', () => {
  it('세 가지 결론을 고를 수 있다', () => {
    render(<ReviewCard item={item({ is_mine: true, stage: 'UNDER_REVIEW' })} reasons={REASONS} />);

    expect(screen.getByLabelText('지적이 맞습니다')).toBeInTheDocument();
    expect(screen.getByLabelText('자동 판정이 틀렸습니다')).toBeInTheDocument();
    expect(screen.getByLabelText('지금 근거로는 판단할 수 없습니다')).toBeInTheDocument();
  });

  it('판단 없이 반납할 수 있다', () => {
    render(<ReviewCard item={item({ is_mine: true })} reasons={REASONS} />);

    expect(screen.getByRole('button', { name: '판단 없이 반납' })).toBeInTheDocument();
  });
});

describe('다른 사람이 맡은 건', () => {
  it('버튼 없이 이유만 보여준다', () => {
    render(<ReviewCard item={item({ is_held_by_someone: true })} reasons={REASONS} />);

    expect(screen.getByText(/다른 검수자가 맡고 있습니다/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '착수하기' })).toBeNull();
  });

  it('누가 맡았는지는 보여주지 않는다', () => {
    // 검수 화면이 조직원 명단을 흘리는 자리가 되면 안 된다.
    const { container } = render(
      <ReviewCard item={item({ is_held_by_someone: true })} reasons={REASONS} />,
    );

    expect(container.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/);
  });
});
