import { readFileSync, readdirSync } from 'node:fs';
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

  /**
   * 예전에는 "모든 항목은 `:read` 권한으로만 가린다" 를 검사했다. 그 규칙이 지키려던 것은
   * **볼 수 있는 화면이 메뉴에서 사라지지 않는 것**이었고, 접미사는 그것의 대용이었다.
   *
   * 위험 검수 화면에서 대용이 어긋난다. 그 화면은 `observation:review` 로만 열리는데,
   * 안에 든 것이 **검수 전 지적의 원문**이라 `observation:read` 로 열면 안 된다 —
   * 그것을 고객 문서에서 막으려고 공개 게이트를 둔 것이다.
   *
   * 그래서 대용 대신 원래 지키려던 것을 직접 검사한다. **메뉴가 요구하는 권한은 그 화면이
   * 스스로 요구하는 권한과 같아야 한다.** 어긋나면 둘 중 하나가 일어난다 — 못 여는 메뉴가
   * 보이거나, 열 수 있는 화면이 숨는다.
   */
  it('asks for exactly the permission the page itself gates on', () => {
    const consoleDir = path.join(
      import.meta.dirname,
      '..',
      'app',
      '(console)',
      'console',
    );
    for (const item of CONSOLE_NAV) {
      const area = item.href.replace('/console/', '');
      const source = readFileSync(path.join(consoleDir, area, 'page.tsx'), 'utf8');
      const declared = /<PermissionGate[^>]*permission="([^"]+)"/.exec(source);
      expect(declared?.[1] ?? null, `${item.href}`).toBe(item.permission);
    }
  });
});

describe('visibleConsoleNav', () => {
  it('shows only the signed-in-everyone areas to an identity with no permissions', () => {
    // Account settings has no permission by design: gating "change my own password"
    // would hide it from exactly the accounts that hold none. The changelog is the
    // same class — release notes are for everyone who signed in.
    const visible = visibleConsoleNav({ permissions: [] });
    expect(visible.map((item) => item.href)).toEqual([
      '/console/changelog',
      '/console/account',
    ]);
  });

  it('shows nothing when there is no identity', () => {
    expect(visibleConsoleNav(null)).toEqual([]);
  });

  it('shows only what the identity may actually open', () => {
    const visible = visibleConsoleNav({
      permissions: ['report:read', 'issue:read'],
    });

    // Account settings and the changelog are always present for a signed-in person.
    expect(visible.map((item) => item.href).sort()).toEqual([
      '/console/account',
      '/console/changelog',
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
      '/console/changelog',
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
