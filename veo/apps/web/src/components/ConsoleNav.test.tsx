import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ConsoleNav, ConsoleTopbar } from './ConsoleNav';
import type { PublicConsoleIdentity } from '@/lib/session';

const ANALYST: PublicConsoleIdentity = {
  userId: 'u-1',
  organizationId: 'o-1',
  displayName: '이재훈',
  email: 'analyst@example.com',
  roles: ['ANALYST'],
  permissions: [
    'project:read',
    'scan:read',
    'observation:read',
    'keyword:read',
    'competitor:read',
    'issue:read',
    'report:read',
    'scoring_spec:read',
  ],
};

const NARROW: PublicConsoleIdentity = {
  ...ANALYST,
  displayName: '박세일',
  email: 'sales@example.com',
  roles: ['SALES_VIEWER'],
  permissions: ['report:read'],
};

describe('ConsoleNav', () => {
  it('lists every console area the identity may open', () => {
    render(<ConsoleNav identity={ANALYST} />);
    expect(screen.getByRole('link', { name: /이슈/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /리포트/ })).toBeInTheDocument();
  });

  it('hides the areas the identity may not open', () => {
    render(<ConsoleNav identity={NARROW} />);
    expect(screen.getByRole('link', { name: /리포트/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /이슈/ })).toBeNull();
    expect(screen.queryByRole('link', { name: /키워드/ })).toBeNull();
  });

  it('says so plainly when nothing is available, rather than showing an empty box', () => {
    render(<ConsoleNav identity={{ ...NARROW, permissions: [] }} />);
    expect(screen.queryAllByRole('link')).toHaveLength(0);
    expect(screen.getByText(/열람할 수 있는 메뉴가 없습니다/)).toBeInTheDocument();
  });

  it('is a labelled navigation landmark', () => {
    render(<ConsoleNav identity={ANALYST} />);
    expect(screen.getByRole('navigation', { name: '콘솔 메뉴' })).toBeInTheDocument();
  });

  it('reaches every visible link with the keyboard', async () => {
    const user = userEvent.setup();
    render(<ConsoleNav identity={NARROW} />);

    const links = screen.getAllByRole('link');
    for (const link of links) {
      await user.tab();
      expect(document.activeElement).toBe(link);
    }
  });
});

describe('ConsoleTopbar', () => {
  it('shows the real signed-in account, never a placeholder', () => {
    render(<ConsoleTopbar identity={ANALYST} />);
    expect(screen.getAllByText('이재훈').length).toBeGreaterThan(0);
    expect(screen.queryByText(/관리자로 로그인|데모|샘플/)).toBeNull();
  });

  it('translates the role into Korean', () => {
    render(<ConsoleTopbar identity={ANALYST} />);
    expect(screen.getByText('분석가')).toBeInTheDocument();
  });

  it('signs out by posting a form, so it works without JavaScript', () => {
    const { container } = render(<ConsoleTopbar identity={ANALYST} />);
    const form = container.querySelector('form');
    expect(form?.getAttribute('method')?.toLowerCase()).toBe('post');
    expect(form?.getAttribute('action')).toBe('/api/session/logout');
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument();
  });

  it('puts no access token anywhere in the rendered markup', () => {
    const { container } = render(<ConsoleTopbar identity={ANALYST} />);
    expect(container.innerHTML).not.toMatch(/token/i);
    expect(container.innerHTML).not.toMatch(/bearer/i);
  });
});
