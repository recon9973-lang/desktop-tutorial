import { describe, expect, it } from 'vitest';

import { normalizeScanTarget } from './scan-target';

/**
 * 사람이 주소창에서 복사해 오는 형태는 한 가지가 아니다. 여기서 막히면 "이 도구는
 * 내 주소를 못 알아먹는다"가 되고, 그건 점수가 틀린 것보다 빨리 신뢰를 잃는다.
 */
describe('normalizeScanTarget — 사람이 실제로 치는 형태', () => {
  it.each([
    ['koreahospital.com', 'https://koreahospital.com'],
    ['www.koreahospital.com', 'https://www.koreahospital.com'],
    ['https://koreahospital.com', 'https://koreahospital.com'],
    ['http://koreahospital.com', 'http://koreahospital.com'],
    ['  koreahospital.com  ', 'https://koreahospital.com'],
    ['KoreaHospital.COM', 'https://koreahospital.com'],
  ])('%s → %s', (typed, expected) => {
    expect(normalizeScanTarget(typed)).toBe(expected);
  });

  it('경로와 질의를 지우지 않는다 — 특정 페이지를 진단하려는 사람이 있다', () => {
    expect(normalizeScanTarget('koreahospital.com/about?tab=2')).toBe(
      'https://koreahospital.com/about?tab=2',
    );
  });

  it('한글 도메인을 punycode 로 바꿔 받는다', () => {
    // 값은 URL 표준이 정한다. 손으로 적어 두면 틀리기 쉬워서, 실제 변환 결과를 고정한다.
    expect(normalizeScanTarget('병원.한국')).toBe('https://xn--om3bw6p.xn--3e0b707e');
  });

  it('맨 끝 슬래시만 있는 루트는 그대로 둔다', () => {
    expect(normalizeScanTarget('koreahospital.com/')).toBe('https://koreahospital.com/');
  });
});

describe('normalizeScanTarget — 거절해야 하는 것', () => {
  it.each([
    ['', '빈 값'],
    ['   ', '공백뿐'],
    ['그냥 한글 문장', '점이 없어 도메인이 아님'],
    ['javascript:alert(1)', 'http(s) 가 아닌 스킴'],
    ['file:///etc/passwd', '로컬 파일'],
    ['ftp://example.com', 'http(s) 가 아닌 스킴'],
    ['http://localhost', '내부 주소'],
    ['http://127.0.0.1', '내부 주소'],
    ['http://192.168.0.1', '사설 대역'],
    ['http://[::1]', '내부 주소'],
  ])('%s 는 거절한다 (%s)', (typed) => {
    expect(normalizeScanTarget(typed)).toBeNull();
  });

  it('서버의 SSRF 방어를 대신하지 않는다 — 화면에서 걸러도 서버는 다시 검사한다', () => {
    // 이 테스트는 값을 확인하기보다 의도를 고정한다. 여기 목록이 전부라고 믿고
    // 서버 검사를 빼면, API 를 직접 부르는 경로가 그대로 열린다.
    expect(normalizeScanTarget('http://169.254.169.254')).toBeNull();
  });
});
