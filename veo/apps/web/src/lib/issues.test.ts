import { describe, expect, it } from 'vitest';

import {
  claimedButUnverified,
  evidenceKindLabel,
  inWorkOrder,
  ownerLabel,
  type Issue,
} from './issues';

/**
 * 이 파일이 지키는 규칙 하나: **수정 보고는 해결이 아니다.**
 *
 * 그 규칙이 깨지는 자리는 늘 합계다 — 누군가 "열린 건수" 에서 `FIX_CLAIMED` 를 빼면
 * 화면은 깨끗해지고 사이트는 그대로다.
 */

function issue(over: Partial<Issue> = {}): Issue {
  return {
    id: 'i-1',
    project_id: 'p-1',
    check_id: 'seo.title.present',
    severity: 'MAJOR',
    state: 'OPEN',
    state_label_ko: '미확인',
    is_open: true,
    title_ko: '제목 태그가 없습니다',
    business_impact_ko: null,
    affected_url_count: 3,
    remediation_owner: 'DEVELOPER',
    recurrence_count: 0,
    assigned_to: null,
  summary_ko: '요약',
    human_transitions: [],
    ...over,
  };
}

describe('재측정을 기다리는 건수', () => {
  it('수정 보고와 재측정 대기를 함께 센다', () => {
    const count = claimedButUnverified([
      issue({ id: 'a', state: 'FIX_CLAIMED' }),
      issue({ id: 'b', state: 'VERIFYING' }),
      issue({ id: 'c', state: 'OPEN' }),
    ]);

    expect(count).toBe(2);
  });

  it('재측정으로 확인된 해결은 여기에 들어가지 않는다', () => {
    const count = claimedButUnverified([
      issue({ state: 'VERIFIED_RESOLVED', is_open: false, state_label_ko: '재측정으로 해결 확인' }),
    ]);

    expect(count).toBe(0);
  });
});

describe('줄 세우는 순서', () => {
  it('재발한 건이 먼저 온다', () => {
    // 한 번 해결로 확인됐다가 다시 나온 문제는, 같은 심각도의 처음 보는 문제와
    // 무게가 다르다.
    const ordered = inWorkOrder([
      issue({ id: 'fresh', severity: 'BLOCKER', recurrence_count: 0 }),
      issue({ id: 'again', severity: 'MINOR', recurrence_count: 1 }),
    ]);

    expect(ordered.map((one) => one.id)).toEqual(['again', 'fresh']);
  });

  it('재발 횟수가 같으면 심각한 것이 먼저다', () => {
    const ordered = inWorkOrder([
      issue({ id: 'minor', severity: 'MINOR' }),
      issue({ id: 'blocker', severity: 'BLOCKER' }),
      issue({ id: 'major', severity: 'MAJOR' }),
    ]);

    expect(ordered.map((one) => one.id)).toEqual(['blocker', 'major', 'minor']);
  });

  it('모르는 심각도를 맨 앞에 세우지 않는다', () => {
    // 명세에 없는 값이 들어왔을 때 조용히 최상위로 올라가면, 새 심각도를 넣은 사람이
    // 목록 전체를 뒤집어 놓고도 모른다.
    const ordered = inWorkOrder([
      issue({ id: 'known', severity: 'MINOR' }),
      issue({ id: 'unknown', severity: 'WHATEVER' }),
    ]);

    expect(ordered.map((one) => one.id)).toEqual(['known', 'unknown']);
  });

  it('원본 배열을 뒤집어 놓지 않는다', () => {
    const source = [issue({ id: 'a', severity: 'MINOR' }), issue({ id: 'b', severity: 'BLOCKER' })];
    inWorkOrder(source);

    expect(source.map((one) => one.id)).toEqual(['a', 'b']);
  });
});

describe('담당 직군', () => {
  it('코드를 사람 말로 바꾼다', () => {
    expect(ownerLabel('DEVELOPER')).toBe('개발');
  });

  it('모르는 값은 지어내지 않고 그대로 보인다', () => {
    expect(ownerLabel('LEGAL')).toBe('LEGAL');
  });
});

describe('근거 종류', () => {
  it('코드를 사람 말로 바꾼다', () => {
    expect(evidenceKindLabel('http_response')).toBe('서버 응답');
  });

  it('모르는 종류는 지어내지 않고 그대로 보인다', () => {
    // 지어낸 한국어 이름은 근거가 무엇인지에 대한 거짓 정보가 된다.
    expect(evidenceKindLabel('crux_record')).toBe('crux_record');
  });
});
