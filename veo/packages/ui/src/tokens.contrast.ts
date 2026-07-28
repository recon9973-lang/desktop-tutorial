/*
 * Contrast arithmetic over the real `tokens.css` file.
 *
 * This is not a lint of the CSS text: it reads the declarations, follows
 * `var(--…)` indirection to a literal colour, and computes the WCAG 2.x
 * relative-luminance ratio. The numbers it produces are the numbers a browser
 * would produce for the same two colours, so a failure here is a real failure
 * rather than a stylistic objection.
 *
 * What it cannot see: anything that depends on layout — a translucent overlay,
 * a colour composited over an image, text rendered at a size that would qualify
 * for the 3:1 large-text threshold. Those need a real browser. The pair table
 * in `tokens.contrast.test.ts` therefore states, for every pair, which element
 * uses it, so the list can be checked against the components by reading.
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export type ThemeName = 'light' | 'dark';

const TOKENS_CSS = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  'tokens.css',
);

/** Marks where the dark-scheme overrides begin. */
const DARK_BLOCK = '@media (prefers-color-scheme: dark)';

const DECLARATION = /(--veo-[a-z0-9-]+)\s*:\s*([^;]+);/g;

function declarationsIn(source: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const match of source.matchAll(DECLARATION)) {
    const name = match[1];
    const value = match[2];
    if (name !== undefined && value !== undefined) {
      map.set(name, value.trim());
    }
  }
  return map;
}

/**
 * The two custom-property environments a browser can be in.
 *
 * Dark is not a separate palette: it is the light `:root` block with the
 * dark-scheme overrides applied on top, which is exactly the cascade a browser
 * performs. Reading only the dark block would miss every token it inherits.
 */
export function readThemes(cssPath: string = TOKENS_CSS): Record<ThemeName, Map<string, string>> {
  const css = readFileSync(cssPath, 'utf8');
  const darkAt = css.indexOf(DARK_BLOCK);
  if (darkAt < 0) {
    throw new Error(`tokens.css no longer contains a "${DARK_BLOCK}" block`);
  }

  const light = declarationsIn(css.slice(0, darkAt));
  const dark = new Map(light);
  for (const [name, value] of declarationsIn(css.slice(darkAt))) {
    dark.set(name, value);
  }

  return { light, dark };
}

/** Follows `var(--x)` chains until a literal value is reached. */
export function resolveToken(tokens: Map<string, string>, name: string): string {
  let value = tokens.get(name);
  if (value === undefined) {
    throw new Error(`tokens.css does not define ${name}`);
  }

  for (let hop = 0; hop < 16; hop += 1) {
    const indirect = /^var\(\s*(--[a-z0-9-]+)\s*\)$/.exec(value);
    if (indirect === null) {
      return value;
    }
    const next = tokens.get(indirect[1] ?? '');
    if (next === undefined) {
      throw new Error(`${name} resolves to ${indirect[1]}, which tokens.css does not define`);
    }
    value = next;
  }

  throw new Error(`${name} does not resolve to a literal colour`);
}

export type Rgb = readonly [number, number, number];

export function parseHex(value: string): Rgb {
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(value.trim());
  if (hex === null) {
    throw new Error(`"${value}" is not an opaque hex colour, so its contrast cannot be computed`);
  }
  const digits = hex[1] ?? '';
  const full =
    digits.length === 3
      ? digits
          .split('')
          .map((d) => d + d)
          .join('')
      : digits;
  const n = Number.parseInt(full, 16);
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff];
}

/** WCAG 2.x relative luminance. */
export function relativeLuminance([r, g, b]: Rgb): number {
  const channel = (raw: number): number => {
    const c = raw / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG 2.x contrast ratio, always ≥ 1, rounded to two decimals by the caller. */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

export function ratioForTokens(
  tokens: Map<string, string>,
  foreground: string,
  background: string,
): number {
  return contrastRatio(
    parseHex(resolveToken(tokens, foreground)),
    parseHex(resolveToken(tokens, background)),
  );
}
