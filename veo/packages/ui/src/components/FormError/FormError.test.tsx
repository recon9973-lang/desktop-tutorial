import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FormError } from './FormError';

describe('FormError', () => {
  it('announces its message through a live alert region', () => {
    render(<FormError message="이메일 또는 비밀번호가 올바르지 않습니다." />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('이메일 또는 비밀번호가 올바르지 않습니다.');
  });

  it('renders the alert region even while empty so screen readers announce a later message', () => {
    render(<FormError message={null} />);
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toBe('');
  });

  it('carries a text icon so the failure is not signalled by colour alone', () => {
    const { container } = render(<FormError message="서버에 연결할 수 없습니다." />);
    expect(container.querySelector('[data-veo-form-error="present"]')).not.toBeNull();
    expect(screen.getByRole('alert').textContent).toContain('서버에 연결할 수 없습니다.');
  });

  it('keeps a caller id so a field can point aria-describedby at it', () => {
    render(<FormError id="veo-login-error" message="확인이 필요합니다." />);
    expect(screen.getByRole('alert')).toHaveAttribute('id', 'veo-login-error');
  });
});
