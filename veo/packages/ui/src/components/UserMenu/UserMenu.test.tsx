import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserMenu } from './UserMenu';

function renderMenu(defaultOpen = false) {
  return render(
    <UserMenu
      name="이재훈"
      email="analyst@example.com"
      roleLabels={['분석가']}
      defaultOpen={defaultOpen}
      actions={<button type="button">로그아웃</button>}
    />,
  );
}

describe('UserMenu', () => {
  it('shows the signed-in name without needing to be opened', () => {
    renderMenu();
    expect(screen.getAllByText('이재훈').length).toBeGreaterThan(0);
  });

  it('uses a native disclosure so it works with the keyboard and without JavaScript', async () => {
    const user = userEvent.setup();
    const { container } = renderMenu();

    const summary = container.querySelector('summary');
    expect(summary).not.toBeNull();

    await user.tab();
    expect(document.activeElement).toBe(summary);
  });

  it('names the disclosure for assistive technology', () => {
    const { container } = renderMenu();
    expect(container.querySelector('summary')?.getAttribute('aria-label')).toContain(
      '계정',
    );
  });

  it('lists the roles as text rather than as a colour', () => {
    renderMenu(true);
    expect(screen.getByText('분석가')).toBeInTheDocument();
  });

  it('shows the email so the account is identifiable', () => {
    renderMenu(true);
    expect(screen.getByText('analyst@example.com')).toBeInTheDocument();
  });

  it('renders the caller-supplied actions, owning no sign-out logic itself', () => {
    renderMenu(true);
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument();
  });

  it('reaches every control by keyboard, in order', async () => {
    const user = userEvent.setup();
    const { container } = renderMenu(true);

    const summary = container.querySelector('summary');
    await user.tab();
    expect(document.activeElement).toBe(summary);

    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: '로그아웃' }));
  });
});
