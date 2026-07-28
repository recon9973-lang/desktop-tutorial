import type { ReactNode } from 'react';
import { cx } from '../../utils/cx';
import styles from './EmptyState.module.css';

/** VEO shows this instead of inventing a placeholder number. */
export const EMPTY_STATE_DEFAULT_TITLE = '아직 측정 데이터가 없습니다';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: ReactNode;
  compact?: boolean;
  className?: string;
}

export function EmptyState({
  title = EMPTY_STATE_DEFAULT_TITLE,
  description,
  action,
  compact = false,
  className,
}: EmptyStateProps) {
  return (
    <div className={cx(styles.emptyState, compact && styles.compact, className)}>
      <svg
        className={styles.icon}
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
        role="presentation"
      >
        <rect
          x="3"
          y="4"
          width="18"
          height="16"
          rx="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeDasharray="3 3"
        />
        <path
          d="M7 15.5h3M13 15.5h4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
      <p className={styles.title}>{title}</p>
      {description !== undefined ? (
        <p className={styles.description}>{description}</p>
      ) : null}
      {action !== undefined ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
