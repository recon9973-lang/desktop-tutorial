import type { ReactNode } from 'react';
import { Avatar } from '../Avatar/Avatar';
import { cx } from '../../utils/cx';
import styles from './UserMenu.module.css';

export interface UserMenuProps {
  /** Real display name from the session. Never a placeholder. */
  name: string;
  email: string;
  /** Human-readable role names, already translated by the caller. */
  roleLabels: readonly string[];
  /** Sign-out control and anything else the console wants in the panel. */
  actions?: ReactNode;
  /** Renders the panel open. Used by tests and by no-JavaScript fallbacks. */
  defaultOpen?: boolean;
  className?: string;
}

/**
 * Account disclosure for the console header.
 *
 * Built on `<details>` so it opens with the keyboard and without JavaScript, and
 * so no focus-trap logic has to be maintained. It owns no session state: the
 * caller passes the identity in and the sign-out control as `actions`.
 */
export function UserMenu({
  name,
  email,
  roleLabels,
  actions,
  defaultOpen = false,
  className,
}: UserMenuProps) {
  return (
    <details className={cx(styles.menu, className)} open={defaultOpen}>
      <summary className={styles.summary} tabIndex={0} aria-label={`계정 메뉴: ${name}`}>
        <Avatar name={name} size="sm" />
        <span className={styles.name}>{name}</span>
        <span className={styles.chevron} aria-hidden="true">
          ▾
        </span>
      </summary>

      <div className={styles.panel}>
        <p className={styles.email}>{email}</p>

        {roleLabels.length > 0 ? (
          <>
            {/*
              Named with `aria-label` rather than `aria-labelledby`. This runs as
              a server component, so `useId` is not available to make a unique
              id, and a hard-coded one would collide the moment the console
              renders two account menus — a real possibility once the topbar
              gains an organisation switcher.
            */}
            <p className={styles.rolesLabel} aria-hidden="true">
              역할
            </p>
            <ul className={styles.roles} aria-label="역할">
              {roleLabels.map((label) => (
                <li key={label} className={styles.role}>
                  {label}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className={styles.noRoles}>부여된 역할이 없습니다.</p>
        )}

        {actions === undefined ? null : <div className={styles.actions}>{actions}</div>}
      </div>
    </details>
  );
}
