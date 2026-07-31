import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { Issue } from '@/lib/issues';

import { IssueCard } from './IssueCard';

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

/**
 * 이 카드가 절대 하지 말아야 하는 일: **수정 보고를 해결처럼 보이게 하는 것.**
 *
 * 그리고 버튼 목록을 스스로 만들지 않는 것 — 목록은 엔진의 상태 표에서 온다.
 */

function issue(over: Partial<Issue> = {}): Issue {
  return {
    id: 'i-1',
    project_id: 'p-1',
    check_id: 'seo.title.present',
    severity: 'MAJOR',
    state: 'OPEN',
    state_label_ko: '미확인',
    is_open: true,
    title_ko: '제목 태그가 없습니다',
    business_impact_ko: null,
    affected_url_count: 3,
    remediation_owner: 'DEVELOPER',
    recurrence_count: 0,
    summary_ko: '요약',
    human_transitions: [],
    ...over,
  };
}

describe('수정 보고', () => {
  it('재측정 전이라는 사실을 글자로 말한다', () => {
    render(
      <IssueCard
        issue={issue({ state: 'FIX_CLAIMED', state_label_ko: '수정했다고 보고됨(재측정 전)' })}
      />,
    );

    expect(screen.getByText(/재측정으로 확인되지 않았습니다/)).toBeInTheDocument();
  });

  it('재측정 대기도 같은 말을 붙인다', () => {
    render(<IssueCard issue={issue({ state: 'VERIFYING', state_label_ko: '재측정 대기' })} />);

    expect(screen.getByText(/재측정으로 확인되지 않았습니다/)).toBeInTheDocument();
  });

  it('열려 있는 보통 건에는 그 문장을 붙이지 않는다', () => {
    render(<IssueCard issue={issue()} />);

    expect(screen.queryByText(/재측정으로 확인되지 않았습니다/)).not.toBeInTheDocument();
  });
});

describe('할 수 있는 일', () => {
  it('엔진이 준 이동만 버튼으로 그린다', () => {
    render(
      <IssueCard
        issue={issue({
          human_transitions: [
            { to_state: 'ACKNOWLEDGED', label_ko: '확인함', reason_ko: '담당자가 확인했습니다.' },
            { to_state: 'WONT_FIX', label_ko: '조치하지 않음', reason_ko: '결정입니다.' },
          ],
        })}
      />,
    );

    expect(screen.getByRole('button', { name: '확인함' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '조치하지 않음' })).toBeInTheDocument();
    expect(screen.getAllByRole('button')).toHaveLength(2);
  });

  it('목록이 비면 버튼을 지어내지 않고 왜 없는지 말한다', () => {
    render(
      <IssueCard
        issue={issue({
          state: 'VERIFIED_RESOLVED',
          state_label_ko: '재측정으로 해결 확인',
          is_open: false,
        })}
      />,
    );

    expect(screen.queryAllByRole('button')).toHaveLength(0);
    expect(screen.getByText(/다음 변화는 재측정이 정합니다/)).toBeInTheDocument();
  });
});

describe('재발', () => {
  it('몇 번 되돌아왔는지 적는다', () => {
    render(<IssueCard issue={issue({ recurrence_count: 2 })} />);

    expect(screen.getByText(/2회 재발/)).toBeInTheDocument();
  });
});
