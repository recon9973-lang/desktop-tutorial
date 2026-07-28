import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ConsoleOutage } from './ConsoleOutage';

describe('ConsoleOutage', () => {
  it('states the outage as an outage', () => {
    render(<ConsoleOutage reason="UNAVAILABLE" />);
    expect(screen.getByText('인증 서버에 연결하지 못했습니다')).toBeInTheDocument();
  });

  it('tells an unreachable server apart from an unconfigured one', () => {
    const unreachable = render(<ConsoleOutage reason="UNAVAILABLE" />);
    const unconfigured = render(<ConsoleOutage reason="NOT_CONFIGURED" />);
    expect(unreachable.container.textContent).not.toBe(unconfigured.container.textContent);
    expect(screen.getByText('인증 서버가 연결되지 않았습니다')).toBeInTheDocument();
  });

  it('does not tell the reader to sign in again', () => {
    const { container } = render(<ConsoleOutage reason="UNAVAILABLE" />);
    const text = container.textContent ?? '';
    expect(text).toContain('비밀번호를 다시 입력할 필요는 없습니다');
    expect(screen.queryByRole('link', { name: /로그인/ })).toBeNull();
  });

  it('announces itself as an alert rather than only by colour', () => {
    render(<ConsoleOutage reason="UNAVAILABLE" />);
    expect(screen.getByRole('alert')).toHaveTextContent('인증 서버에 연결하지 못했습니다');
  });

  it('offers a way out of the dead end', () => {
    render(<ConsoleOutage reason="NOT_CONFIGURED" />);
    expect(
      screen.getByRole('link', { name: '공개 점검 도구로 돌아가기' }),
    ).toHaveAttribute('href', '/');
  });
});
