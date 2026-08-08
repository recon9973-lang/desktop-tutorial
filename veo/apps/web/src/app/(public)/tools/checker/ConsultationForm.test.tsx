/**
 * 상담 요청 폼 — 무료 진단이 영업으로 이어지는 유일한 문.
 *
 * 지키는 것 넷 —
 *
 * 1. **광고 수신 동의 칸이 없다.** 서버가 받지도 저장하지도 않는다. 화면에만 두면
 *    받은 것처럼 보이고, 그건 개인정보 안내에서 가장 나쁜 종류의 거짓이다.
 * 2. 전화·이메일 **둘 중 하나면 된다.** 둘 다 요구하면 남길 수 있는 사람이 준다.
 * 3. **무엇을 저장했는지는 우리가 적지 않는다** — 서버가 돌려준 목록을 그대로 보인다.
 * 4. 서버의 거절 문장을 우리 문장으로 갈아 끼우지 않는다.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ConsultationForm } from './ConsultationForm';

function mockFetch(response: { ok: boolean; body: unknown }): ReturnType<typeof vi.fn> {
  const impl = vi.fn(
    async () =>
      new Response(JSON.stringify(response.body), {
        status: response.ok ? 200 : 422,
        headers: { 'Content-Type': 'application/json' },
      }),
  );
  vi.stubGlobal('fetch', impl);
  return impl;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('상담 요청 폼', () => {
  it('광고 수신 동의 칸이 없다', () => {
    render(<ConsultationForm siteUrl="https://example.kr" />);

    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.getByText(/광고 수신 동의는 받지/)).toBeInTheDocument();
  });

  it('이름만 있고 연락처가 없으면 보내지 않는다', async () => {
    const spy = mockFetch({ ok: true, body: {} });
    const user = userEvent.setup();
    render(<ConsultationForm siteUrl={null} />);

    await user.type(screen.getByLabelText('이름'), '이재훈');
    await user.click(screen.getByRole('button', { name: '상담 요청' }));

    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByText(/전화번호 또는 이메일 중 하나는/)).toBeInTheDocument();
  });

  it('전화만 적어도 보낸다', async () => {
    const spy = mockFetch({ ok: true, body: { receipt: { storedFieldsKo: [] } } });
    const user = userEvent.setup();
    render(<ConsultationForm siteUrl="https://example.kr" />);

    await user.type(screen.getByLabelText('이름'), '이재훈');
    await user.type(screen.getByLabelText('전화번호'), '010-1234-5678');
    await user.click(screen.getByRole('button', { name: '상담 요청' }));

    expect(spy).toHaveBeenCalledTimes(1);
    const sent = JSON.parse(String((spy.mock.calls[0]?.[1] as RequestInit).body));
    expect(sent).toEqual({
      name: '이재훈',
      phone: '010-1234-5678',
      email: '',
      siteUrl: 'https://example.kr',
    });
  });

  it('이메일만 적어도 보낸다', async () => {
    const spy = mockFetch({ ok: true, body: { receipt: { storedFieldsKo: [] } } });
    const user = userEvent.setup();
    render(<ConsultationForm siteUrl={null} />);

    await user.type(screen.getByLabelText('이름'), '이재훈');
    await user.type(screen.getByLabelText('이메일'), 'a@example.kr');
    await user.click(screen.getByRole('button', { name: '상담 요청' }));

    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('저장한 항목은 서버가 돌려준 목록을 그대로 보인다', async () => {
    mockFetch({
      ok: true,
      body: {
        receipt: {
          storedFieldsKo: ['이름', '전화번호', '홈페이지 주소'],
          retentionNoteKo: '상담 종료 후 6개월 뒤 지웁니다.',
          consentNoteKo: '광고 수신 동의는 받지 않았습니다.',
        },
      },
    });
    const user = userEvent.setup();
    render(<ConsultationForm siteUrl="https://example.kr" />);

    await user.type(screen.getByLabelText('이름'), '이재훈');
    await user.type(screen.getByLabelText('전화번호'), '010-1234-5678');
    await user.click(screen.getByRole('button', { name: '상담 요청' }));

    expect(await screen.findByText('상담 요청이 접수되었습니다')).toBeInTheDocument();
    expect(screen.getByText('홈페이지 주소')).toBeInTheDocument();
    expect(screen.getByText('상담 종료 후 6개월 뒤 지웁니다.')).toBeInTheDocument();
    // 입력칸은 사라진다 — 두 번 보내게 두지 않는다.
    expect(screen.queryByLabelText('이름')).not.toBeInTheDocument();
  });

  it('서버의 거절 문장을 그대로 보인다', async () => {
    mockFetch({ ok: false, body: { message: '요청이 많습니다. 잠시 후 다시 시도해 주십시오.' } });
    const user = userEvent.setup();
    render(<ConsultationForm siteUrl={null} />);

    await user.type(screen.getByLabelText('이름'), '이재훈');
    await user.type(screen.getByLabelText('이메일'), 'a@example.kr');
    await user.click(screen.getByRole('button', { name: '상담 요청' }));

    expect(
      await screen.findByText('요청이 많습니다. 잠시 후 다시 시도해 주십시오.'),
    ).toBeInTheDocument();
  });
});
