import { cx } from '../../utils/cx';
import styles from './Skeleton.module.css';

export interface SkeletonProps {
  /** Number of placeholder lines. */
  lines?: number;
  /** Announced to assistive technology while content loads. */
  label?: string;
  variant?: 'text' | 'block';
  className?: string;
}

export function Skeleton({
  lines = 3,
  label = '불러오는 중',
  variant = 'text',
  className,
}: SkeletonProps) {
  const count = Math.max(1, Math.trunc(lines));

  return (
    <div
      className={cx(styles.skeleton, variant === 'block' && styles.block, className)}
      role="status"
      aria-busy="true"
      aria-live="polite"
    >
      <span className={styles.srOnly}>{label}</span>
      {Array.from({ length: count }, (_, index) => (
        <span
          key={index}
          className={styles.line}
          data-skeleton-line=""
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
