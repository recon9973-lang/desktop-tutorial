import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { InviteForm } from './InviteForm';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));

const TOKEN = 'a-token-that-came-out-of-the-url-1234567890';
const GOOD = 'a-colleagues-own-password';

function fetchReturning(status: number, body: unknown) {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

describe('InviteForm', () => {
  beforeEach(() => {
    push.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('refuses a password below the minimum before sending anything', async () => {
    const doFetch = fetchReturning(200, { ok: true });
    vi.stubGlobal('fetch', doFetch);
    const user = userEvent.setup();

    render(<InviteForm token={TOKEN} />);
    await user.type(screen.getByLabelText('새 비밀번호'), 'short');
    await user.type(screen.getByLabelText('새 비밀번호 확인'), 'short');
    await user.click(screen.getByRole('button', { name: /비밀번호 설정/ }));

    expect(doFetch).not.toHaveBeenCalled();
    // Twice on purpose: once in the focused summary, once beside the field. A
    // screen-reader user hears every problem at submit; a sighted user sees which
    // box to fix. Matched on the error wording specifically — the field's standing
    // hint says "12자 이상" too, and counting it would make this pass even with the
    // validation removed.
    expect(await screen.findAllByText(/비밀번호는 12자 이상/)).toHaveLength(2);
  });

  it('refuses when the two entries differ', async () => {
    const doFetch = fetchReturning(200, { ok: true });
    vi.stubGlobal('fetch', doFetch);
    const user = userEvent.setup();

    render(<InviteForm token={TOKEN} />);
    await user.type(screen.getByLabelText('새 비밀번호'), GOOD);
    await user.type(screen.getByLabelText('새 비밀번호 확인'), `${GOOD}x`);
    await user.click(screen.getByRole('button', { name: /비밀번호 설정/ }));

    expect(doFetch).not.toHaveBeenCalled();
    expect(await screen.findAllByText(/서로 다릅니다/)).toHaveLength(2);
  });

  it('sends the token and the password, then names the login id', async () => {
    const doFetch = fetchReturning(200, { ok: true, email: 'seo@venom.kr' });
    vi.stubGlobal('fetch', doFetch);
    const user = userEvent.setup();

    render(<InviteForm token={TOKEN} />);
    await user.type(screen.getByLabelText('새 비밀번호'), GOOD);
    await user.type(screen.getByLabelText('새 비밀번호 확인'), GOOD);
    await user.click(screen.getByRole('button', { name: /비밀번호 설정/ }));

    await waitFor(() => expect(doFetch).toHaveBeenCalledTimes(1));
    const [url, init] = doFetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/invite');
    expect(JSON.parse(String(init.body))).toEqual({ token: TOKEN, password: GOOD });

    // 비밀번호를 정한 것은 로그인이 아니다. 여기서 세션을 주면 인증되는 경로가
    // 둘이 된다. 다만 **곧바로 로그인 화면으로 넘기지도 않는다** — 초대받은 사람은
    // 자기 아이디가 무엇인지 모르는 상태라, 넘겨 버리면 빈 이메일 칸 앞에서 멈춘다.
    expect(await screen.findByText('seo@venom.kr')).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: '로그인하러 가기' }));
    expect(push).toHaveBeenCalledWith('/login');
  });

  it('이메일을 못 받으면 담당자에게 물어보라고 한다', async () => {
    /** 지어내지 않는다. 모르면 모른다고 하고, 알 수 있는 사람을 가리킨다. */
    vi.stubGlobal('fetch', fetchReturning(200, { ok: true, email: null }));
    const user = userEvent.setup();

    render(<InviteForm token={TOKEN} />);
    await user.type(screen.getByLabelText('새 비밀번호'), GOOD);
    await user.type(screen.getByLabelText('새 비밀번호 확인'), GOOD);
    await user.click(screen.getByRole('button', { name: /비밀번호 설정/ }));

    expect(await screen.findByText(/초대한 담당자에게/)).toBeInTheDocument();
  });

  it('tells the reader to ask for a new link when the token is spent', async () => {
    vi.stubGlobal('fetch', fetchReturning(404, { ok: false, reason: 'INVALID_TOKEN' }));
    const user = userEvent.setup();

    render(<InviteForm token={TOKEN} />);
    await user.type(screen.getByLabelText('새 비밀번호'), GOOD);
    await user.type(screen.getByLabelText('새 비밀번호 확인'), GOOD);
    await user.click(screen.getByRole('button', { name: /비밀번호 설정/ }));

    expect(await screen.findByText(/새 링크를 요청/)).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it('reads an unrecognised reason as a server fault, never as a bad link', async () => {
    vi.stubGlobal('fetch', fetchReturning(500, { ok: false, reason: 'SOMETHING_NEW' }));
    const user = userEvent.setup();

    render(<InviteForm token={TOKEN} />);
    await user.type(screen.getByLabelText('새 비밀번호'), GOOD);
    await user.type(screen.getByLabelText('새 비밀번호 확인'), GOOD);
    await user.click(screen.getByRole('button', { name: /비밀번호 설정/ }));

    expect(await screen.findByText(/잠시 후 다시 시도/)).toBeInTheDocument();
  });

  it('never renders the token, which is a credential until it is spent', () => {
    vi.stubGlobal('fetch', fetchReturning(200, { ok: true }));
    const { container } = render(<InviteForm token={TOKEN} />);
    expect(container.innerHTML).not.toContain(TOKEN);
  });
});
