import { describe, expect, it } from 'vitest';

import { bySpecFamily, specLabel, type ScoringSpecSummary } from './scoring';

/**
 * 이 파일이 지키는 규칙 하나: **어느 판이 지금 쓰이는지 화면이 정하지 않는다.**
 *
 * 그 규칙이 깨지는 자리는 늘 정렬이다 — 누군가 "제일 큰 버전이 현재겠지" 하고 semver 비교를
 * 넣는 순간, 발행 규칙이 엔진과 화면 두 곳에 생긴다. 그러면 엔진이 1.6.0 을 쓰는데 화면은
 * 디스크에 있는 2.0.0 초안을 현재라고 말하는 날이 오고, 그날 아무것도 깨지지 않는다.
 */

function spec(over: Partial<ScoringSpecSummary> = {}): ScoringSpecSummary {
  return {
    spec_id: 'veo.seo.readiness',
    domain: 'SEO_READINESS',
    version: '1.0.0',
    status: 'PUBLISHED',
    checksum: 'a'.repeat(64),
    effective_at: '2026-07-28T00:00:00+09:00',
    methodology_owner: 'VEO-LAB',
    implementation_owner: 'VENOM',
    score_meaning_ko: '기술 준비도입니다.',
    is_rank_prediction: false,
    category_weights: {},
    is_current: false,
    ...over,
  };
}

describe('bySpecFamily', () => {
  it('명세 ID 별로 묶는다', () => {
    const families = bySpecFamily([
      spec({ spec_id: 'veo.seo.readiness', version: '1.0.0' }),
      spec({ spec_id: 'veo.seo.readiness', version: '1.1.0', is_current: true }),
      spec({ spec_id: 'veo.geo.readiness', version: '1.0.0', is_current: true }),
    ]);

    expect(families.map((family) => family.specId)).toEqual([
      'veo.seo.readiness',
      'veo.geo.readiness',
    ]);
  });

  it('엔진이 is_current 로 지목한 판만 현재가 된다', () => {
    const [family] = bySpecFamily([
      spec({ version: '1.0.0' }),
      spec({ version: '1.1.0', is_current: true }),
      spec({ version: '1.2.0' }),
    ]);

    expect(family?.current?.version).toBe('1.1.0');
    expect(family?.superseded.map((one) => one.version)).toEqual(['1.2.0', '1.0.0']);
  });

  it('버전 번호가 더 커도 엔진이 지목하지 않았으면 현재가 아니다', () => {
    // 발행 전 초안이 디스크에 있는 상황. 여기서 화면이 "제일 큰 것" 을 고르면
    // 아직 아무 점수도 내지 않은 명세를 적용 중이라고 말하게 된다.
    const [family] = bySpecFamily([
      spec({ version: '1.6.0', is_current: true }),
      spec({ version: '2.0.0', status: 'DRAFT' }),
    ]);

    expect(family?.current?.version).toBe('1.6.0');
    expect(family?.superseded.map((one) => one.version)).toEqual(['2.0.0']);
  });

  it('발행본이 하나도 없으면 현재를 지어내지 않는다', () => {
    const [family] = bySpecFamily([spec({ version: '0.9.0', status: 'DRAFT' })]);

    expect(family?.current).toBeNull();
    expect(family?.superseded).toHaveLength(1);
  });

  it('빈 목록에서 가족을 만들어 내지 않는다', () => {
    expect(bySpecFamily([])).toEqual([]);
  });
});

describe('specLabel', () => {
  it('명세 ID 와 버전을 함께 적는다 — 버전 없는 명세 이름은 리포트에서 의미가 없다', () => {
    expect(specLabel(spec({ version: '1.6.0' }))).toBe('veo.seo.readiness 1.6.0');
  });
});
