/**
 * 거래처 대장의 소재지.
 *
 * **상호는 식별자가 아니다.** `서울치과` 는 수십 곳이고, 목록에 이름만 있으면 어느 곳을
 * 맡고 있는지 사람이 가리지 못한다.
 *
 * 여기서 지키는 것 셋 —
 *
 * 1. 넣은 소재지가 서버까지 간다.
 * 2. **빈 값은 안 보낸다.** 재 보기만 하던 자리를 거래처로 올릴 때 빈 소재지를 함께
 *    보내면, 그 자리에 적혀 있던 소재지가 지워진다.
 * 3. 진단이 자동으로 만드는 자리에는 소재지가 없다 — **모르는 것을 지어내지 않는다.**
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const callConsoleApi = vi.fn();
const readAllPages = vi.fn();

vi.mock('server-only', () => ({}));
vi.mock('@/lib/console-api', () => ({ callConsoleApi, readAllPages }));

const { createCompany, findOrCreateSiteByOrigin, listCompanies } = await import('./companies');

const ORIGIN = 'https://ondam.co.kr';

function registryEmpty(): void {
  readAllPages.mockResolvedValue({ ok: true, data: [], meta: {} });
}

/** 재 보기만 하던 자리(`is_registered: false`)가 그 주소를 갖고 있는 상태. */
function registryHasUnregistered(): void {
  readAllPages.mockImplementation((path: string) => {
    if (path.startsWith('/api/customers')) {
      return Promise.resolve({
        ok: true,
        data: [{ id: 'c1', name: 'ondam.co.kr', is_registered: false }],
        meta: {},
      });
    }
    if (path.startsWith('/api/projects')) {
      return Promise.resolve({ ok: true, data: [{ id: 'p1', customer_id: 'c1' }], meta: {} });
    }
    return Promise.resolve({
      ok: true,
      data: [{ id: 's1', project_id: 'p1', origin: ORIGIN }],
      meta: {},
    });
  });
}

/** `/api/customers` 로 간 본문. */
function customerBody(): Record<string, unknown> {
  const call = callConsoleApi.mock.calls.find((one) =>
    String(one[0]).startsWith('/api/customers'),
  );
  return (call?.[1] as { body?: Record<string, unknown> })?.body ?? {};
}

beforeEach(() => {
  callConsoleApi.mockReset();
  readAllPages.mockReset();
  callConsoleApi.mockResolvedValue({ ok: true, data: { id: 'new' }, meta: {} });
});

describe('등록할 때', () => {
  it('소재지를 서버로 보낸다', async () => {
    registryEmpty();

    await createCompany('온담의원', ORIGIN, 'abcd1234', '대구 수성구 동대구로 31');

    expect(customerBody()['address']).toBe('대구 수성구 동대구로 31');
  });

  it('앞뒤 공백을 떼고 보낸다', async () => {
    registryEmpty();

    await createCompany('온담의원', ORIGIN, 'abcd1234', '  대구 수성구 동대구로 31  ');

    expect(customerBody()['address']).toBe('대구 수성구 동대구로 31');
  });

  it('비워 두면 아예 보내지 않는다 — 빈 문자열을 저장하지 않는다', async () => {
    registryEmpty();

    await createCompany('온담의원', ORIGIN, 'abcd1234');

    expect(customerBody()).not.toHaveProperty('address');
  });
});

describe('재 보기만 하던 자리를 거래처로 올릴 때', () => {
  it('소재지를 함께 채운다 — 그때가 처음 아는 시점인 경우가 많다', async () => {
    registryHasUnregistered();

    await createCompany('온담의원', ORIGIN, 'abcd1234', '대구 수성구 동대구로 31');

    expect(customerBody()).toMatchObject({
      is_registered: true,
      address: '대구 수성구 동대구로 31',
    });
  });

  it('소재지를 안 넣었으면 보내지 않는다 — 적혀 있던 값이 지워진다', async () => {
    registryHasUnregistered();

    await createCompany('온담의원', ORIGIN, 'abcd1234');

    expect(customerBody()).not.toHaveProperty('address');
    expect(customerBody()['is_registered']).toBe(true);
  });
});

describe('진단이 자동으로 자리를 만들 때', () => {
  it('소재지를 지어내지 않는다', async () => {
    /* 아는 것이 주소 하나뿐이다. 사람이 거래처로 올릴 때 채운다. */
    registryEmpty();

    await findOrCreateSiteByOrigin(ORIGIN, 'abcd1234');

    expect(customerBody()).not.toHaveProperty('address');
    expect(customerBody()['is_registered']).toBe(false);
  });
});

describe('목록을 읽을 때', () => {
  it('소재지를 함께 읽는다', async () => {
    readAllPages.mockImplementation((path: string) => {
      if (path.startsWith('/api/customers')) {
        return Promise.resolve({
          ok: true,
          data: [{ id: 'c1', name: '서울치과', address: '서울 강남구 테헤란로 1' }],
          meta: {},
        });
      }
      return Promise.resolve({ ok: true, data: [], meta: {} });
    });

    const outcome = await listCompanies();

    expect(outcome.ok && outcome.data[0]?.address).toBe('서울 강남구 테헤란로 1');
  });

  it('소재지가 없으면 null 이다 — 빈 문자열과 구별한다', async () => {
    readAllPages.mockImplementation((path: string) => {
      if (path.startsWith('/api/customers')) {
        return Promise.resolve({ ok: true, data: [{ id: 'c1', name: '서울치과' }], meta: {} });
      }
      return Promise.resolve({ ok: true, data: [], meta: {} });
    });

    const outcome = await listCompanies();

    expect(outcome.ok && outcome.data[0]?.address).toBeNull();
  });
});
