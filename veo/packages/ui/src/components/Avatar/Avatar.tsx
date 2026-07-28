import { cx } from '../../utils/cx';
import styles from './Avatar.module.css';

export type AvatarSize = 'sm' | 'md';

export interface AvatarProps {
  /** The real display name. Nothing is invented when it is empty. */
  name: string;
  size?: AvatarSize;
  className?: string;
}

/**
 * Derives the glyph shown inside the avatar.
 *
 * Korean and other single-token names take their first character; Latin names
 * with a given and family name take one letter from each. An empty name yields a
 * neutral middle dot rather than a made-up identity.
 */
export function initialsFor(name: string): string {
  const trimmed = name.trim();
  if (trimmed === '') {
    return '·';
  }

  const parts = trimmed.split(/\s+/).filter((part) => part.length > 0);
  if (parts.length >= 2) {
    const first = Array.from(parts[0] ?? '')[0] ?? '';
    const last = Array.from(parts[parts.length - 1] ?? '')[0] ?? '';
    return `${first}${last}`.toUpperCase();
  }

  return (Array.from(trimmed)[0] ?? '·').toUpperCase();
}

export function Avatar({ name, size = 'md', className }: AvatarProps) {
  return (
    <span className={cx(styles.avatar, styles[size], className)}>
      <span className={styles.glyph} data-veo-avatar-initials="" aria-hidden="true">
        {initialsFor(name)}
      </span>
      {/* The name carries the meaning; the glyph is decoration. */}
      <span className={styles.name}>{name}</span>
    </span>
  );
}
