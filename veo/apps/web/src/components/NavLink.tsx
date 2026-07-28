'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

/**
 * Decides whether `href` names the area the reader is currently in.
 *
 * Exact match, or a match on a whole path segment — `/console/projects` is
 * current while reading `/console/projects/42`, but `/console/scoring-versions`
 * is not current from `/console/scoring`, which a plain `startsWith` would get
 * wrong. Exported so the rule can be tested without rendering.
 */
export function isCurrentPath(pathname: string | null, href: string): boolean {
  if (pathname === null) {
    return false;
  }
  if (pathname === href) {
    return true;
  }
  return href !== '/' && pathname.startsWith(`${href}/`);
}

export interface NavLinkProps {
  href: string;
  className?: string;
  /** Applied in addition to `className` when this link is the current page. */
  currentClassName?: string;
  children: ReactNode;
}

/**
 * A navigation link that says, in the accessibility tree, whether it is where
 * you already are.
 *
 * Both navigations previously marked the current page in no way at all — not
 * visually and not programmatically — so a screen-reader user tabbing the
 * console sidebar had nothing telling them which of the nine areas was open.
 * `aria-current="page"` is the programmatic half; `data-current` gives the
 * stylesheet something to hang a non-colour marker on.
 */
export function NavLink({ href, className, currentClassName, children }: NavLinkProps) {
  const current = isCurrentPath(usePathname(), href);

  return (
    <Link
      href={href}
      className={[className, current ? currentClassName : undefined]
        .filter((value) => typeof value === 'string' && value.length > 0)
        .join(' ')}
      {...(current ? { 'aria-current': 'page' as const, 'data-current': '' } : {})}
    >
      {children}
    </Link>
  );
}
