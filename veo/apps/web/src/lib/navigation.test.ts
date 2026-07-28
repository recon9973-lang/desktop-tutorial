import { readdirSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

import { CONSOLE_NAV, PUBLIC_NAV, visibleConsoleNav } from './navigation';
import { isPermission } from './permissions';

describe('CONSOLE_NAV', () => {
  it('names a real permission for every entry that gates on one', () => {
    expect(CONSOLE_NAV.length).toBeGreaterThan(0);
    for (const item of CONSOLE_NAV) {
      if (item.permission === null) continue;
      expect(isPermission(item.permission), `${item.href} → ${item.permission}`).toBe(true);
    }
  });

  it('covers exactly the routes that exist under (console)/console', () => {
    const consoleDir = path.join(
      import.meta.dirname,
      '..',
      'app',
      '(console)',
      'console',
    );
    const routes = readdirSync(consoleDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => `/console/${entry.name}`);

    expect([...CONSOLE_NAV.map((item) => item.href)].sort()).toEqual([...routes].sort());
  });

  it('only ever asks for a read permission — navigation is not an action', () => {
    for (const item of CONSOLE_NAV) {
      if (item.permission === null) continue;
      expect(item.permission.endsWith(':read')).toBe(true);
    }
  });
});

describe('visibleConsoleNav', () => {
  it('shows only the signed-in-everyone areas to an identity with no permissions', () => {
    // Account settings has no permission by design: gating "change my own password"
    // would hide it from exactly the accounts that hold none.
    const visible = visibleConsoleNav({ permissions: [] });
    expect(visible.map((item) => item.href)).toEqual(['/console/account']);
  });

  it('shows nothing when there is no identity', () => {
    expect(visibleConsoleNav(null)).toEqual([]);
  });

  it('shows only what the identity may actually open', () => {
    const visible = visibleConsoleNav({
      permissions: ['report:read', 'issue:read'],
    });

    // Account settings is always present for a signed-in person, whatever they hold.
    expect(visible.map((item) => item.href).sort()).toEqual([
      '/console/account',
      '/console/issues',
      '/console/reports',
    ]);
  });

  it('preserves the declared order', () => {
    const visible = visibleConsoleNav({
      permissions: ['scoring_spec:read', 'project:read'],
    });
    expect(visible.map((item) => item.href)).toEqual([
      '/console/projects',
      '/console/scoring-versions',
      '/console/account',
    ]);
  });
});

describe('PUBLIC_NAV', () => {
  it('stays free of permissions — the public tools need no session', () => {
    for (const item of PUBLIC_NAV) {
      expect(item).not.toHaveProperty('permission');
    }
  });
});
