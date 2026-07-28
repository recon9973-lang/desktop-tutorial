import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TextField } from './TextField';

describe('TextField', () => {
  it('associates the visible label with the control', () => {
    render(<TextField label="이메일" name="email" />);
    const input = screen.getByLabelText('이메일');
    expect(input).toBeInstanceOf(HTMLInputElement);
    expect(input).toHaveAttribute('name', 'email');
  });

  it('keeps a caller-supplied id instead of generating one', () => {
    render(<TextField id="veo-login-email" label="이메일" name="email" />);
    expect(screen.getByLabelText('이메일')).toHaveAttribute('id', 'veo-login-email');
  });

  it('generates distinct ids for two fields with the same label', () => {
    render(
      <>
        <TextField label="비밀번호" name="a" />
        <TextField label="비밀번호" name="b" />
      </>,
    );
    const [first, second] = screen.getAllByLabelText('비밀번호');
    expect(first?.id).toBeTruthy();
    expect(second?.id).toBeTruthy();
    expect(first?.id).not.toBe(second?.id);
  });

  it('points aria-describedby at the hint when there is no error', () => {
    render(<TextField label="이메일" name="email" hint="회사 계정 주소를 입력하세요." />);
    const input = screen.getByLabelText('이메일');
    const describedBy = input.getAttribute('aria-describedby');
    expect(describedBy).toBeTruthy();

    const hint = document.getElementById(describedBy ?? '');
    expect(hint?.textContent).toBe('회사 계정 주소를 입력하세요.');
    expect(input).not.toHaveAttribute('aria-invalid', 'true');
  });

  it('marks the control invalid and describes it with the error text', () => {
    render(
      <TextField
        label="이메일"
        name="email"
        hint="회사 계정 주소를 입력하세요."
        error="이메일을 입력해 주세요."
      />,
    );
    const input = screen.getByLabelText('이메일');
    expect(input).toHaveAttribute('aria-invalid', 'true');

    const ids = (input.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);
    const described = ids
      .map((id) => document.getElementById(id)?.textContent ?? '')
      .join(' ');
    expect(described).toContain('이메일을 입력해 주세요.');
    expect(described).toContain('회사 계정 주소를 입력하세요.');
  });

  it('states the error in text, never by colour alone', () => {
    const { container } = render(
      <TextField label="이메일" name="email" error="이메일을 입력해 주세요." />,
    );
    expect(screen.getByText('이메일을 입력해 주세요.')).toBeInTheDocument();
    // A non-colour marker rides along with the message.
    expect(container.querySelector('[data-veo-field-state="invalid"]')).not.toBeNull();
  });

  it('marks a required field for both sighted and assistive users', () => {
    render(<TextField label="비밀번호" name="password" required />);
    const input = screen.getByLabelText(/비밀번호/);
    expect(input).toBeRequired();
    expect(screen.getByText('필수')).toBeInTheDocument();
  });

  it('forwards input attributes such as type and autoComplete', () => {
    render(
      <TextField
        label="비밀번호"
        name="password"
        type="password"
        autoComplete="current-password"
      />,
    );
    const input = screen.getByLabelText('비밀번호');
    expect(input).toHaveAttribute('type', 'password');
    expect(input).toHaveAttribute('autocomplete', 'current-password');
  });

  it('leaves aria-describedby off entirely when there is nothing to describe', () => {
    render(<TextField label="이메일" name="email" />);
    expect(screen.getByLabelText('이메일')).not.toHaveAttribute('aria-describedby');
  });
});
