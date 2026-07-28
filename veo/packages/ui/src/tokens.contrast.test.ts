// @vitest-environment node
import { describe, expect, it } from 'vitest';

import { ratioForTokens, readThemes } from './tokens.contrast';
import type { ThemeName } from './tokens.contrast';

/**
 * Every foreground/background pair the VEO interface actually paints, checked
 * against WCAG 2.2 in both themes with real arithmetic.
 *
 * `where` names the element that produces the pair. If a component stops using
 * a pair, delete the row; if one starts using a new pair, add it. A row nobody
 * can point at is worse than no row, because it makes the suite look thorough
 * without checking anything real.
 *
 * Thresholds:
 *   4.5 — SC 1.4.3 body text
 *   3.0 — SC 1.4.3 large text (≥ 24px, or ≥ 18.66px bold), and SC 1.4.11
 *         non-text contrast for the boundary of a user-interface component
 *
 * Deliberately *not* asserted at 3:1, with the measured number recorded so the
 * decision is visible rather than silent, are the purely decorative rules:
 * `--veo-color-border` around a Card and under the topbar. Those outline a
 * container whose content is already fully legible; SC 1.4.11 covers the
 * boundary of a *control*, which is `--veo-color-border-strong` here. See
 * `apps/web/docs/accessibility.md`.
 */

interface Pair {
  readonly fg: string;
  readonly bg: string;
  readonly min: number;
  readonly where: string;
}

const TEXT_PAIRS: readonly Pair[] = [
  {
    fg: '--veo-color-text',
    bg: '--veo-color-bg',
    min: 4.5,
    where: 'body text on the page background',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-color-surface',
    min: 4.5,
    where: 'Card / ScoreCard body text',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-color-surface-raised',
    min: 4.5,
    where: 'UserMenu panel text',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-color-surface-sunken',
    min: 4.5,
    where: 'EmptyState title, .token code chips',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-color-bg-subtle',
    min: 4.5,
    where: 'nav link and UserMenu summary hover',
  },
  {
    fg: '--veo-color-text-muted',
    bg: '--veo-color-bg',
    min: 4.5,
    where: 'page lede and footer note',
  },
  {
    fg: '--veo-color-text-muted',
    bg: '--veo-color-surface',
    min: 4.5,
    where: 'Card description, ScoreCard meta terms, nav link description',
  },
  {
    fg: '--veo-color-text-muted',
    bg: '--veo-color-surface-sunken',
    min: 4.5,
    where: 'EmptyState description, DataSourceBadge text',
  },
  {
    fg: '--veo-color-text-muted',
    bg: '--veo-color-surface-raised',
    min: 4.5,
    where: 'UserMenu email and role label',
  },
  {
    fg: '--veo-color-accent',
    bg: '--veo-color-surface',
    min: 4.5,
    where: 'inline links, VEO wordmark',
  },
  {
    fg: '--veo-color-accent',
    bg: '--veo-color-bg',
    min: 4.5,
    where: 'inline links and the eyebrow label on a page background',
  },
  {
    fg: '--veo-color-accent',
    bg: '--veo-color-accent-subtle',
    min: 4.5,
    where: 'ScoreCard band, Avatar initials, header 콘솔 link',
  },
  {
    fg: '--veo-color-text-on-accent',
    bg: '--veo-color-accent',
    min: 4.5,
    where: 'primary Button label',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-color-secondary-subtle',
    min: 4.5,
    where: 'callout paragraph',
  },
  {
    fg: '--veo-color-secondary',
    bg: '--veo-color-surface',
    min: 4.5,
    where: 'GEO/observation accent text',
  },
];

const STATUS_PAIRS: readonly Pair[] = [
  {
    fg: '--veo-status-pass-fg',
    bg: '--veo-status-pass-bg',
    min: 4.5,
    where: 'StatusChip PASS label and icon',
  },
  {
    fg: '--veo-status-warning-fg',
    bg: '--veo-status-warning-bg',
    min: 4.5,
    where: 'StatusChip WARNING label and icon',
  },
  {
    fg: '--veo-status-fail-fg',
    bg: '--veo-status-fail-bg',
    min: 4.5,
    where: 'StatusChip FAIL, ErrorState, FormError, danger Button',
  },
  {
    fg: '--veo-status-na-fg',
    bg: '--veo-status-na-bg',
    min: 4.5,
    where: 'StatusChip NOT_APPLICABLE, PermissionDenied mark',
  },
  {
    fg: '--veo-status-unknown-fg',
    bg: '--veo-status-unknown-bg',
    min: 4.5,
    where: 'StatusChip UNKNOWN (측정 불가)',
  },
  {
    fg: '--veo-status-unknown-fg',
    bg: '--veo-color-surface',
    min: 3,
    where: 'ScoreCard 측정 불가 headline (22px semibold — large text)',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-status-fail-bg',
    min: 4.5,
    where: 'ErrorState description',
  },
  {
    fg: '--veo-color-text-muted',
    bg: '--veo-status-fail-bg',
    min: 4.5,
    where: 'ErrorState 오류 코드',
  },
  {
    fg: '--veo-color-text',
    bg: '--veo-status-na-bg',
    min: 4.5,
    where: 'PermissionDenied heading',
  },
  {
    fg: '--veo-color-text-muted',
    bg: '--veo-status-na-bg',
    min: 4.5,
    where: 'PermissionDenied description',
  },
];

