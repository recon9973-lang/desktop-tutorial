import type { ReactNode } from 'react';

import { SiteFooter } from '@/components/SiteFooter';
import { SiteHeader } from '@/components/SiteHeader';
import { MAIN_LANDMARK_ID } from '@/components/SkipLink';

import theme from '@/styles/stripe-theme.module.css';

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    // 콘솔과 **같은 테마 파일**을 쓴다 — 한 제품이 두 얼굴을 갖지 않게.
    <div className={theme.stripe}>
      <SiteHeader />
      {/* tabIndex makes the skip link move focus, not just the scroll position. */}
      <main id={MAIN_LANDMARK_ID} tabIndex={-1}>
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
