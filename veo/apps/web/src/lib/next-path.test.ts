import { describe, expect, it } from 'vitest';

import { DEFAULT_CONSOLE_PATH, loginPathFor, safeNextPath } from './next-path';

describe('safeNextPath', () => {
  it('keeps an in-app path with its query string', () => {
    expect(safeNextPath('/console/issues?severity=BLOCKER')).toBe(
      '/console/issues?severity=BLOCKER',
    );
  });

  it('rejects an absolute URL to another origin', () => {
    expect(safeNextPath('https://evil.example/steal')).toBeNull();
  });

  it('rejects a protocol-relative URL', () => {
    expect(safeNextPath('//evil.example/steal')).toBeNull();
    expect(safeNextPath('/\\evil.example')).toBeNull();
  });

  it('rejects a scheme-bearing value even when it starts with a slash', () => {
    expect(safeNextPath('/\t/evil.example')).toBeNull();
    expect(safeNextPath('javascript:alert(1)')).toBeNull();
  });

  it('rejects a relative path with no leading slash', () => {
    expect(safeNextPath('console/issues')).toBeNull();
  });

  it('rejects the login page itself so sign-in cannot loop', () => {
    expect(safeNextPath('/login')).toBeNull();
    expect(safeNextPath('/login?next=/console/dashboard')).toBeNull();
  });

  it('rejects the session endpoints', () => {
    expect(safeNextPath('/api/session')).toBeNull();
  });

  it('returns null for anything that is not a string', () => {
    expect(safeNextPath(undefined)).toBeNull();
    expect(safeNextPath(null)).toBeNull();
    expect(safeNextPath(['/console/dashboard'])).toBeNull();
    expect(safeNextPath('')).toBeNull();
  });
});

describe('loginPathFor', () => {
  it('carries a safe destination so sign-in returns the user where they were', () => {
    expect(loginPathFor('/console/issues?severity=BLOCKER')).toBe(
      '/login?next=%2Fconsole%2Fissues%3Fseverity%3DBLOCKER',
    );
  });

  it('drops an unsafe destination rather than passing it on', () => {
    expect(loginPathFor('https://evil.example')).toBe('/login');
  });

  it('has a bare form when there is no destination', () => {
    expect(loginPathFor(null)).toBe('/login');
  });
});

describe('DEFAULT_CONSOLE_PATH', () => {
  it('is a console route', () => {
    expect(DEFAULT_CONSOLE_PATH.startsWith('/console/')).toBe(true);
    expect(safeNextPath(DEFAULT_CONSOLE_PATH)).toBe(DEFAULT_CONSOLE_PATH);
  });
});
