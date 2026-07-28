import { PERMISSION_VALUES } from '@veo/shared-types';
import type { Permission, Role } from '@veo/shared-types';

export type { Permission };

/**
 * The console permission vocabulary.
 *
 * Re-exported from `@veo/shared-types`, which is generated from
 * `apps/api/src/veo/authz/permissions.py`. This used to be a hand-maintained copy kept
 * honest by a drift test — and the moment a permission was added on the server, that
 * test failed rather than the list updating itself. There is now one definition.
 *
 * What is deliberately **not** here is the role → permission matrix. That lives
 * in the API and reaches this app only as the resolved list on `/auth/me`, so a
 * role can never be widened by editing the front end.
 */
export const CONSOLE_PERMISSIONS = PERMISSION_VALUES;

const PERMISSION_SET: ReadonlySet<string> = new Set<string>(CONSOLE_PERMISSIONS);

export function isPermission(value: unknown): value is Permission {
  return typeof value === 'string' && PERMISSION_SET.has(value);
}

/**
 * Narrows an untrusted list from the API to permissions this build understands.
 *
 * Unrecognised entries are dropped rather than carried around: an unknown string
 * can never be matched by `hasPermission`, so keeping it would only make the
 * session look more capable than it is.
 */
export function parsePermissions(value: unknown): readonly Permission[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isPermission);
}

/** Anything carrying a resolved permission list — a session, or a test double. */
export interface PermissionHolder {
  readonly permissions: readonly Permission[];
}

/**
 * The single place the console asks "may this identity do that?".
 *
 * Deny by default: no identity, or no permission, is a no.
 */
export function hasPermission(
  holder: PermissionHolder | null | undefined,
  permission: Permission,
): boolean {
  if (holder === null || holder === undefined) {
    return false;
  }
  return holder.permissions.includes(permission);
}

export function hasAnyPermission(
  holder: PermissionHolder | null | undefined,
  ...permissions: readonly Permission[]
): boolean {
  return permissions.some((permission) => hasPermission(holder, permission));
}

/** Display names for the roles the API resolves. */
export const ROLE_LABELS_KO: Record<Role, string> = {
  SUPER_ADMIN: '최고 관리자',
  LAB_ADMIN: '연구 관리자',
  ANALYST: '분석가',
  DEVELOPER: '개발자',
  SALES_VIEWER: '영업 열람자',
  CLIENT_VIEWER: '고객 열람자',
};

export const ROLE_VALUES = [
  'SUPER_ADMIN',
  'LAB_ADMIN',
  'ANALYST',
  'DEVELOPER',
  'SALES_VIEWER',
  'CLIENT_VIEWER',
] as const satisfies readonly Role[];

// Fails to compile if the contract gains a role this app does not label.
type UnlabelledRole = Exclude<Role, (typeof ROLE_VALUES)[number]>;
const _everyRoleIsCovered: UnlabelledRole[] = [];
void _everyRoleIsCovered;

export function isRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLE_VALUES as readonly string[]).includes(value);
}

export function parseRoles(value: unknown): readonly Role[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isRole);
}
