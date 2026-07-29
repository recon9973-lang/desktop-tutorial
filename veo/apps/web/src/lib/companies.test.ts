import { describe, expect, it } from 'vitest';

import { toOrigin } from './companies';

/**
 * 직원이 주소창에서 복사해 붙이는 값은 대개 깨끗하지 않다 — 경로가 붙어 있고, 스킴이
 * 없고, 공백이 딸려 온다. 사이트 등록은 `https://호스트` 만 받고 나머지를 거부하므로,
 * 여기서 다듬지 않으면 "붙여넣었는데 저장이 안 된다" 가 된다.
 *
 * 다만 다듬는 것과 **없던 허가를 만들어 주는 것**은 다르다. 자격정보가 박힌 주소나
 * `javascript:` 같은 스킴은 조용히 고치지 않고 거부한다.
 */
describe('toOrigin', () => {
  it('스킴이 없으면 https 로 읽는다', () => {
    expect(toOrigin('ondam.co.kr')).toBe('https://ondam.co.kr');
  });

  it('경로와 질의를 떼어 낸다', () => {
    expect(toOrigin('https://ondam.co.kr/about?utm_source=x')).toBe('https://ondam.co.kr');
  });

  it('앞뒤 공백을 무시한다', () => {
    expect(toOrigin('  https://ondam.co.kr  ')).toBe('https://ondam.co.kr');
  });

  it('포트는 호스트의 일부라 남긴다', () => {
    expect(toOrigin('https://ondam.co.kr:8443/x')).toBe('https://ondam.co.kr:8443');
  });

  it('http 도 받는다 — 아직 https 가 아닌 고객 사이트가 있고, 그건 진단 결과에 나온다', () => {
    expect(toOrigin('http://ondam.co.kr')).toBe('http://ondam.co.kr');
  });

  it('자격정보가 박힌 주소는 거부한다', () => {
    expect(toOrigin('https://user:pw@ondam.co.kr')).toBeNull();
  });

  it('http·https 가 아닌 스킴은 거부한다', () => {
    expect(toOrigin('javascript:alert(1)')).toBeNull();
    expect(toOrigin('file:///etc/passwd')).toBeNull();
  });

  it('빈 값은 거부한다', () => {
    expect(toOrigin('')).toBeNull();
    expect(toOrigin('   ')).toBeNull();
  });

  it('주소로 읽을 수 없으면 거부한다', () => {
    expect(toOrigin('h ttp://x')).toBeNull();
  });
});
