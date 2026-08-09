/**
 * 같은 주소가 여러 업체에 걸린 것을 **찾아낸다.**
 *
 * 막는 관문은 등록 폼에 있다(`findCompanyByOrigin`, 2026-08-08). 그 전에 들어간 것은
 * 남아 있고 — 참사랑한의원이 같은 주소로 세 번 — 엔진의 유일성 제약은
 * `(project_id, origin)` 이라 **프로젝트가 다르면 통과**하므로 DB 도 오류로 보지 않는다.
 * 사람이 목록을 눈으로 훑어야 찾는데, 업체가 늘면 못 찾는다.
 */

import { describe, expect, it } from 'vitest';

import { findDuplicateOrigins } from './companies';
import type { Company } from './companies';

function company(name: string, origins: string[]): Company {
  return {
    customerId: `cus-${name}`,
    name,
    industry: null,
    address: null,
    isRegistered: true,
    projects: [],
    sites: origins.map((origin, index) => ({
      siteId: `${name}-${index}`,
      origin,
      displayName: origin,
      isPrimary: index === 0,
      projectId: `prj-${name}-${index}`,
    })),
  };
}

describe('업체를 건너뛴 중복만 찾는다', () => {
  it('두 업체가 같은 주소를 쓰면 찾는다', () => {
    const found = findDuplicateOrigins([
      company('참사랑한의원', ['https://a.kr']),
      company('참사랑한의원 (2)', ['https://a.kr']),
    ]);

    expect(found).toHaveLength(1);
    expect(found[0]?.origin).toBe('https://a.kr');
    expect(found[0]?.companies.map((one) => one.name)).toEqual([
      '참사랑한의원',
      '참사랑한의원 (2)',
    ]);
  });

  it('세 곳이면 셋 다 든다', () => {
    const found = findDuplicateOrigins([
      company('가', ['https://a.kr']),
      company('나', ['https://a.kr']),
      company('다', ['https://a.kr']),
    ]);

    expect(found[0]?.companies).toHaveLength(3);
  });

  it('한 업체가 같은 주소를 두 번 가진 것은 세지 않는다', () => {
    // 그것은 엔진의 (project_id, origin) 제약이 업체 안에서 막는다. 여기서 찾는 것은
    // **업체를 건너뛴** 중복이다.
    expect(findDuplicateOrigins([company('가', ['https://a.kr', 'https://a.kr'])])).toEqual([]);
  });

  it('겹치지 않으면 아무것도 내지 않는다', () => {
    expect(
      findDuplicateOrigins([company('가', ['https://a.kr']), company('나', ['https://b.kr'])]),
    ).toEqual([]);
  });

  it('여러 곳이 걸린 주소가 위로 온다', () => {
    const found = findDuplicateOrigins([
      company('가', ['https://two.kr', 'https://three.kr']),
      company('나', ['https://two.kr', 'https://three.kr']),
      company('다', ['https://three.kr']),
    ]);

    expect(found[0]?.origin).toBe('https://three.kr');
    expect(found[0]?.companies).toHaveLength(3);
  });

  it('업체가 없으면 빈 목록', () => {
    expect(findDuplicateOrigins([])).toEqual([]);
  });
});
