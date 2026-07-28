import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { Role } from '@veo/shared-types';

import {
  CONSOLE_PERMISSIONS,
  ROLE_LABELS_KO,
  hasAnyPermission,
  hasPermission,
  isPermission,
  parsePermissions,
} from './permissions';
import type { Permission } from './permissions';

/**
 * Test fixture only.
 *
 * The role → permission matrix is owned by the API
 * (`apps/api/src/veo/authz/permissions.py`) and reaches the browser as the
 * resolved list on `/auth/me`. It is written out here so `hasPermission` can be
 * exercised per role; production code never contains this table.
 */
const ROLE_FIXTURE: Record<Role, readonly Permission[]> = {
  SUPER_ADMIN: CONSOLE_PERMISSIONS,
  LAB_ADMIN: [
    'org:read',
    'user:read',
    'customer:read',
    'project:read',
    'site:read',
    'competitor:read',
    'scan:read',
    'evidence:read',
    'keyword:read',
    'observation:read',
    'observation:raw_read',
    'issue:read',
    'report:read',
    'scoring_spec:read',
    'scoring_spec:author',
    'scoring_spec:publish',
    'usage:read',
    'audit:read',
  ],
  ANALYST: [
    'org:read',
    'customer:read',
    'customer:write',
    'project:read',
    'project:write',
    'site:read',
    'site:write',
    'competitor:read',
    'competitor:write',
    'scan:read',
    'scan:run',
    'evidence:read',
    'keyword:read',
    'keyword:run',
    'observation:read',
    'observation:run',
    'observation:raw_read',
    'issue:read',
    'issue:write',
    'report:read',
    'report:export',
    'scoring_spec:read',
    'credential:read_state',
    'usage:read',
  ],
  DEVELOPER: [
    'org:read',
    'project:read',
    'site:read',
    'scan:read',
    'scan:run',
    'evidence:read',
    'keyword:read',
    'observation:read',
    'issue:read',
    'issue:write',
    'report:read',
    'scoring_spec:read',
    'credential:read_state',
    'usage:read',
  ],
  SALES_VIEWER: [
    'org:read',
    'customer:read',
    'project:read',
    'site:read',
    'competitor:read',
    'scan:read',
    'keyword:read',
    'observation:read',
    'issue:read',
    'report:read',
    'scoring_spec:read',
  ],
  CLIENT_VIEWER: [
    'project:read',
    'site:read',
    'scan:read',
    'keyword:read',
    'observation:read',
    'competitor:read',
    'issue:read',
    'report:read',
    'scoring_spec:read',
  ],
};

function identityFor(role: Role) {
  return { permissions: ROLE_FIXTURE[role] };
}

describe('permission vocabulary', () => {
  it('matches the API permission enum exactly', () => {
    const source = path.join(
      import.meta.dirname,
      '..',
      '..',
      '..',
      '..',
      'apps',
      'api',
      'src',
      'veo',
      'authz',
      'permissions.py',
    );

    let python: string;
    try {
      python = readFileSync(source, 'utf8');
    } catch {
      // The API package is not always checked out beside the web app. Drift is
      // caught wherever both are present rather than failing the web build.
      return;
    }

    const enumBody = python.split('class Permission(StrEnum):')[1]?.split('\n\n\n')[0] ?? '';
    const fromPython = [...enumBody.matchAll(/^\s{4}[A-Z_]+ = "([^"]+)"/gm)].map(
      (match) => match[1],
    );

    expect(fromPython.length).toBeGreaterThan(0);
    expect([...CONSOLE_PERMISSIONS].sort()).toEqual([...fromPython].sort());
  });

  it('recognises a known permission and rejects an invented one', () => {
    expect(isPermission('issue:write')).toBe(true);
    expect(isPermission('issue:destroy')).toBe(false);
    expect(isPermission('')).toBe(false);
  });

  it('drops values it does not recognise instead of trusting them', () => {
    expect(parsePermissions(['issue:read', 'issue:invented', 42, null])).toEqual([
      'issue:read',
    ]);
  });

  it('returns nothing for a non-array', () => {
    expect(parsePermissions('issue:read')).toEqual([]);
    expect(parsePermissions(undefined)).toEqual([]);
  });
});

