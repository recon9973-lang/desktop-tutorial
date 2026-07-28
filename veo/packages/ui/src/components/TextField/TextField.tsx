'use client';

import { useId } from 'react';
import type { InputHTMLAttributes, Ref } from 'react';
import { cx } from '../../utils/cx';
import styles from './TextField.module.css';

type NativeInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'id' | 'className' | 'aria-describedby' | 'aria-invalid'
>;

export interface TextFieldProps extends NativeInputProps {
  /** Forwarded to the underlying input, so a form can move focus to it. */
  ref?: Ref<HTMLInputElement>;
  /** Always visible. A placeholder is never a substitute for a label. */
  label: string;
  name: string;
  /** Supply one to keep the id stable across renders; otherwise one is generated. */
  id?: string;
  /** Persistent guidance. Stays visible while an error is shown. */
  hint?: string;
  /** Field-level validation message. Its presence is what marks the field invalid. */
  error?: string | null;
  className?: string;
}

export function TextField({
  label,
  name,
  id,
  hint,
  error,
  required = false,
  className,
  ref,
  ...rest
}: TextFieldProps) {
  const generatedId = useId();
  const fieldId = id ?? `${generatedId}${name}`;
  const hintId = `${fieldId}-hint`;
  const errorId = `${fieldId}-error`;

  const hasHint = typeof hint === 'string' && hint.length > 0;
  const invalid = typeof error === 'string' && error.length > 0;

  // The error is announced before the hint: the correction matters more than the
  // guidance the reader has already heard once.
  const describedBy = [invalid ? errorId : null, hasHint ? hintId : null]
    .filter((value): value is string => value !== null)
    .join(' ');

  return (
    <div
      className={cx(styles.field, className)}
      data-veo-field-state={invalid ? 'invalid' : 'valid'}
    >
      <label className={styles.label} htmlFor={fieldId}>
        {label}
        {required ? <span className={styles.required}>필수</span> : null}
      </label>

      <input
        {...rest}
        ref={ref}
        id={fieldId}
        name={name}
        required={required}
        className={cx(styles.input, invalid && styles.inputInvalid)}
        aria-invalid={invalid || undefined}
        {...(describedBy === '' ? {} : { 'aria-describedby': describedBy })}
      />

      {invalid ? (
        <p className={styles.error} id={errorId}>
          <span className={styles.errorMark} aria-hidden="true">
            !
          </span>
          {error}
        </p>
      ) : null}

      {hasHint ? (
        <p className={styles.hint} id={hintId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
