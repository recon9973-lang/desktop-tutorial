import type { ButtonHTMLAttributes, MouseEvent, ReactNode } from 'react';
import { cx } from '../../utils/cx';
import styles from './Button.module.css';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner and blocks interaction while work is in flight. */
  busy?: boolean;
  block?: boolean;
  children: ReactNode;
}

/**
 * `busy` deliberately does not set the `disabled` attribute.
 *
 * A button that becomes `disabled` under the reader's own focus is removed from
 * the tab order, and the browser drops focus to `<body>` — the person waiting
 * for the result is thrown to the top of the page without being told. So a busy
 * button stays focusable and announces itself with `aria-busy` + `aria-disabled`,
 * and the click is swallowed here instead. `disabled` still means disabled: a
 * control that is genuinely unavailable (no API yet, no permission) uses it.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  busy = false,
  block = false,
  type = 'button',
  disabled = false,
  className,
  onClick,
  children,
  ...rest
}: ButtonProps) {
  function handleClick(event: MouseEvent<HTMLButtonElement>) {
    if (busy) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    onClick?.(event);
  }

  return (
    <button
      {...rest}
      type={type}
      disabled={disabled}
      aria-busy={busy || undefined}
      aria-disabled={busy || undefined}
      onClick={handleClick}
      className={cx(
        styles.button,
        styles[variant],
        styles[size],
        block && styles.block,
        className,
      )}
    >
      {busy ? <span className={styles.spinner} aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
