import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const replace = vi.fn();
const refresh = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, refresh, push: vi.fn() }),
}));

const { LoginForm } = await import('./LoginForm');
const { LOGIN_MESSAGES, FIELD_MESSAGES } = await import('@/lib/login-messages');

const TOKEN = 'super-secret-access-token';

function mockFetch(response: unknown, status = 200) {
  const fetchMock = vi.fn(
    async () =>
      new Response(JSON.stringify(response), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
  );
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  email = 'analyst@example.com',
  password = 'correct horse',
) {
  await user.type(screen.getByLabelText(/이메일/), email);
  await user.type(screen.getByLabelText(/비밀번호/), password);
  await user.click(screen.getByRole('button', { name: '로그인' }));
}

beforeEach(() => {
  replace.mockReset();
  refresh.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('LoginForm — structure', () => {
  it('renders labelled email and password fields', () => {
    render(<LoginForm nextPath={null} />);

    const email = screen.getByLabelText(/이메일/);
    const password = screen.getByLabelText(/비밀번호/);

    expect(email).toHaveAttribute('type', 'email');
    expect(email).toHaveAttribute('autocomplete', 'username');
    expect(password).toHaveAttribute('type', 'password');
    expect(password).toHaveAttribute('autocomplete', 'current-password');
    expect(screen.getByRole('button', { name: '로그인' })).toBeEnabled();
  });

  it('exposes a live error region from the very first render', () => {
    render(<LoginForm nextPath={null} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('이메일 → 비밀번호 → 보기 → 로그인 순서로 키보드가 닿는다', async () => {
    const user = userEvent.setup();
    render(<LoginForm nextPath={null} />);

    await user.tab();
    expect(document.activeElement).toBe(screen.getByLabelText(/이메일/));
    await user.tab();
    expect(document.activeElement).toBe(screen.getByLabelText(/비밀번호/));
    // 보기 버튼도 키보드로 닿아야 한다. 마우스로만 쓸 수 있으면 화면 낭독기나
    // 키보드만 쓰는 사람은 비밀번호를 확인할 방법이 없다.
    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: '보기' }));
    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: '로그인' }));
  });

  it('보기 버튼이 비밀번호를 글자로 바꾼다', async () => {
    const user = userEvent.setup();
    render(<LoginForm nextPath={null} />);

    const field = screen.getByLabelText(/비밀번호/);
    expect(field).toHaveAttribute('type', 'password');

    await user.click(screen.getByRole('button', { name: '보기' }));
    expect(field).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: '숨기기' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    await user.click(screen.getByRole('button', { name: '숨기기' }));
    expect(field).toHaveAttribute('type', 'password');
  });

  it('보기로 바꿔도 브라우저가 비밀번호 칸으로 알아본다', () => {
    /** `autocomplete` 를 잃으면 비밀번호 관리자가 저장을 제안하지 않는다. */
    render(<LoginForm nextPath={null} />);

    expect(screen.getByLabelText(/비밀번호/)).toHaveAttribute(
      'autocomplete',
      'current-password',
    );
  });
});

describe('LoginForm — client-side validation', () => {
  it('does not call the server when both fields are empty', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await user.click(screen.getByRole('button', { name: '로그인' }));

    expect(fetchMock).not.toHaveBeenCalled();
    // Once under the field, once in the summary at the top of the form.
    expect(screen.getAllByText(FIELD_MESSAGES.emailRequired)).toHaveLength(2);
    expect(screen.getAllByText(FIELD_MESSAGES.passwordRequired)).toHaveLength(2);
  });

  it('marks the offending field invalid for assistive technology', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await user.type(screen.getByLabelText(/비밀번호/), 'x');
    await user.click(screen.getByRole('button', { name: '로그인' }));

    expect(screen.getByLabelText(/이메일/)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText(/비밀번호/)).not.toHaveAttribute('aria-invalid', 'true');
  });

  it('rejects an address that is not an email', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user, 'not-an-email', 'correct horse');

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getAllByText(FIELD_MESSAGES.emailFormat).length).toBeGreaterThan(0);
  });

  it('moves focus to the error summary, which names every problem at once', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await user.click(screen.getByRole('button', { name: '로그인' }));

    const summary = screen.getByRole('alert');
    expect(document.activeElement).toBe(summary);

    // Focusing the first bad field would have hidden the second problem until
    // the reader fixed the first one and submitted again.
    const listed = within(summary)
      .getAllByRole('listitem')
      .map((item) => item.textContent);
    expect(listed).toEqual([
      FIELD_MESSAGES.emailRequired,
      FIELD_MESSAGES.passwordRequired,
    ]);
  });

  it('leaves the summary in front of the fields, so Tab reaches the first one', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await user.click(screen.getByRole('button', { name: '로그인' }));
    expect(document.activeElement).toBe(screen.getByRole('alert'));

    await user.tab();
    expect(document.activeElement).toBe(screen.getByLabelText(/이메일/));
  });

  it('clears the summary once the input is corrected', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await user.click(screen.getByRole('button', { name: '로그인' }));
    expect(within(screen.getByRole('alert')).getAllByRole('listitem')).toHaveLength(2);

    await fillAndSubmit(user);
    await waitFor(() =>
      expect(within(screen.getByRole('alert')).queryAllByRole('listitem')).toHaveLength(0),
    );
  });
});

