/**
 * 재측정 칸 — 이슈가 닫히는 유일한 자리.
 *
 * 화면을 눈으로 못 여는 자리라(콘솔은 로그인이 필요하다) 여기서 실제로 그려 보고
 * 확인한다. 지키는 것 넷 —
 *
 * 1. **판정을 고르는 칸이 없다.** 있으면 아무것도 안 고치고 목록만 깨끗해진다.
 *    이 시험이 그 칸이 생기는 것을 막는다.
 * 2. 재측정 대기가 **아닌** 상태에서는 진단을 고를 수 없다. 순서가 있다.
 * 3. 서버의 거부 문장을 우리 문장으로 갈아 끼우지 않는다 — 그 문장이 다음에 무엇을
 *    눌러야 하는지 알려 준다.
 * 4. 재검사 요청이 성공하면 **무엇을 다시 재는지**가 보인다.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { VerificationPanel, type SelectableScanRun } from './VerificationPanel';

const RUNS: SelectableScanRun[] = [
  { id: 'run-1', label: '2026-08-08 · https://example.kr · 120장 · 71.8점' },
  { id: 'run-2', label: '2026-08-01 · https://example.kr · 118장 · 68.2점' },
];

function mockFetch(response: { ok: boolean; status?: number; body: unknown }): typeof fetch {
  const impl = vi.fn(async () =>
    new Response(JSON.stringify(response.body), {
      status: response.status ?? (response.ok ? 200 : 409),
      headers: { 'Content-Type': 'application/json' },
    }),
  );
  vi.stubGlobal('fetch', impl);
  return impl as unknown as typeof fetch;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('재측정 칸', () => {
  it('손으로 해결로 옮기는 길이 없다는 것을 먼저 말한다', () => {
    render(<VerificationPanel issueId="i-1" state="OPEN" scanRuns={RUNS} />);
    expect(screen.getByText(/다시 재서 통과했을 때만/)).toBeInTheDocument();
  });

  it('판정을 고르는 칸이 없다', () => {
    render(<VerificationPanel issueId="i-1" state="VERIFYING" scanRuns={RUNS} />);

    // 고를 수 있는 것은 "어느 진단으로 볼 것인가" 하나뿐이다.
    expect(screen.getAllByRole('combobox')).toHaveLength(1);
    expect(screen.getByLabelText('확인에 쓸 진단')).toBeInTheDocument();
    expect(screen.queryByText(/해결로 표시/)).not.toBeInTheDocument();
  });

  it('재측정 대기가 아니면 진단을 고를 수 없고 순서를 알려 준다', () => {
    render(<VerificationPanel issueId="i-1" state="IN_PROGRESS" scanRuns={RUNS} />);

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getByText(/먼저 재검사를 요청하십시오/)).toBeInTheDocument();
  });

  it('고를 진단이 없으면 지어내지 않고 없다고 말한다', () => {
    render(<VerificationPanel issueId="i-1" state="VERIFYING" scanRuns={[]} />);

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getByText(/고를 진단이 없습니다/)).toBeInTheDocument();
  });

  it('재검사 요청이 되면 무엇을 다시 재는지 보인다', async () => {
    mockFetch({
      ok: true,
      body: {
        ok: true,
        requested: {
          request: {
            check_id: 'seo.meta.title_unique',
            target_urls: ['https://example.kr/a', 'https://example.kr/b'],
            note_ko: '이 검사 하나만 다시 봅니다.',
          },
        },
      },
    });
    const user = userEvent.setup();
    render(<VerificationPanel issueId="i-1" state="IN_PROGRESS" scanRuns={RUNS} />);

    await user.click(screen.getByRole('button', { name: '재검사 요청' }));

    expect(await screen.findByText('seo.meta.title_unique')).toBeInTheDocument();
    expect(screen.getByText('https://example.kr/a')).toBeInTheDocument();
    expect(screen.getByText('https://example.kr/b')).toBeInTheDocument();
  });

  it('서버의 거부 문장을 그대로 보인다', async () => {
    mockFetch({
      ok: false,
      status: 409,
      body: { ok: false, reason: 'CONFLICT', message: '이미 재측정 대기 상태입니다.' },
    });
    const user = userEvent.setup();
    render(<VerificationPanel issueId="i-1" state="VERIFYING" scanRuns={RUNS} />);

    await user.click(screen.getByRole('button', { name: '재검사 요청' }));

    expect(await screen.findByText('이미 재측정 대기 상태입니다.')).toBeInTheDocument();
  });

  it('판정 결과를 서버가 준 코드 그대로 보인다 — 통과가 아니면 통과라고 하지 않는다', async () => {
    mockFetch({
      ok: true,
      body: {
        ok: true,
        recorded: {
          state_label_ko: '재측정 실패(여전히 문제 있음)',
          outcome: 'STILL_FAILING',
          reason_ko: '영향 URL 40장 중 12장이 아직 실패입니다.',
        },
      },
    });
    const user = userEvent.setup();
    render(<VerificationPanel issueId="i-1" state="VERIFYING" scanRuns={RUNS} />);

    await user.click(screen.getByRole('button', { name: '이 진단으로 확인' }));

    expect(await screen.findByText(/여전히 문제 있음/)).toBeInTheDocument();
    expect(screen.getByText(/12장이 아직 실패/)).toBeInTheDocument();
  });

  it('고른 진단 번호를 그대로 보낸다', async () => {
    const spy = mockFetch({ ok: true, body: { ok: true, recorded: null } });
    const user = userEvent.setup();
    render(<VerificationPanel issueId="i-1" state="VERIFYING" scanRuns={RUNS} />);

    await user.selectOptions(screen.getByLabelText('확인에 쓸 진단'), 'run-2');
    await user.click(screen.getByRole('button', { name: '이 진단으로 확인' }));

    const call = (spy as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(JSON.parse(String((call?.[1] as RequestInit).body))).toEqual({
      issueId: 'i-1',
      step: 'result',
      scanRunId: 'run-2',
    });
  });
});
