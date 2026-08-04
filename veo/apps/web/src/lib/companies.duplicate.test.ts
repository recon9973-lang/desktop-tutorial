/**
 * 한 주소는 한 자리에만 등록된다.
 *
 * 주소만 넣고 재는 길에는 이 검사가 처음부터 있었는데, 업체 관리에서 손으로 등록하는
 * 길에는 없었다. 그래서 진단이 자동으로 만들어 둔 업체와 사람이 등록한 업체가 같은
 * 주소로 나란히 남았다 — 화면에 같은 업체가 두 번 나오고, 이력은 두 갈래로 갈린다
 * (사용자 지적: 참사랑한의원이 두 번).
 *
 * 여기서 지키는 것 셋:
 * 1. 이미 있는 주소면 **만들기 전에** 멈춘다.
 * 2. 어느 업체에 있는지 말한다 — 그래야 목록을 눈으로 훑지 않는다.
 * 3. 목록을 못 읽었으면 "없다" 로 삼지 않는다. 그러면 중복이 생긴다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const callConsoleApi = vi.fn();
const readAllPages = vi.fn();

vi.mock('server-only', () => ({}));
vi.mock('@/lib/console-api', () => ({ callConsoleApi, readAllPages }));

const { createCompany, addSite } = await import('./companies');

const TAKEN = 'https://chamsarang1075.com';

/** 참사랑한의원이 그 주소를 이미 갖고 있는 상태. */
function registryHas(origin: string) {
  readAllPages.mockImplementation((path: string) => {
    if (path.startsWith('/api/customers')) {
      return Promise.resolve({ ok: true, data: [{ id: 'c1', name: '참사랑한의원' }], meta: {} });
    }
    if (path.startsWith('/api/projects')) {
      return Promise.resolve({
        ok: true,
        data: [{ id: 'p1', customer_id: 'c1', name: '참사랑한의원' }],
        meta: {},
      });
    }
    return Promise.resolve({
      ok: true,
      data: [{ id: 's1', project_id: 'p1', origin, display_name: '참사랑한의원' }],
      meta: {},
    });
  });
}

/** 아무것도 등록돼 있지 않은 상태. */
function registryEmpty() {
  readAllPages.mockResolvedValue({ ok: true, data: [], meta: {} });
}

beforeEach(() => {
  callConsoleApi.mockReset();
  readAllPages.mockReset();
  callConsoleApi.mockResolvedValue({ ok: true, data: { id: 'new' }, meta: {} });
});

describe('이미 등록된 주소는 다시 만들지 않는다', () => {
  it('업체 등록 — 같은 주소면 거절한다', async () => {
    registryHas(TAKEN);

    const result = await createCompany('참사랑한의원', TAKEN, 'abcd1234');

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe('DUPLICATE');
  });

  it('업체명이 달라도 주소가 같으면 거절한다 — 갈라지는 것은 이력이다', async () => {
    registryHas(TAKEN);

    // 진단이 호스트 이름으로 만들어 둔 자리에, 사람이 정식 이름으로 다시 등록하는 상황.
    const result = await createCompany('전혀 다른 이름', TAKEN, 'abcd1234');

    expect(result.ok).toBe(false);
  });

  it('어느 업체에 있는지 말한다', async () => {
    registryHas(TAKEN);

    const result = await createCompany('참사랑한의원', TAKEN, 'abcd1234');

    if (!result.ok && result.reason === 'DUPLICATE') {
      expect(result.owner).toBe('참사랑한의원');
    } else {
      expect.unreachable('중복으로 거절했어야 한다');
    }
  });

  it('거절할 때는 아무것도 만들지 않는다', async () => {
    registryHas(TAKEN);

    await createCompany('참사랑한의원', TAKEN, 'abcd1234');

    // 절반만 만들어 두면 URL 없는 업체가 남는다.
    expect(callConsoleApi).not.toHaveBeenCalled();
  });

  it('기존 업체에 URL 을 더할 때도 막는다', async () => {
    registryHas(TAKEN);

    const result = await addSite('c1', '참사랑한의원', TAKEN, 'abcd1234');

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe('DUPLICATE');
  });

  it('주소 표기가 달라도 같은 주소로 본다', async () => {
    registryHas(TAKEN);

    // 주소창에서 복사하면 경로가 딸려 온다. 다듬은 뒤에 비교해야 한다.
    const result = await createCompany('참사랑한의원', 'chamsarang1075.com/about', 'abcd1234');

    expect(result.ok).toBe(false);
  });
});

describe('막지 않아야 할 것은 막지 않는다', () => {
  it('처음 보는 주소는 그대로 만든다', async () => {
    registryEmpty();

    const result = await createCompany('온담의원', 'https://ondam.co.kr', 'abcd1234');

    expect(result.ok).toBe(true);
    // 고객 → 프로젝트 → 사이트 세 번.
    expect(callConsoleApi).toHaveBeenCalledTimes(3);
  });
});

describe('목록을 못 읽으면 "없다" 로 삼지 않는다', () => {
  it('읽기가 실패하면 만들지 않고 실패로 돌려준다', async () => {
    readAllPages.mockResolvedValue({ ok: false, reason: 'SERVER_ERROR', message: null });

    const result = await createCompany('온담의원', 'https://ondam.co.kr', 'abcd1234');

    expect(result.ok).toBe(false);
    // 못 읽은 것을 "비어 있다" 로 읽으면, 장애 시간에 만든 등록이 전부 중복이 된다.
    expect(callConsoleApi).not.toHaveBeenCalled();
  });
});