const NON_TEXT_PAIRS: readonly Pair[] = [
  {
    fg: '--veo-color-border-strong',
    bg: '--veo-color-surface',
    min: 3,
    where: 'TextField input boundary, secondary Button boundary on a card',
  },
  {
    fg: '--veo-color-border-strong',
    bg: '--veo-color-bg',
    min: 3,
    where: 'TextField input boundary on the page background',
  },
  {
    fg: '--veo-color-border-strong',
    bg: '--veo-color-bg-subtle',
    min: 3,
    where: 'secondary Button boundary while hovered',
  },
  {
    fg: '--veo-color-focus-ring',
    bg: '--veo-color-bg',
    min: 3,
    where: 'focus indicator against the page background',
  },
  {
    fg: '--veo-color-focus-ring',
    bg: '--veo-color-surface',
    min: 3,
    where: 'focus indicator against a card',
  },
  {
    fg: '--veo-status-pass-border',
    bg: '--veo-status-pass-bg',
    min: 3,
    where: 'StatusChip PASS pill silhouette',
  },
  {
    fg: '--veo-status-warning-border',
    bg: '--veo-status-warning-bg',
    min: 3,
    where: 'StatusChip WARNING rounded-square silhouette',
  },
  {
    fg: '--veo-status-fail-border',
    bg: '--veo-status-fail-bg',
    min: 3,
    where: 'ErrorState and FormError left rule against their own tint',
  },
  {
    fg: '--veo-status-fail-border',
    bg: '--veo-color-surface',
    min: 3,
    where: 'TextField invalid boundary, drawn on a card',
  },
  {
    fg: '--veo-status-fail-border',
    bg: '--veo-color-bg',
    min: 3,
    where: 'TextField invalid boundary, drawn on the page background',
  },
  {
    fg: '--veo-status-na-border',
    bg: '--veo-status-na-bg',
    min: 3,
    where: 'StatusChip NOT_APPLICABLE pill silhouette',
  },
  {
    fg: '--veo-status-unknown-border',
    bg: '--veo-status-unknown-bg',
    min: 3,
    where: 'StatusChip UNKNOWN dashed silhouette',
  },
];

const THEMES = readThemes();
const THEME_NAMES: readonly ThemeName[] = ['light', 'dark'];

function check(name: ThemeName, pair: Pair): { ratio: number; line: string } {
  const ratio = ratioForTokens(THEMES[name], pair.fg, pair.bg);
  const rounded = Math.round(ratio * 100) / 100;
  return {
    ratio: rounded,
    line: `${name}: ${pair.fg} on ${pair.bg} = ${rounded.toFixed(2)}:1 (needs ${pair.min}:1) — ${pair.where}`,
  };
}

describe.each(THEME_NAMES)('token contrast · %s theme', (theme) => {
  describe('text (SC 1.4.3)', () => {
    it.each(TEXT_PAIRS)('$where', (pair) => {
      const { ratio, line } = check(theme, pair);
      expect(ratio, line).toBeGreaterThanOrEqual(pair.min);
    });
  });

  describe('measurement status (SC 1.4.3)', () => {
    it.each(STATUS_PAIRS)('$where', (pair) => {
      const { ratio, line } = check(theme, pair);
      expect(ratio, line).toBeGreaterThanOrEqual(pair.min);
    });
  });

  describe('component boundaries and focus (SC 1.4.11)', () => {
    it.each(NON_TEXT_PAIRS)('$where', (pair) => {
      const { ratio, line } = check(theme, pair);
      expect(ratio, line).toBeGreaterThanOrEqual(pair.min);
    });
  });
});

describe('the contrast harness itself', () => {
  it('agrees with the published WCAG worked examples', () => {
    // Black on white is the definitional maximum; #777 on white is the value
    // the WCAG understanding document uses as the 4.5:1 boundary case.
    const tokens = new Map([
      ['--black', '#000000'],
      ['--white', '#ffffff'],
      ['--grey', '#777777'],
    ]);
    expect(ratioForTokens(tokens, '--black', '--white')).toBeCloseTo(21, 5);
    expect(ratioForTokens(tokens, '--grey', '--white')).toBeCloseTo(4.48, 2);
  });

  it('follows var() indirection rather than giving up on it', () => {
    const tokens = new Map([
      ['--raw', '#0a6b64'],
      ['--semantic', 'var(--raw)'],
      ['--white', '#ffffff'],
    ]);
    expect(ratioForTokens(tokens, '--semantic', '--white')).toBeCloseTo(6.36, 2);
  });

  it('refuses a colour it cannot evaluate instead of scoring it as a pass', () => {
    const tokens = new Map([['--translucent', 'rgba(0, 0, 0, 0.5)'], ['--white', '#ffffff']]);
    expect(() => ratioForTokens(tokens, '--translucent', '--white')).toThrow(
      /not an opaque hex colour/,
    );
  });

  it('reads both themes out of the one stylesheet, with dark inheriting light', () => {
    // `--veo-space-4` is declared only in the light `:root` block; the dark map
    // must still carry it, or the dark checks are reading a partial cascade.
    expect(THEMES.dark.get('--veo-space-4')).toBe(THEMES.light.get('--veo-space-4'));
    expect(THEMES.dark.get('--veo-color-bg')).not.toBe(THEMES.light.get('--veo-color-bg'));
  });
});
