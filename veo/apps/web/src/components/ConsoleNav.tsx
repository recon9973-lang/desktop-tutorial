import Link from 'next/link';
import { Button, UserMenu } from '@veo/ui';

import { NavLink } from '@/components/NavLink';
import { visibleConsoleNav } from '@/lib/navigation';
import { ROLE_LABELS_KO } from '@/lib/permissions';
import type { PublicConsoleIdentity } from '@/lib/session';
import styles from './ConsoleNav.module.css';

export interface ConsoleChromeProps {
  /** Token-free view of the session. See `toPublicIdentity`. */
  identity: PublicConsoleIdentity;
}

/** Ties the sidebar's visible label to the navigation landmark that uses it. */
const NAV_TITLE_ID = 'veo-console-nav-title';

export function ConsoleTopbar({ identity }: ConsoleChromeProps) {
  const roleLabels = identity.roles.map((role) => ROLE_LABELS_KO[role]);

  return (
    <header className={styles.topbar}>
      <div className={styles.topbarInner}>
        <Link href="/" className={styles.brand}>
          <span className={styles.wordmark}>VEO</span>
          <span className={styles.badge}>콘솔</span>
        </Link>

        <UserMenu
          name={identity.displayName}
          email={identity.email}
          roleLabels={roleLabels}
          actions={
            // A plain form POST: sign-out works without JavaScript, and the
            // cookie is cleared by the server rather than by the browser.
            <form method="post" action="/api/session/logout" className={styles.logoutForm}>
              <Button type="submit" variant="secondary" size="sm" block>
                로그아웃
              </Button>
            </form>
          }
        />
      </div>
    </header>
  );
}

export function ConsoleNav({ identity }: ConsoleChromeProps) {
  const items = visibleConsoleNav(identity);

  return (
    // Named from its own visible label rather than from an `aria-label` the
    // reader cannot see. It used to be an <h2>, which made it the first heading
    // in the document — ahead of the page's <h1>, because the sidebar precedes
    // <main>. The landmark already carries the name, so the heading was doing
    // nothing except disordering the heading outline.
    <nav className={styles.sidebar} aria-labelledby={NAV_TITLE_ID}>
      <p className={styles.sidebarTitle} id={NAV_TITLE_ID}>
        콘솔 메뉴
      </p>

      {items.length === 0 ? (
        <p className={styles.emptyNav}>
          열람할 수 있는 메뉴가 없습니다. 계정에 부여된 권한이 없어 콘솔 화면을 열 수
          없습니다. 조직의 콘솔 관리자에게 문의하세요.
        </p>
      ) : (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.href}>
              <NavLink
                href={item.href}
                className={styles.link}
                currentClassName={styles.linkCurrent}
              >
                {item.label}
                <span className={styles.linkDescription}>{item.description}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