describe('LoginForm — submission', () => {
  it('posts the credentials to the session route handler', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({ ok: true, redirectTo: '/console/issues' });
    render(<LoginForm nextPath="/console/issues" />);

    await fillAndSubmit(user);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/session');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({
      email: 'analyst@example.com',
      password: 'correct horse',
      next: '/console/issues',
    });
  });

  it('follows the destination the server returned', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: true, redirectTo: '/console/issues' });
    render(<LoginForm nextPath="/console/issues" />);

    await fillAndSubmit(user);

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/console/issues'));
    expect(refresh).toHaveBeenCalled();
  });

  it('blocks a second submit while one is in flight', async () => {
    const user = userEvent.setup();
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const fetchMock = vi.fn(async () => {
      await gate;
      return new Response(JSON.stringify({ ok: true, redirectTo: '/console/dashboard' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<LoginForm nextPath={null} />);
    await fillAndSubmit(user);

    const submit = screen.getByRole('button', { name: /로그인/ });
    await waitFor(() => expect(submit).toHaveAttribute('aria-busy', 'true'));
    // The button stays enabled so it keeps keyboard focus while the request is
    // in flight; the second press is swallowed rather than prevented by
    // `disabled`. What matters is that only one request goes out.
    expect(submit).toBeEnabled();
    expect(submit).toHaveAttribute('aria-disabled', 'true');
    await user.click(submit);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    release?.();
    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe('LoginForm — failure messages', () => {
  it('moves focus to the summary when the server rejects the sign-in', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: false, reason: 'INVALID_CREDENTIALS' }, 401);
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);

    // Without this the reader is left focused on a submit button that gave no
    // sign anything happened, while the message sits above, unread.
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('alert')));
    expect(screen.getByRole('alert')).toHaveTextContent(
      LOGIN_MESSAGES.INVALID_CREDENTIALS,
    );
  });

  it('shows one generic message for a rejected sign-in', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: false, reason: 'INVALID_CREDENTIALS' }, 401);
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);

    const alert = await screen.findByRole('alert');
    await waitFor(() =>
      expect(alert).toHaveTextContent(LOGIN_MESSAGES.INVALID_CREDENTIALS),
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it('never says which of the two fields was wrong', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: false, reason: 'INVALID_CREDENTIALS' }, 401);
    const { container } = render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        LOGIN_MESSAGES.INVALID_CREDENTIALS,
      ),
    );

    // Neither field is singled out, and no wording hints at account existence.
    expect(screen.getByLabelText(/이메일/)).not.toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText(/비밀번호/)).not.toHaveAttribute('aria-invalid', 'true');
    for (const oracle of [
      '등록되지 않은',
      '존재하지 않는',
      '없는 계정',
      '비밀번호가 틀',
      '가입되지 않은',
      '계정을 찾을 수 없',
    ]) {
      expect(container.textContent ?? '').not.toContain(oracle);
    }
  });

  it('produces the same message whether the account exists or the password was wrong', async () => {
    const user = userEvent.setup();

    mockFetch({ ok: false, reason: 'INVALID_CREDENTIALS' }, 401);
    const unknownAccount = render(<LoginForm nextPath={null} />);
    await fillAndSubmit(user, 'nobody@example.com', 'whatever');
    await waitFor(() =>
      expect(unknownAccount.container.textContent).toContain(
        LOGIN_MESSAGES.INVALID_CREDENTIALS,
      ),
    );
    const firstText = unknownAccount.container.textContent;
    unknownAccount.unmount();

    mockFetch({ ok: false, reason: 'INVALID_CREDENTIALS' }, 401);
    const wrongPassword = render(<LoginForm nextPath={null} />);
    await fillAndSubmit(user, 'analyst@example.com', 'wrong');
    await waitFor(() =>
      expect(wrongPassword.container.textContent).toContain(
        LOGIN_MESSAGES.INVALID_CREDENTIALS,
      ),
    );

    expect(wrongPassword.container.textContent).toBe(firstText);
  });

  it('gives lockout its own message, distinct from a bad password', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: false, reason: 'LOCKED_OUT', retryAfterSeconds: 120 }, 429);
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(LOGIN_MESSAGES.LOCKED_OUT),
    );
    expect(LOGIN_MESSAGES.LOCKED_OUT).not.toBe(LOGIN_MESSAGES.INVALID_CREDENTIALS);
  });

  it('gives a server fault its own message', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: false, reason: 'SERVER_ERROR' }, 500);
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(LOGIN_MESSAGES.SERVER_ERROR),
    );
  });

  it('says the auth server is unreachable when the request itself fails', async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      }),
    );
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(LOGIN_MESSAGES.UNAVAILABLE),
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it('falls back to the server-fault message for a reason it does not know', async () => {
    const user = userEvent.setup();
    mockFetch({ ok: false, reason: 'SOMETHING_NEW' }, 418);
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(LOGIN_MESSAGES.SERVER_ERROR),
    );
  });

  it('never signs anyone in when the response body is not the expected shape', async () => {
    const user = userEvent.setup();
    mockFetch({ unexpected: true }, 200);
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);
    await waitFor(() => expect(screen.getByRole('alert')).not.toBeEmptyDOMElement());
    expect(replace).not.toHaveBeenCalled();
  });
});

