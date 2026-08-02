/**
 * 무료 키워드 조회 폼 — E3 배선의 성질.
 *
 * 1. 값이 없는 것은 0 이 아니다 — 비공개·최소 단위 미만은 그렇게 쓰인다.
 * 2. 엔진의 거절 사유("최대 5개" 등)는 엔진의 문장 그대로 나온다.
 * 3. 서버 안내문(notices_ko·scope notice)은 화면이 다시 쓰지 않고 그대로 전달한다.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { KeywordLookupForm } from './KeywordLookupForm';
import type { KeywordLookupResult } from '@/lib/public-keywords-types';

const RESULT: KeywordLookupResult = {
  searchadState: 'ENABLED',
  rows: [
    {
      keyword: '강남 피부과',
      normalizedKeyword: '강남피부과',
      total: { value: 42100, quality: 'EXACT' },
      pc: { value: null, quality: 'SUPPRESSED_BY_PROVIDER' },
      mobile: { value: null, quality: 'BELOW_PROVIDER_THRESHOLD' },
      competitionLabel: '높음',
    },
  ],
  noticesKo: ['서버가 보낸 안내문'],
  scopeNoticeKo: '무료 조회 범위 안내',
};

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

async function lookUp(keyword = '강남 피부과'): Promise<void> {
  render(<KeywordLookupForm />);
  await userEvent.type(screen.getByRole('textbox'), keyword);
  await userEvent.click(screen.getByRole('button', { name: '조회' }));
}

describe('값의 부재를 0으로 바꾸지 않는다', () => {
  it('받은 숫자는 그대로, 없는 값은 그 이유로 그린다', async () => {
    mockFetch(200, { result: RESULT });
    await lookUp();

    expect(await screen.findByText('42,100')).toBeInTheDocument();
    expect(screen.getByText('비공개')).toBeInTheDocument();
    expect(screen.getByText('최소 단위 미만')).toBeInTheDocument();
    expect(screen.getByText('높음')).toBeInTheDocument();
    // 정규화된 키워드가 다르면 무엇을 기준으로 조회했는지 보인다.
    expect(screen.getByText(/조회 기준: 강남피부과/)).toBeInTheDocument();
  });

  it('서버 안내문을 다시 쓰지 않고 그대로 전달한다', async () => {
    mockFetch(200, { result: RESULT });
    await lookUp();

    expect(await screen.findByText('서버가 보낸 안내문')).toBeInTheDocument();
    expect(screen.getByText('무료 조회 범위 안내')).toBeInTheDocument();
  });
});

describe('거절은 엔진의 문장으로', () => {
  it('422 의 사유가 그대로 화면에 나온다', async () => {
    mockFetch(422, { message: '무료 조회는 한 번에 최대 5개 키워드까지 가능합니다.' });
    await lookUp();

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent('무료 조회는 한 번에 최대 5개 키워드까지 가능합니다.');
  });

  it('빈 입력으로는 아무 요청도 나가지 않는다', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    render(<KeywordLookupForm />);

    expect(screen.getByRole('button', { name: '조회' })).toBeDisabled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
