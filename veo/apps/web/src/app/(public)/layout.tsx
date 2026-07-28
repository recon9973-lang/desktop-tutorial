import type { ReactNode } from 'react';

import { SiteFooter } from '@/components/SiteFooter';
import { SiteHeader } from '@/components/SiteHeader';
import { MAIN_LANDMARK_ID } from '@/components/SkipLink';

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteHeader />
      {/* tabIndex makes the skip link move focus, not just the scroll position. */}
      <main id={MAIN_LANDMARK_ID} tabIndex={-1}>
        {children}
      </main>
      <SiteFooter />
    </>
  );
}
