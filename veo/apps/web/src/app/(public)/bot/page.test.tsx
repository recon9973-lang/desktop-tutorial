// @vitest-environment node
/**
 * VEOBot 안내 페이지.
 *
 * 이 페이지는 사이트 운영자가 로그에서 낯선 봇을 보고 찾아오는 곳이다. 2026-08-06
 * 실측에서 **HTTP 404** 였다 — 우리 User-Agent 가 이 주소를 가리키면서 안내는 없었다.
 *
 * 여기서 지키는 것은 디자인이 아니라 **적힌 값이 사실인가** 다. 값이 코드와 갈라지면
 * 운영자가 그대로 복사한 robots.txt 규칙이 우리를 막지 못한다 — 안내가 있으나 마나가
 * 되고, 오히려 "차단했는데도 계속 온다" 는 신뢰 문제를 만든다.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const source = readFileSync(join(__dirname, 'page.tsx'), 'utf8');

/** 엔진이 실제로 보내는 값. `apps/api/src/veo/common/security/fetcher.py` 와 같아야 한다. */
const USER_AGENT = 'VEOBot/1.0 (+https://veo.seokorea.org/bot)';
const FROM = 'bot@seokorea.org';
/** robots.txt 매칭 이름. `veo.seo.parsing.robots.CRAWLER_AGENT_NAME` 의 표기형. */
const ROBOTS_TOKEN = 'VEOBot';

describe('적힌 신원이 실제와 같은가', () => {
  it('User-Agent 문자열을 그대로 싣는다', () => {
    expect(source).toContain(USER_AGENT);
  });

  it('연락처를 싣는다', () => {
    expect(source).toContain(FROM);
  });

  it('차단 방법을 robots.txt 규칙으로 보여준다', () => {
    expect(source).toContain(ROBOTS_TOKEN);
    expect(source).toContain('Disallow: /');
  });
});

describe('운영자가 알아야 할 것을 빠뜨리지 않는가', () => {
  it.each([
    ['연결당 요청 간격', '최소 1초'],
    ['동시 연결', '2개 이하'],
    // 연결이 2개이므로 서버가 받는 것은 초당 2회다. 간격만 적어 두면 그 사실이
    // 가려진다 — 이 페이지는 우리가 실제로 하는 일을 적는 곳이다.
    ['서버가 실제로 받는 밀도', '최대 2회'],
    ['문서 크기', '최대 2MB'],
  ])('%s 를 밝힌다', (_label, value) => {
    expect(source).toContain(value);
  });

  it('다른 크롤러를 사칭하지 않는다고 밝힌다', () => {
    expect(source).toContain('다른 크롤러의 이름을 쓰지 않습니다');
  });
});
