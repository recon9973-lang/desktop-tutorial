import Link from 'next/link';

import { NavLink } from '@/components/NavLink';
import { PUBLIC_NAV } from '@/lib/navigation';
import styles from './SiteHeader.module.css';

export function SiteHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/" className={styles.brand}>
          <span className={styles.wordmark}>VEO</span>
          <span className={styles.tagline}>SEO · GEO · 네이버 키워드</span>
        </Link>

        <nav className={styles.nav} aria-label="주요 메뉴">
          <ul className={styles.navList}>
            {PUBLIC_NAV.map((item) => (
              <li key={item.href}>
                <NavLink
                  href={item.href}
                  className={styles.navLink}
                  currentClassName={styles.navLinkCurrent}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <Link href="/console/dashboard" className={styles.consoleLink}>
            콘솔
          </Link>
        </nav>
      </div>
    </header>
  );
}
