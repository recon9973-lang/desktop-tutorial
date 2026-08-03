import type { ReactNode } from 'react';

import { ConsoleNav, ConsoleTopbar } from '@/components/ConsoleNav';
import { ConsoleOutage } from '@/components/ConsoleOutage';
import { SiteFooter } from '@/components/SiteFooter';
import { MAIN_LANDMARK_ID } from '@/components/SkipLink';
import {
  AuthUnavailableError,
  requireConsoleSession,
  toPublicIdentity,
} from '@/lib/session';
import type { ConsoleSession } from '@/lib/session';
import styles from '@/components/ConsoleNav.module.css';

import theme from './console-theme.module.css';

/**
 * Auth-guard boundary for every `/console/*` route.
 *
 * `requireConsoleSession()` verifies the session cookie against the auth API and
 * redirects to `/login?next=…` when there is none, so no console page below this
 * layout can render for an anonymous visitor. Nothing here invents a user.
 *
 * When the auth API cannot be reached at all, the layout returns the outage
 * screen and never renders `children` — the pages below it therefore never run.
 * The catch is narrow: `redirect()` signals itself by throwing, and that throw
 * must pass through untouched.
 *
 * Only `toPublicIdentity(session)` crosses into the tree; the access token stays
 * on the server.
 */
export default async function ConsoleLayout({ children }: { children: ReactNode }) {
  let session: ConsoleSession;
  try {
    session = await requireConsoleSession();
  } catch (error) {
    if (error instanceof AuthUnavailableError) {
      return <ConsoleOutage reason={error.reason} />;
    }
    throw error;
  }

  const identity = toPublicIdentity(session);

  return (
    // 콘솔 팔레트(시안 v2.2 · DESIGN-stripe.md)는 이 래퍼의 토큰 오버라이드로만
    // 들어간다 — 공개 도구의 확정 시안(틸)은 전역 토큰 그대로 남는다.
    <div className={theme.stripe}>
      <ConsoleTopbar identity={identity} />
      <div className={styles.shell}>
        <ConsoleNav identity={identity} />
        {/* tabIndex makes the skip link move focus past the sidebar, not just
            the scroll position. */}
        <main id={MAIN_LANDMARK_ID} tabIndex={-1} className={styles.content}>
          {children}
        </main>
      </div>
      <SiteFooter />
    </div>
  );
}