/**
 * Node 26 shadows jsdom's Web Storage, so the suite installs its own recording
 * doubles. Asserting that nothing ever called them is a stronger statement than
 * reading an empty store back: it catches a write that was later cleared too.
 */
function spyOnWebStorage() {
  const setItem = vi.fn();
  const store = {
    setItem,
    getItem: vi.fn(() => null),
    removeItem: vi.fn(),
    clear: vi.fn(),
    key: vi.fn(() => null),
    length: 0,
  };
  vi.stubGlobal('localStorage', store);
  vi.stubGlobal('sessionStorage', { ...store, setItem });
  return setItem;
}

describe('LoginForm — token handling', () => {
  it('puts no access token in the DOM even if the server sends one back', async () => {
    const user = userEvent.setup();
    const setItem = spyOnWebStorage();
    mockFetch({ ok: true, redirectTo: '/console/dashboard', accessToken: TOKEN }, 200);
    const { container } = render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user);
    await waitFor(() => expect(replace).toHaveBeenCalled());

    expect(container.innerHTML).not.toContain(TOKEN);
    expect(document.cookie).not.toContain(TOKEN);
    expect(document.cookie).toBe('');
    expect(setItem).not.toHaveBeenCalled();
    // The destination came back; the token did not travel with it.
    expect(replace).toHaveBeenCalledWith('/console/dashboard');
  });

  it('never persists the typed password anywhere', async () => {
    const user = userEvent.setup();
    const setItem = spyOnWebStorage();
    const fetchMock = mockFetch({ ok: true, redirectTo: '/console/dashboard' });
    render(<LoginForm nextPath={null} />);

    await fillAndSubmit(user, 'analyst@example.com', 'correct horse');
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    // The password lives in the request body and in the input the user typed it
    // into. It is never copied into storage, a cookie, or the URL.
    expect(setItem).not.toHaveBeenCalled();
    expect(document.cookie).toBe('');
    expect(window.location.search).not.toContain('correct horse');

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body)).password).toBe('correct horse');
  });
});
