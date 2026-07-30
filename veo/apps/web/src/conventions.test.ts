import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Next.js 의 파일 규약을 두 벌 두지 않는다.
 *
 * 실제로 겪은 일: Next.js 16 이 `middleware` 규약을 `proxy` 로 바꿨는데, 그 사실을
 * 확인하지 않고 `middleware.ts` 를 새로 만들었다. 이미 있던 `proxy.ts` 와 둘 다
 * 존재하게 되어 빌드가 거부했다 — **그런데 그 오류는 `next build` 에서만 난다.**
 * 타입체크·테스트·린트는 전부 통과했고, 그래서 "됐습니다" 라고 말한 채 배포했다.
 * 화면은 옛 코드로 남았고, 고쳤다던 기능은 실제로 없었다.
 *
 * 이 검사는 그 한 가지를 막는다. 근본 대책은 CI 가 `next build` 까지 돌리는 것이고
 * (`.github/workflows/ci.yml` 의 `web` 작업), 이것은 그 위에 얹는 빠른 그물이다.
 */

const SRC = join(process.cwd(), 'src');

describe('Next.js 파일 규약', () => {
  it('middleware 와 proxy 를 동시에 두지 않는다', () => {
    const middleware = existsSync(join(SRC, 'middleware.ts'));
    const proxy = existsSync(join(SRC, 'proxy.ts'));

    expect(
      middleware && proxy,
      'Next.js 16 은 proxy.ts 만 쓴다. 둘 다 있으면 빌드가 거부한다.',
    ).toBe(false);
  });

  it('요청 가로채기는 proxy.ts 하나뿐이다', () => {
    expect(existsSync(join(SRC, 'proxy.ts'))).toBe(true);
    expect(existsSync(join(SRC, 'middleware.ts'))).toBe(false);
  });
});
