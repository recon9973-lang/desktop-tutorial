/**
 * 진단 폼의 작업 폴링 (P1-6) — 요청이 크롤을 붙들지 않는다.
 *
 * 1. 제출 → 작업 표 → 폴링 → 성공 시 저장된 실행으로 이동한다.
 * 2. 실패한 작업은 서버의 안전한 문장으로 보고된다.
 * 3. 소식이 끊긴 작업(is_stale)은 "실행 중"인 척하지 않는다.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
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
  // 이전 시험의 폼이 화면에 남아 있으면 다음 시험이 그것을 집는다.
  cleanup();
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

/**
 * 화면이 오지 않을 결과를 기다리게 두지 않는가.
 *
 * 2026-08-07 실측: 폴링 루프에 **탈출구가 없었다.** 서버가 답을 못 주면 `continue`
 * 뿐이라 화면은 영원히 돌았다. 죽은 작업을 "실행 중" 으로 보여주지 않겠다고
 * `is_stale` 까지 만들어 놓고, 그 신호를 받으러 가는 길이 막히면 소용이 없다.
 */
describe('물어볼 수 없을 때', () => {
  it('로그인이 풀리면 곧바로 말하고 멈춘다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' }))
      .mockResolvedValue(new Response('', { status: 401 }));
    vi.stubGlobal('fetch', fetchMock);

    render(<ScanForm siteId="s1" pollMs={1} />);
    await userEvent.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => expect(screen.getByText(/로그인이 풀렸습니다/)).toBeTruthy());
    // 401 을 한 번 받고 그만뒀다 — 계속 물어봐야 같은 답이다.
    expect(fetchMock.mock.calls.length).toBeLessThan(5);
  });

  it('연달아 실패하면 영원히 돌지 않고 그만둔다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' }))
      .mockRejectedValue(new Error('network down'));
    vi.stubGlobal('fetch', fetchMock);

    render(<ScanForm siteId="s1" pollMs={1} />);
    await userEvent.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => expect(screen.getByText(/물어볼 수 없습니다/)).toBeTruthy(), {
      timeout: 3_000,
    });
  });

  it('한 번 끊겼다가 이어지면 그대로 진행한다', async () => {
    /** 잠깐의 네트워크 끊김으로 진단을 포기하면 그것대로 문제다. */
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' }))
      .mockRejectedValueOnce(new Error('blip'))
      .mockResolvedValueOnce(
        jsonResponse({ job: { status: 'SUCCEEDED', is_stale: false, current_stage: '저장', safe_error_message: null, result_run_id: 'r9', note_ko: '' } }),
      );
    vi.stubGlobal('fetch', fetchMock);

    render(<ScanForm siteId="s1" pollMs={1} />);
    await userEvent.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => expect(push).toHaveBeenCalledWith('/console/seo?site=s1&run=r9'));
  });
});

/**
 * 소요 시간 추정은 **근거가 있을 때만** 말한다.
 *
 * 예전에는 사이트와 무관하게 120초 고정이었다. 154페이지짜리 거래처에서 화면이
 * "예상(120초)보다 오래 걸리고 있습니다" 를 띄웠고, 정상 동작이 고장으로 읽혔다.
 */
describe('남은 시간 표시', () => {
  /**
   * 응답을 **호출 순서가 아니라 요청 내용으로** 정한다.
   *
   * 순서로 정하면, 앞 시험에서 아직 안 끝난 폴링이 이 시험의 첫 응답을 먼저 집어간다.
   * 그러면 제출이 작업 표를 못 받고 곧바로 끝나 버려서, 정작 보려던 진행 표시가
   * 화면에 뜨지도 않는다.
   */
  function runningForever() {
    const fetchMock = vi.fn((_url: unknown, init?: { method?: string }) =>
      Promise.resolve(
        init?.method === 'POST'
          ? jsonResponse({ ok: true, siteId: 's1', jobId: 'j1' })
          : jsonResponse({ job: { status: 'RUNNING', is_stale: false, current_stage: null, safe_error_message: null, result_run_id: null, note_ko: '' } }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
  }

  it('지난번 페이지 수를 알면 그 근거를 밝히고 추정한다', async () => {
    runningForever();

    render(<ScanForm siteId="s1" expectedPages={154} pollMs={1} />);
    await userEvent.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => expect(screen.getByText(/154페이지 기준/)).toBeTruthy());
  });

  it('처음 재는 곳이면 숫자를 지어내지 않는다', async () => {
    runningForever();

    render(<ScanForm siteId="s1" pollMs={1} />);
    await userEvent.click(screen.getByRole('button', { name: '다시 측정' }));

    await waitFor(() => expect(screen.getByText(/페이지 수에 달렸습니다/)).toBeTruthy());
    expect(screen.queryByText(/남은 시간 약/)).toBeNull();
  });
});
