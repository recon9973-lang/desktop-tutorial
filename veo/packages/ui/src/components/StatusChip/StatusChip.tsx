import { cx } from '../../utils/cx';
import styles from './StatusChip.module.css';

/** The five check states VEO reports. Order is stable and part of the contract. */
export const CHECK_STATUSES = [
  'PASS',
  'WARNING',
  'FAIL',
  'NOT_APPLICABLE',
  'UNKNOWN',
] as const;

export type CheckStatus = (typeof CHECK_STATUSES)[number];

/** Tone is a semantic bucket, never a colour. NOT_APPLICABLE is neutral, not a failure. */
export type StatusTone = 'positive' | 'caution' | 'danger' | 'neutral' | 'unknown';

/** Shape name for the non-colour indicator. Unique per state. */
export type StatusShape = 'check' | 'triangle' | 'cross' | 'dash' | 'query';

interface StatusDescriptor {
  readonly label: string;
  readonly tone: StatusTone;
  readonly shape: StatusShape;
  readonly className: string | undefined;
  readonly meaning: string;
}

export const CHECK_STATUS_DESCRIPTORS: Readonly<Record<CheckStatus, StatusDescriptor>> = {
  PASS: {
    label: '통과',
    tone: 'positive',
    shape: 'check',
    className: styles.pass,
    meaning: '기준을 충족했습니다.',
  },
  WARNING: {
    label: '주의',
    tone: 'caution',
    shape: 'triangle',
    className: styles.warning,
    meaning: '부분적으로만 충족했습니다.',
  },
  FAIL: {
    label: '실패',
    tone: 'danger',
    shape: 'cross',
    className: styles.fail,
    meaning: '기준을 충족하지 못했습니다.',
  },
  NOT_APPLICABLE: {
    label: '해당 없음',
    tone: 'neutral',
    shape: 'dash',
    className: styles.neutral,
    meaning: '이 페이지에는 적용되지 않는 항목이라 채점에서 제외됩니다.',
  },
  UNKNOWN: {
    label: '측정 불가',
    tone: 'unknown',
    shape: 'query',
    className: styles.unknown,
    meaning: '판정에 필요한 근거를 수집하지 못했습니다.',
  },
};

export const CHECK_STATUS_LABELS_KO: Readonly<Record<CheckStatus, string>> = {
  PASS: CHECK_STATUS_DESCRIPTORS.PASS.label,
  WARNING: CHECK_STATUS_DESCRIPTORS.WARNING.label,
  FAIL: CHECK_STATUS_DESCRIPTORS.FAIL.label,
  NOT_APPLICABLE: CHECK_STATUS_DESCRIPTORS.NOT_APPLICABLE.label,
  UNKNOWN: CHECK_STATUS_DESCRIPTORS.UNKNOWN.label,
};

function StatusIcon({ shape }: { shape: StatusShape }) {
  const common = {
    className: styles.icon,
    viewBox: '0 0 16 16',
    'data-shape': shape,
    'aria-hidden': true,
    focusable: false,
    role: 'presentation',
  } as const;

  switch (shape) {
    case 'check':
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M4.5 8.3 6.9 10.7 11.6 5.6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'triangle':
      return (
        <svg {...common}>
          <path
            d="M8 1.6 15 14.2H1z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path d="M8 5.9v3.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <circle cx="8" cy="11.7" r="0.95" fill="currentColor" />
        </svg>
      );
    case 'cross':
      return (
        <svg {...common}>
          <rect
            x="1"
            y="1"
            width="14"
            height="14"
            rx="2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path
            d="M5 5l6 6M11 5l-6 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'dash':
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <path d="M4.6 8h6.8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      );
    case 'query':
      return (
        <svg {...common}>
          <circle
            cx="8"
            cy="8"
            r="7"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeDasharray="2.6 2.2"
          />
          <path
            d="M6.1 6.1a1.95 1.95 0 1 1 2.5 2.2c-.5.2-.7.6-.7 1.1v.3"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <circle cx="7.9" cy="12" r="0.9" fill="currentColor" />
        </svg>
      );
  }
}

export interface StatusChipProps {
  status: CheckStatus;
  /** Optional short explanation shown next to the label. */
  detail?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function StatusChip({ status, detail, size = 'md', className }: StatusChipProps) {
  const descriptor = CHECK_STATUS_DESCRIPTORS[status];

  return (
    <span
      className={cx(
        styles.chip,
        descriptor.className,
        size === 'sm' && styles.sm,
        className,
      )}
      data-status={status}
      data-tone={descriptor.tone}
      title={descriptor.meaning}
    >
      <StatusIcon shape={descriptor.shape} />
      <span className={styles.label}>{descriptor.label}</span>
      {detail !== undefined ? <span className={styles.detail}>{detail}</span> : null}
    </span>
  );
}
