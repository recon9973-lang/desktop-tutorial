import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Avatar, initialsFor } from './Avatar';

describe('initialsFor', () => {
  it('takes the first character of a Korean name', () => {
    expect(initialsFor('이재훈')).toBe('이');
  });

  it('takes the initials of a Latin two-part name', () => {
    expect(initialsFor('Ada Lovelace')).toBe('AL');
  });

  it('falls back to a neutral mark rather than inventing a name', () => {
    expect(initialsFor('')).toBe('·');
    expect(initialsFor('   ')).toBe('·');
  });
});

describe('Avatar', () => {
  it('renders the name for assistive technology, not just the initials', () => {
    render(<Avatar name="이재훈" />);
    expect(screen.getByText('이재훈')).toBeInTheDocument();
  });

  it('hides the decorative initials from the accessibility tree', () => {
    const { container } = render(<Avatar name="Ada Lovelace" />);
    const glyph = container.querySelector('[data-veo-avatar-initials]');
    expect(glyph?.textContent).toBe('AL');
    expect(glyph).toHaveAttribute('aria-hidden', 'true');
  });

  it('never renders a placeholder person when there is no name', () => {
    render(<Avatar name="" />);
    expect(screen.queryByText(/사용자|관리자|admin/i)).toBeNull();
  });
});
