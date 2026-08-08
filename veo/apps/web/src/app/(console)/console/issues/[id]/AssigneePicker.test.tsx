/**
 * 담당자 고르는 칸.
 *
 * 지키는 것 셋 —
 *
 * 1. **해제할 수 있다.** 빈 값을 잘못된 요청으로 떨어뜨리면 맡은 사람을 뗄 방법이 없다.
 * 2. 저장이 실패하면 **화면도 되돌린다.** 안 되돌리면 화면만 바뀐 채로 남고, 그 화면을
 *    보고 "맡겼다" 고 믿는다.
 * 3. 고를 사람이 없으면 지어내지 않고 없다고 말한다.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { AssigneePicker, type AssignableMember } from './AssigneePicker';

const MEMBERS: AssignableMember[] = [
  { id: 'u-1', label: '이재훈 · a@example.kr' },
  { id: 'u-2', label: '김담당 · b@example.kr' },
];

function mockFetch(ok: boolean, message?: string): ReturnType<typeof vi.fn> {
  const impl = vi.fn(
    async () =>
      new Response(JSON.stringify(ok ? { ok: true } : { ok: false, message }), {
        status: ok ? 200 : 403,
        headers: { 'Content-Type': 'application/json' },
      }),
  );
  vi.stubGlobal('fetch', impl);
  return impl;
}

function picker(): HTMLSelectElement {
  return screen.getByLabelText('이 건을 맡을 사람') as HTMLSelectElement;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('담당자 칸', () => {
  it('맡은 사람이 없으면 없음으로 보인다', () => {
    render(<AssigneePicker issueId="i-1" assignedTo={null} members={MEMBERS} />);
    expect(picker().value).toBe('');
  });

  it('이미 맡은 사람이 골라져 있다', () => {
    render(<AssigneePicker issueId="i-1" assignedTo="u-2" members={MEMBERS} />);
    expect(picker().value).toBe('u-2');
  });

  it('고르면 그 사람 번호를 보낸다', async () => {
    const spy = mockFetch(true);
    const user = userEvent.setup();
    render(<AssigneePicker issueId="i-1" assignedTo={null} members={MEMBERS} />);

    await user.selectOptions(picker(), 'u-1');

    expect(JSON.parse(String((spy.mock.calls[0]?.[1] as RequestInit).body))).toEqual({
      issueId: 'i-1',
      userId: 'u-1',
    });
  });

  it('해제는 null 로 보낸다 — 빈 문자열이 아니다', async () => {
    const spy = mockFetch(true);
    const user = userEvent.setup();
    render(<AssigneePicker issueId="i-1" assignedTo="u-1" members={MEMBERS} />);

    await user.selectOptions(picker(), '');

    expect(JSON.parse(String((spy.mock.calls[0]?.[1] as RequestInit).body))).toEqual({
      issueId: 'i-1',
      userId: null,
    });
  });

  it('저장이 실패하면 고른 값을 되돌리고 이유를 보인다', async () => {
    mockFetch(false, '담당자를 지정할 권한이 없습니다.');
    const user = userEvent.setup();
    render(<AssigneePicker issueId="i-1" assignedTo={null} members={MEMBERS} />);

    await user.selectOptions(picker(), 'u-1');

    expect(await screen.findByText('담당자를 지정할 권한이 없습니다.')).toBeInTheDocument();
    expect(picker().value).toBe('');
  });

  it('고를 사람이 없으면 없다고 말한다', () => {
    render(<AssigneePicker issueId="i-1" assignedTo={null} members={[]} />);

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getByText(/지정할 수 있는 구성원이 없습니다/)).toBeInTheDocument();
  });
});
