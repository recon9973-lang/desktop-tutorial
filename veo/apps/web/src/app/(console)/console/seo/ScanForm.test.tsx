/**
 * 진단 폼의 작업 폴링 (P1-6) — 요청이 크롤을 붙들지 않는다.
 *
 * 1. 제출 → 작업 표 → 폴링 → 성공 시 저장된 실행으로 이동한다.
 * 2. 실패한 작업은 서버의 안전한 문장으로 보고된다.
 * 3. 소식이 끊긴 작업(is_stale)은 "실행 중"인 척하지 않는다.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const push = vi.fn();
const refresh = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, refresh }),
}));

import { ScanForm } from './ScanForm';

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

beforeEach(() => {
  push.mockReset();
  refresh.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('작업 폴링', () => {
  it('성공한 작업은 저장된 실행으로 이동한다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' }))
      .mockResolvedValueOnce(
        jsonResponse({ job: { status: 'RUNNING', is_stale: false, current_stage: '수집·채점', safe_error_message: null, result_run_id: null, note_ko: '' } }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ job: { status: 'SUCCEEDED', is_stale: false, current_stage: '저장', safe_error_message: null, result_run_id: 'r9', note_ko: '' } }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ScanForm siteId="s1" pollMs={10} />);
    await user.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith('/console/seo?site=s1&run=r9');
    });
  });

  it('실패한 작업은 서버의 문장을 그대로 보여준다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' }))
      .mockResolvedValueOnce(
        jsonResponse({ job: { status: 'FAILED_FINAL', is_stale: false, current_stage: null, safe_error_message: '대상 사이트가 수집을 거부했습니다.', result_run_id: null, note_ko: '' } }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ScanForm siteId="s1" pollMs={10} />);
    await user.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => {
      expect(screen.getByText('대상 사이트가 수집을 거부했습니다.')).toBeInTheDocument();
    });
    expect(push).not.toHaveBeenCalled();
  });

  it('소식이 끊긴 작업은 실행 중인 척하지 않는다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' }))
      .mockResolvedValueOnce(
        jsonResponse({ job: { status: 'RUNNING', is_stale: true, current_stage: null, safe_error_message: null, result_run_id: null, note_ko: '서버가 재시작되어 진행을 알 수 없습니다.' } }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ScanForm siteId="s1" pollMs={10} />);
    await user.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => {
      expect(
        screen.getByText('서버가 재시작되어 진행을 알 수 없습니다.'),
      ).toBeInTheDocument();
    });
  });
});
