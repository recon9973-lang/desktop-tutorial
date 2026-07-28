import type { ReactNode } from 'react';
import { cx } from '../../utils/cx';
import styles from './ErrorState.module.css';

export interface ErrorStateProps {
  title?: string;
  description: string;
  /** Machine-readable error identifier, useful when contacting support. */
  code?: string;
  action?: ReactNode;
  className?: string;
}

export function ErrorState({
  title = '문제가 발생했습니다',
  description,
  code,
  action,
  className,
}: ErrorStateProps) {
  return (
    <div className={cx(styles.errorState, className)} role="alert">
      <svg
        className={styles.icon}
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
        role="presentation"
      >
        <path
          d="M12 3 22 20H2z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path d="M12 9.5v4.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="17" r="1.1" fill="currentColor" />
      </svg>
      <div className={styles.content}>
        <p className={styles.title}>{title}</p>
        <p className={styles.description}>{description}</p>
        {code !== undefined ? <p className={styles.code}>오류 코드: {code}</p> : null}
        {action !== undefined ? <div className={styles.action}>{action}</div> : null}
      </div>
    </div>
  );
}
