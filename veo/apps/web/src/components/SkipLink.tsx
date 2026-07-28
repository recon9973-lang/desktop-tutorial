/** The id every layout gives its `<main>`, and the skip link's target. */
export const MAIN_LANDMARK_ID = 'veo-main';

/**
 * The first tab stop on every page.
 *
 * Rendered in the root layout, before anything else in `<body>`, so a keyboard
 * reader reaches it with one Tab from the address bar and can step over the
 * header and the console sidebar. The target `<main>` carries `tabIndex={-1}`
 * so following the link moves focus and not just the scroll position — without
 * that, the next Tab goes straight back into the navigation just skipped.
 */
export function SkipLink() {
  return (
    <a className="veo-skip-link" href={`#${MAIN_LANDMARK_ID}`}>
      본문 바로가기
    </a>
  );
}
