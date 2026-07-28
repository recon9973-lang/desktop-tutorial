import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const pathname = vi.fn(() => '/console/issues');
vi.mock('next/navigation', () => ({
  usePathname: () => pathname(),
}));

const { SkipLink } = await import('./SkipLink');
const { ConsoleNav, ConsoleTopbar } = await import('./ConsoleNav');
const { SiteHeader } = await import('./SiteHeader');
const { PermissionGate } = await import('./PermissionGate');
const PublicLayout = (await import('@/app/(public)/layout')).default;
const { PUBLIC_NAV } = await import('@/lib/navigation');

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

/**
 * Structural accessibility of the page chrome.
 *
 * These assert the accessibility tree that jsdom can build: roles, names,
 * relationships, tab order. They cannot assert what the chrome looks like — a
 * focus ring, a current-page marker that is a border rather than a colour — so
 * where a fix has a visual half, the test pins the attribute the CSS hangs off
 * and `apps/web/docs/accessibility.md` records what still needs looking at.
 */

describe('SkipLink · SC 2.4.1 bypass blocks', () => {
  it('is the first thing in the tab order and points at the main landmark', async () => {
    const user = userEvent.setup();
    render(
      <>
        <SkipLink />
        <a href="/tools/seo">SEO 점검</a>
      </>,
    );

    await user.tab();
    const skip = screen.getByRole('link', { name: '본문 바로가기' });
    expect(document.activeElement).toBe(skip);
    expect(skip).toHaveAttribute('href', '#veo-main');
  });
});

describe('PublicLayout · SC 1.3.1 landmarks, SC 2.4.1', () => {
  function renderLayout() {
    return render(
      <PublicLayout>
        <h1>무료 점검 도구</h1>
      </PublicLayout>,
    );
  }

  it('provides banner, main and contentinfo landmarks', () => {
    renderLayout();
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('gives the main landmark the id and tabindex the skip link needs', () => {
    renderLayout();
    const main = screen.getByRole('main');
    expect(main).toHaveAttribute('id', 'veo-main');
    // Without tabIndex the fragment jump scrolls but leaves focus behind, so
    // the next Tab returns to the navigation the reader just skipped.
    expect(main).toHaveAttribute('tabindex', '-1');
  });

  it('names its navigation landmark', () => {
    renderLayout();
    expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toBeInTheDocument();
  });
});

describe('SiteHeader · SC 4.1.2 current page', () => {
  it('marks the link for the page being viewed', () => {
    pathname.mockReturnValue('/tools/geo');
    render(<SiteHeader />);

    const current = screen.getByRole('link', { name: 'GEO 점검' });
    expect(current).toHaveAttribute('aria-current', 'page');

    const other = screen.getByRole('link', { name: 'SEO 점검' });
    expect(other).not.toHaveAttribute('aria-current');
  });

  it('marks nothing when the reader is somewhere else entirely', () => {
    pathname.mockReturnValue('/login');
    render(<SiteHeader />);
    for (const item of PUBLIC_NAV) {
      expect(screen.getByRole('link', { name: item.label })).not.toHaveAttribute(
        'aria-current',
      );
    }
  });
});

describe('ConsoleNav · SC 4.1.2 current page, SC 1.3.1 headings', () => {
  it('marks the console area being viewed', () => {
    pathname.mockReturnValue('/console/issues');
    render(<ConsoleNav identity={ANALYST} />);

    const nav = screen.getByRole('navigation');
    const current = within(nav)
      .getAllByRole('link')
      .filter((link) => link.getAttribute('aria-current') === 'page');

    expect(current).toHaveLength(1);
    expect(current[0]).toHaveAttribute('href', '/console/issues');
  });

  it('treats a nested route as being inside its area', () => {
    pathname.mockReturnValue('/console/projects/42');
    render(<ConsoleNav identity={ANALYST} />);

    const current = screen
      .getAllByRole('link')
      .filter((link) => link.getAttribute('aria-current') === 'page');
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveAttribute('href', '/console/projects');
  });

  it('does not mark /console/scoring-versions as current from /console/scan', () => {
    pathname.mockReturnValue('/console/scoring');
    render(<ConsoleNav identity={ANALYST} />);
    expect(
      screen.queryAllByRole('link').filter((l) => l.hasAttribute('aria-current')),
    ).toHaveLength(0);
  });

  it('names the navigation landmark from its own visible label', () => {
    pathname.mockReturnValue('/console/dashboard');
    render(<ConsoleNav identity={ANALYST} />);
    expect(screen.getByRole('navigation', { name: '콘솔 메뉴' })).toBeInTheDocument();
  });

  it('puts no heading before the page h1', () => {
    pathname.mockReturnValue('/console/dashboard');
    const { container } = render(<ConsoleNav identity={ANALYST} />);
    // The sidebar sits ahead of <main> in the document, so a heading here is the
    // first one a screen reader meets — ahead of the page's own <h1>.
    expect(container.querySelectorAll('h1, h2, h3, h4, h5, h6')).toHaveLength(0);
  });
});

describe('ConsoleTopbar · SC 1.3.1', () => {
  it('is a banner landmark carrying the account menu', () => {
    pathname.mockReturnValue('/console/dashboard');
    render(<ConsoleTopbar identity={ANALYST} />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /로그아웃/ })).toBeInTheDocument();
  });
});

describe('PermissionDenied · SC 1.3.1 heading, SC 2.4.6', () => {
  it('gives the page a level-1 heading, because it replaces the whole page', () => {
    render(
      <PermissionGate identity={{ permissions: [] }} permission="issue:read">
        <p>비밀</p>
      </PermissionGate>,
    );

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('권한이 없습니다');
  });

  it('names the missing permission in text, never by colour', () => {
    render(
      <PermissionGate identity={{ permissions: [] }} permission="keyword:read">
        <p>비밀</p>
      </PermissionGate>,
    );
    expect(screen.getByText('keyword:read')).toBeInTheDocument();
  });

  it('lets an inline use drop to a lower heading level', () => {
    render(
      <PermissionGate
        identity={{ permissions: [] }}
        permission="issue:read"
        headingLevel={2}
      >
        <p>비밀</p>
      </PermissionGate>,
    );
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('권한이 없습니다');
    expect(screen.queryByRole('heading', { level: 1 })).toBeNull();
  });
});
