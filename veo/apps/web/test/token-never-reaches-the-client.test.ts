// @vitest-environment node
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = path.join(import.meta.dirname, '..', 'src');

interface SourceFile {
  readonly relativePath: string;
  readonly text: string;
  /** `text` with comments removed, so prose about a hazard is not read as one. */
  readonly code: string;
  readonly isClient: boolean;
  readonly isTest: boolean;
}

function stripComments(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1');
}

function collect(dir: string, acc: SourceFile[] = []): SourceFile[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collect(full, acc);
      continue;
    }
    if (!/\.(ts|tsx)$/.test(entry.name)) continue;

    const text = readFileSync(full, 'utf8');
    acc.push({
      relativePath: path.relative(SRC, full),
      text,
      code: stripComments(text),
      isClient: /^\s*(['"])use client\1/m.test(text.slice(0, 200)),
      isTest: /\.test\.tsx?$/.test(entry.name),
    });
  }
  return acc;
}

const FILES = collect(SRC);
const PRODUCTION = FILES.filter((file) => !file.isTest);
const CLIENT = PRODUCTION.filter((file) => file.isClient);

/** Modules that hold, fetch, or set the access token. */
const SERVER_ONLY_MODULES = ['@/lib/session', '@/lib/auth-api', '@/lib/session-cookie'];

describe('the source tree', () => {
  it('has files to inspect', () => {
    expect(PRODUCTION.length).toBeGreaterThan(10);
    expect(CLIENT.length).toBeGreaterThan(0);
  });
});

/**
 * 웹 스토리지를 만질 수 있는 유일한 모듈. 2026-08-02 제품 결정 — 공개 진단의
 * 측정 이력(주소·점수·날짜)을 브라우저에만 남긴다. 이 목록에 파일을 더하려면
 * 아래 "the storage module cannot hold a token" 시험이 그 파일에도 성립해야 한다.
 */
const STORAGE_ALLOWLIST = ['lib/scan-history.ts'];

describe('the access token never reaches the browser', () => {
  it('is never written to web storage anywhere in the app', () => {
    const offenders = PRODUCTION.filter((file) =>
      /\b(localStorage|sessionStorage|indexedDB)\b/.test(file.code),
    )
      .map((file) => file.relativePath)
      .filter((relativePath) => !STORAGE_ALLOWLIST.includes(relativePath));
    expect(offenders).toEqual([]);
  });

  it('the storage module cannot hold a token', () => {
    for (const allowed of STORAGE_ALLOWLIST) {
      const file = PRODUCTION.find((candidate) => candidate.relativePath === allowed);
      // 목록에 있는데 파일이 없으면 허용 목록이 죽은 항목을 들고 있는 것이다.
      expect(file, allowed).toBeDefined();
      // 토큰이라는 단어 자체가 등장하지 않는다 — 실수로도 저장할 수 없다.
      expect(/token/i.test(file!.code), `${allowed} mentions a token`).toBe(false);
      // 토큰을 쥐는 서버 전용 모듈을 임포트하지 않는다.
      for (const serverModule of SERVER_ONLY_MODULES) {
        expect(file!.code.includes(serverModule), `${allowed} imports ${serverModule}`).toBe(false);
      }
    }
  });

  it('is never written to a client-readable cookie', () => {
    const offenders = PRODUCTION.filter((file) => /document\s*\.\s*cookie/.test(file.code)).map(
      (file) => file.relativePath,
    );
    expect(offenders).toEqual([]);
  });

  it('is never handed to a client component through a session module import', () => {
    const offenders = CLIENT.filter((file) =>
      SERVER_ONLY_MODULES.some((serverModule) =>
        new RegExp(`from\\s+['"]${serverModule}['"]`).test(
          // A type-only import is erased at build time and carries no value.
          file.code.replace(/import\s+type\s+[^;]+;/g, ''),
        ),
      ),
    ).map((file) => file.relativePath);
    expect(offenders).toEqual([]);
  });

  it('keeps the session modules marked server-only so a bad import fails the build', () => {
    for (const serverModule of SERVER_ONLY_MODULES) {
      const relative = `${serverModule.replace('@/', '')}.ts`;
      const file = PRODUCTION.find((candidate) => candidate.relativePath === relative);
      expect(file, relative).toBeDefined();
      expect(file?.text, relative).toMatch(/^import 'server-only';/m);
      expect(file?.isClient, relative).toBe(false);
    }
  });

  it('exposes no token, secret or password through a NEXT_PUBLIC_ variable', () => {
    const publicVars = PRODUCTION.flatMap((file) => [
      ...file.text.matchAll(/NEXT_PUBLIC_[A-Z0-9_]+/g),
    ]).map((match) => match[0]);

    for (const name of publicVars) {
      expect(name).not.toMatch(/TOKEN|SECRET|PASSWORD|KEY|SESSION/);
    }
  });

  it('names the token cookie in exactly one module', () => {
    const declarations = PRODUCTION.filter((file) =>
      /veo_console_session/.test(file.code),
    ).map((file) => file.relativePath);
    expect(declarations).toEqual(['lib/session-cookie.ts']);
  });

  it('sends the bearer header only from server-side modules', () => {
    const offenders = CLIENT.filter((file) => /Bearer /.test(file.code)).map(
      (file) => file.relativePath,
    );
    expect(offenders).toEqual([]);
  });
});

describe('client components stay inside their boundary', () => {
  it('never import next/headers', () => {
    const offenders = CLIENT.filter((file) => /from\s+['"]next\/headers['"]/.test(file.code)).map(
      (file) => file.relativePath,
    );
    expect(offenders).toEqual([]);
  });
});

describe('no placeholders survive into the product', () => {
  it('contains no TODO, FIXME or stub markers', () => {
    const offenders = PRODUCTION.filter((file) =>
      /\b(TODO|FIXME|XXX|HACK|PLACEHOLDER)\b/.test(file.text),
    ).map((file) => file.relativePath);
    expect(offenders).toEqual([]);
  });

  it('fabricates no signed-in user', () => {
    const offenders = PRODUCTION.filter((file) =>
      /(관리자로 로그인|데모 계정|샘플 계정|mockUser|fakeUser|DEMO_USER)/.test(file.text),
    ).map((file) => file.relativePath);
    expect(offenders).toEqual([]);
  });
});
