import type { ReactNode, Ref } from 'react';
import { cx } from '../../utils/cx';
import styles from './FormError.module.css';

export interface FormErrorProps {
  /** `null` keeps the live region mounted and silent, so a later message is announced. */
  message?: string | null;
  /**
   * One line per thing the reader has to fix. Rendered as a list under the
   * message so the summary says *what* is wrong, not only *that* something is.
   */
  problems?: readonly string[];
  /** Lets a field point `aria-describedby` at this region. */
  id?: string;
  /** So a form can move focus here after a failed submit. */
  ref?: Ref<HTMLDivElement>;
  className?: string;
}

/**
 * Form-level failure region, and the error summary a failed submit focuses.
 *
 * Always rendered, even when empty: a live region that appears only at the
 * moment it gains content is frequently missed by screen readers.
 *
 * `tabIndex={-1}` is permanent rather than conditional. Focus has to be moved
 * in the same commit that reveals the message, and an element that only becomes
 * focusable in that commit is a race; -1 keeps it out of the Tab order either
 * way, so nothing is added to the keyboard path.
 */
export function FormError({ message, problems, id, ref, className }: FormErrorProps) {
  const present = typeof message === 'string' && message.trim().length > 0;
  const listed = problems?.filter((problem) => problem.trim().length > 0) ?? [];

  let body: ReactNode = null;
  if (present) {
    body = (
      <>
        <span className={styles.mark} aria-hidden="true">
          !
        </span>
        <div className={styles.body}>
          <span className={styles.message}>{message}</span>
          {listed.length > 0 ? (
            <ul className={styles.problems}>
              {listed.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </>
    );
  }

  return (
    <div
      {...(id === undefined ? {} : { id })}
      ref={ref}
      role="alert"
      tabIndex={-1}
      data-veo-form-error={present ? 'present' : 'empty'}
      className={cx(styles.region, present && styles.present, className)}
    >
      {body}
    </div>
  );
}
