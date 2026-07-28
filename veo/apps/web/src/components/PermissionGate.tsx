import type { ReactNode } from 'react';

import { hasPermission } from '@/lib/permissions';
import type { Permission, PermissionHolder } from '@/lib/permissions';
import styles from './PermissionGate.module.css';

/** 1 for a whole-page denial, which is what every console page does. */
export type DeniedHeadingLevel = 1 | 2 | 3;

export interface PermissionGateProps {
  /** The resolved identity, or `null` when there is none. */
  identity: PermissionHolder | null | undefined;
  permission: Permission;
  children: ReactNode;
  /** Replaces the default denial notice. */
  fallback?: ReactNode;
  /** Heading level for the default notice. Defaults to 1. */
  headingLevel?: DeniedHeadingLevel;
}

/**
 * Renders `children` only for an identity that holds `permission`.
 *
 * When it does not, the protected content is not rendered at all — it never
 * enters the markup, so it cannot be revealed by reading the page source or by
 * defeating a CSS rule.
 *
 * Hiding a navigation link is a courtesy; this is the control. Every console
 * page wraps its content here, so a URL typed by hand lands on the denial notice
 * instead of on data. The API enforces the same rule again on every request:
 * this component decides what to draw, never what is allowed.
 */
export function PermissionGate({
  identity,
  permission,
  children,
  fallback,
  headingLevel = 1,
}: PermissionGateProps) {
  if (hasPermission(identity, permission)) {
    return <>{children}</>;
  }

  if (fallback !== undefined) {
    return <>{fallback}</>;
  }

  return <PermissionDenied permission={permission} headingLevel={headingLevel} />;
}

export interface PermissionDeniedProps {
  permission: Permission;
  headingLevel?: DeniedHeadingLevel;
}

/**
 * The denial notice.
 *
 * States the fact in words — never by colour alone — and names the permission
 * that is missing so the reader can ask an administrator for the right thing.
 *
 * The title is a real heading. Every console page wraps its *entire* body in the
 * gate, including its own `<h1>`, so a denied page used to reach the reader with
 * no headings at all: nothing to navigate to, and nothing for the browser tab
 * order or a heading list to describe.
 */
export function PermissionDenied({
  permission,
  headingLevel = 1,
}: PermissionDeniedProps) {
  const Heading = `h${headingLevel}` as 'h1' | 'h2' | 'h3';

  return (
    <div className={styles.denied} role="status">
      <span className={styles.mark} aria-hidden="true">
        —
      </span>
      <div className={styles.content}>
        <Heading className={styles.title}>권한이 없습니다</Heading>
        <p className={styles.description}>
          이 화면을 열려면 아래 권한이 필요합니다. 계정에는 부여되어 있지 않으므로 내용을
          표시하지 않았습니다. 조직의 콘솔 관리자에게 권한 부여를 요청하세요.
        </p>
        <p className={styles.permission}>
          필요한 권한: <span className={styles.token}>{permission}</span>
        </p>
      </div>
    </div>
  );
}
