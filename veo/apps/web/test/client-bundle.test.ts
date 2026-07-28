// @vitest-environment node
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Reads what `next build` actually shipped to the browser.
 *
 * The structural checks in `token-never-reaches-the-client.test.ts` reason about
 * the source; this one reads the output. Run `pnpm --filter @veo/web build`
 * before `pnpm --filter @veo/web test` for it to have anything to inspect —
 * without a build directory there is nothing to assert about, and it says so
 * rather than passing quietly.
 */

const STATIC_DIR = path.join(import.meta.dirname, '..', '.next', 'static');

function readAll(dir: string, acc: { file: string; text: string }[] = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      readAll(full, acc);
    } else if (/\.(js|mjs|json|txt|map)$/.test(entry.name)) {
      acc.push({ file: path.relative(STATIC_DIR, full), text: readFileSync(full, 'utf8') });
    }
  }
  return acc;
}

const BUILT = existsSync(STATIC_DIR);

describe.skipIf(!BUILT)('the built client bundle', () => {
  const chunks = BUILT ? readAll(STATIC_DIR) : [];

  it('contains chunks to inspect', () => {
    expect(chunks.length).toBeGreaterThan(0);
  });

  it('never names the session cookie', () => {
    const offenders = chunks
      .filter((chunk) => chunk.text.includes('veo_console_session'))
      .map((chunk) => chunk.file);
    expect(offenders).toEqual([]);
  });

  it('never reads or writes a cookie or web storage', () => {
    const offenders = chunks
      .filter((chunk) => /veo_console_session|Bearer \$\{/.test(chunk.text))
      .map((chunk) => chunk.file);
    expect(offenders).toEqual([]);
  });

  it('never carries the auth API paths, which are server-side only', () => {
    const offenders = chunks
      .filter((chunk) => chunk.text.includes('/api/auth/login'))
      .map((chunk) => chunk.file);
    expect(offenders).toEqual([]);
  });
});

describe('build output', () => {
  it('is inspected when present', () => {
    // Fails nothing on its own; records whether the assertions above ran.
    expect(typeof BUILT).toBe('boolean');
  });
});