describe('hasPermission', () => {
  it('denies when there is no identity at all', () => {
    expect(hasPermission(null, 'project:read')).toBe(false);
    expect(hasPermission(undefined, 'project:read')).toBe(false);
  });

  it('denies when the identity holds no permissions', () => {
    expect(hasPermission({ permissions: [] }, 'project:read')).toBe(false);
  });

  it('grants SUPER_ADMIN every permission in the vocabulary', () => {
    for (const permission of CONSOLE_PERMISSIONS) {
      expect(hasPermission(identityFor('SUPER_ADMIN'), permission)).toBe(true);
    }
  });

  it('lets an analyst write issues but never publish a scoring spec', () => {
    expect(hasPermission(identityFor('ANALYST'), 'issue:write')).toBe(true);
    expect(hasPermission(identityFor('ANALYST'), 'scoring_spec:publish')).toBe(false);
  });

  it('lets a lab admin publish a scoring spec but never write customer data', () => {
    expect(hasPermission(identityFor('LAB_ADMIN'), 'scoring_spec:publish')).toBe(true);
    expect(hasPermission(identityFor('LAB_ADMIN'), 'customer:write')).toBe(false);
    expect(hasPermission(identityFor('LAB_ADMIN'), 'project:write')).toBe(false);
  });

  it('lets a developer fix and re-run, but never export a report', () => {
    expect(hasPermission(identityFor('DEVELOPER'), 'issue:write')).toBe(true);
    expect(hasPermission(identityFor('DEVELOPER'), 'scan:run')).toBe(true);
    expect(hasPermission(identityFor('DEVELOPER'), 'report:export')).toBe(false);
  });

  it('keeps a sales viewer out of raw evidence and every write', () => {
    expect(hasPermission(identityFor('SALES_VIEWER'), 'report:read')).toBe(true);
    expect(hasPermission(identityFor('SALES_VIEWER'), 'evidence:read')).toBe(false);
    expect(hasPermission(identityFor('SALES_VIEWER'), 'issue:write')).toBe(false);
    expect(hasPermission(identityFor('SALES_VIEWER'), 'scan:run')).toBe(false);
  });

  it('keeps a client viewer out of the customer list and credentials', () => {
    expect(hasPermission(identityFor('CLIENT_VIEWER'), 'project:read')).toBe(true);
    expect(hasPermission(identityFor('CLIENT_VIEWER'), 'customer:read')).toBe(false);
    expect(hasPermission(identityFor('CLIENT_VIEWER'), 'credential:read_state')).toBe(
      false,
    );
  });

  it('never grants a credential secret read to anyone, because none exists', () => {
    expect(isPermission('credential:read')).toBe(false);
  });
});

describe('hasAnyPermission', () => {
  it('grants when at least one permission is held', () => {
    expect(hasAnyPermission(identityFor('SALES_VIEWER'), 'issue:write', 'report:read')).toBe(
      true,
    );
  });

  it('denies when none is held', () => {
    expect(
      hasAnyPermission(identityFor('SALES_VIEWER'), 'issue:write', 'scoring_spec:publish'),
    ).toBe(false);
  });

  it('denies with no identity', () => {
    expect(hasAnyPermission(null, 'report:read')).toBe(false);
  });
});

describe('ROLE_LABELS_KO', () => {
  it('labels every role in Korean', () => {
    const roles: readonly Role[] = [
      'SUPER_ADMIN',
      'LAB_ADMIN',
      'ANALYST',
      'DEVELOPER',
      'SALES_VIEWER',
      'CLIENT_VIEWER',
    ];
    for (const role of roles) {
      expect(ROLE_LABELS_KO[role]).toMatch(/[가-힣]/);
    }
  });
});
