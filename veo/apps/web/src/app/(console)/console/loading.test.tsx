/**
 * 콘솔의 모든 화면에는 **누른 직후 보일 것**이 있어야 한다.
 *
 * 화면이 서버에서 그려지는 동안 표시가 없으면, 사용자는 눌린 것인지 느린 것인지 알 수
 * 없다. 규칙을 글로만 적어 두면 다음 화면을 추가하는 사람이 모른다 — 그래서 검사를
 * 붙인다(0-H).
 *
 * 지금은 `console/` 한 곳의 경계가 그 아래 전부를 덮는다. 나중에 누군가 하위 구역에
 * 자기 경계를 따로 두면 그것도 유효하므로, 여기서 확인하는 것은 **파일이 몇 개인가**가
 * 아니라 **모든 화면 위에 하나라도 있는가** 이다.
 */

import { existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const CONSOLE_DIR = dirname(fileURLToPath(import.meta.url));

/** `dir` 부터 콘솔 뿌리까지 올라가며 경계를 찾는다. */
function hasLoadingAbove(dir: string): boolean {
  let here = dir;
  for (;;) {
    if (existsSync(join(here, 'loading.tsx'))) return true;
    if (here === CONSOLE_DIR) return false;
    here = dirname(here);
  }
}

function routeDirs(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (!entry.isDirectory()) return [];
    const child = join(dir, entry.name);
    const self = existsSync(join(child, 'page.tsx')) ? [child] : [];
    return [...self, ...routeDirs(child)];
  });
}

describe('누른 직후 보일 것이 있다', () => {
  it('콘솔 화면이 하나도 빠짐없이 경계 아래에 있다', () => {
    const routes = routeDirs(CONSOLE_DIR);

    // 화면을 못 찾았는데 통과하면, 검사가 아무것도 지키지 않는다.
    expect(routes.length).toBeGreaterThan(10);
    expect(routes.filter((route) => !hasLoadingAbove(route))).toEqual([]);
  });
});
