// @vitest-environment node
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * SC 2.2.2 · Pause, Stop, Hide.
 *
 * Two of the design system's animations loop forever — the Button spinner while
 * a request is in flight, and the Skeleton shimmer while a panel loads. Neither
 * can be dismissed, so the only correct behaviour for someone who has asked
 * their system for less motion is not to start them.
 *
 * This reads the stylesheets rather than the rendered page: vitest does not
 * apply CSS, and jsdom does not evaluate media queries, so there is no way to
 * observe the effect at runtime here. What it can prove is that no stylesheet
 * introduces a looping animation without an escape — which is the mistake this
 * is guarding against. That an escape *works* is on the manual list in
 * `apps/web/docs/accessibility.md`.
 */

const SRC = path.join(path.dirname(fileURLToPath(import.meta.url)));

function stylesheets(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      stylesheets(full, acc);
    } else if (entry.name.endsWith('.css')) {
      acc.push(full);
    }
  }
  return acc;
}

const SHEETS = stylesheets(SRC).map((file) => ({
  name: path.relative(SRC, file),
  text: readFileSync(file, 'utf8'),
}));

const REDUCED_MOTION = '@media (prefers-reduced-motion: reduce)';

describe('motion', () => {
  it('finds the stylesheets it is supposed to be checking', () => {
    expect(SHEETS.length).toBeGreaterThan(0);
    expect(SHEETS.map((sheet) => sheet.name)).toContain('tokens.css');
  });

  it.each(SHEETS.filter((sheet) => sheet.text.includes('@keyframes')))(
    '$name pairs every @keyframes with a reduced-motion escape',
    (sheet) => {
      expect(sheet.text).toContain(REDUCED_MOTION);

      const escape = sheet.text.slice(sheet.text.indexOf(REDUCED_MOTION));
      // The escape has to actually turn the animation off, not merely exist.
      expect(escape).toMatch(/animation:\s*none/);
    },
  );

  it('collapses the motion duration tokens to zero under reduced motion', () => {
    const tokens = SHEETS.find((sheet) => sheet.name === 'tokens.css');
    expect(tokens).toBeDefined();

    const escape = (tokens?.text ?? '').slice(
      (tokens?.text ?? '').indexOf(REDUCED_MOTION),
    );
    for (const token of [
      '--veo-duration-instant',
      '--veo-duration-fast',
      '--veo-duration-base',
    ]) {
      expect(escape).toContain(`${token}: 0ms`);
    }
  });

  it('never animates anything for longer than five seconds without a control', () => {
    // SC 2.2.2 exempts motion shorter than five seconds. Anything longer, or
    // infinite, has to be stoppable — and the only stop VEO offers is the
    // reduced-motion escape checked above, so nothing may opt out of it.
    const looping = SHEETS.filter((sheet) => /animation:[^;]*infinite/.test(sheet.text));
    expect(looping.length).toBeGreaterThan(0);
    for (const sheet of looping) {
      expect(sheet.text, `${sheet.name} loops forever with no reduced-motion escape`).toContain(
        REDUCED_MOTION,
      );
    }
  });
});
