/**
 * 공개 SEO 진단 화면 — 확정 시안(2026-08-02)의 성질.
 *
 * 1. 화면은 숫자를 만들지 않는다 — 점수·카운트·+N점 전부 서버 값 그대로 그린다.
 * 2. 필터 칩은 서버 카운트를 보여주고, 누르면 그 상태만 남는다.
 * 3. "더보기" 를 열면 조치 코드가 나온다. 통과·측정 불가에는 코드가 없다.
 * 4. 측정 불가는 이유와 함께 나온다 — 통과처럼 보이면 안 된다.
 * 5. 점수 밖 항목은 "점수 밖" 배지를 단다.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { PublicChecker } from './PublicChecker';
import type { ScanCheckRow, ScanResult } from '@/lib/scan-api-types';

function checkRow(overrides: Partial<ScanCheckRow>): ScanCheckRow {
  return {
    checkId: 'seo.x',
    title: '검사',
    categoryId: 'cat',
    categoryName: '영역',
    severity: 'MAJOR',
    owner: 'DEVELOPER',
    verdict: 'PASS',
    note: null,
    gainPoints: null,
    blockedByCap: false,
    outsideScore: false,
    codeExample: null,
    ...overrides,
  };
}

const RESULT: ScanResult = {
  kind: 'SEO',
  targetUrl: 'https://grand1.co.kr/',
  summary: '요약',
  scopeNotice: '이 결과는 입력한 1장 기준입니다.',
  score: {
    specId: 'veo.seo.readiness',
    specVersion: '1.8.0',
    specChecksum: 'abc',
    value: 31.5,
    bandLabel: '취약',
    coverage: 0.8,
    confidence: 0.9,
    meaning: '순위 예측이 아닙니다',
  },
  reach: 0.99,
  stages: [
    { categoryId: 's1', name: '색인 차단', score: 85, weight: 0, isGate: true },
    { categoryId: 's2', name: '대표 URL', score: 9, weight: 21.4, isGate: false },
  ],
  checks: [
    checkRow({
      checkId: 'seo.ux.mobile_viewport',
      title: '모바일 뷰포트 선언 없음',
      categoryId: 'tech',
      categoryName: '기술 SEO',
      verdict: 'FAIL',
      note: '모바일 우선 색인에서 축소 화면으로 보입니다.',
      gainPoints: 5.1,
      codeExample: '<meta name="viewport" content="width=device-width, initial-scale=1">',
    }),
    checkRow({
      checkId: 'seo.onpage.title_present',
      title: '제목 있음',
      categoryId: 'tech',
      categoryName: '기술 SEO',
      verdict: 'PASS',
    }),
    checkRow({
      checkId: 'seo.content.no_duplicate_bodies',
      title: '페이지 간 본문 중복',
      categoryId: 'tech',
      categoryName: '기술 SEO',
      verdict: 'UNKNOWN',
      note: '한 장 진단으로는 판정할 수 없습니다.',
    }),
    checkRow({
      checkId: 'seo.integration.gsc',
      title: '서치콘솔 연동',
      categoryId: 'integration',
      categoryName: '검색엔진 연동',
      verdict: 'UNKNOWN',
      note: '연동이 필요합니다.',
      outsideScore: true,
    }),
  ],
  counts: { failed: 1, warned: 0, passed: 1, unknown: 2, notApplicable: 0 },
  exposure: null,
  previews: {
    serpTitle: null,
    serpDescription: null,
    ogTitle: null,
    ogDescription: null,
    hasOgImage: false,
  },
  findings: [],
  findingCount: 1,
  unmeasuredCount: 2,
  resultToken: 't',
  resultExpiresAt: '2026-08-09T00:00:00Z',
};

function mockScan(result: ScanResult = RESULT) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ result }), { status: 200 })),
  );
}

async function runScanThroughForm() {
  const user = userEvent.setup();
  render(<PublicChecker kind="SEO" />);
  await user.type(screen.getByLabelText('진단할 주소'), 'https://grand1.co.kr/');
  await user.click(screen.getByRole('button', { name: '진단하기' }));
  await screen.findByText('취약');
  return user;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('점수 밴드', () => {
  it('점수·도달률·단계를 서버 값 그대로 그린다', async () => {
    mockScan();
    await runScanThroughForm();

    expect(screen.getAllByText('31.5').length).toBeGreaterThan(0);
    expect(screen.getByText('0.99')).toBeInTheDocument();
    expect(screen.getByText('색인 차단')).toBeInTheDocument();
    expect(screen.getByText('· 관문')).toBeInTheDocument();
  });

  it('GEO 는 숫자 대신 링크다 — 재지 않은 값을 그리지 않는다', async () => {
    mockScan();
    await runScanThroughForm();

    expect(
      screen.getByRole('link', { name: /같은 주소로 AI 답변 엔진 준비도 확인/ }),
    ).toBeInTheDocument();
  });
});

describe('필터 칩', () => {
  it('서버 카운트를 그대로 보여주고, 누르면 그 상태만 남는다', async () => {
    mockScan();
    const user = await runScanThroughForm();

    const failChip = screen.getByRole('button', { name: /실패 1/ });
    await user.click(failChip);

    expect(screen.getByText('모바일 뷰포트 선언 없음')).toBeInTheDocument();
    expect(screen.queryByText('제목 있음')).not.toBeInTheDocument();
  });
});

describe('더보기', () => {
  it('실패 항목을 열면 조치 코드가 나온다', async () => {
    mockScan();
    const user = await runScanThroughForm();

    await user.click(screen.getByText('모바일 뷰포트 선언 없음'));

    expect(screen.getByText(/width=device-width/)).toBeInTheDocument();
    expect(screen.getByText(/\+5\.1점/)).toBeInTheDocument();
  });

  it('측정 불가는 이유가 보이고 통과처럼 그려지지 않는다', async () => {
    mockScan();
    await runScanThroughForm();

    // 요약 줄과 더보기 안에 두 번 나올 수 있다 — 있는지가 중요하다.
    expect(
      screen.getAllByText('한 장 진단으로는 판정할 수 없습니다.').length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/측정 불가:/).length).toBeGreaterThan(0);
  });

  it('점수 밖 항목은 배지로 갈라 그린다', async () => {
    mockScan();
    await runScanThroughForm();

    expect(screen.getAllByText('점수 밖').length).toBeGreaterThan(0);
  });
});

describe('GEO', () => {
  it('노출 차단은 점수와 별개의 경고로 나온다 — 합치지 않는다', async () => {
    mockScan({
      ...RESULT,
      kind: 'GEO',
      previews: null,
      exposure: { isBlocked: true, labels: ['인증서 경고'] },
    });
    const user = userEvent.setup();
    render(<PublicChecker kind="GEO" />);
    await user.type(screen.getByLabelText('진단할 주소'), 'https://grand1.co.kr/');
    await user.click(screen.getByRole('button', { name: '진단하기' }));
    await screen.findByText('취약');

    expect(screen.getByRole('alert')).toHaveTextContent('노출 차단');
    expect(screen.getByRole('alert')).toHaveTextContent('인증서 경고');
    // 점수는 점수대로 그려진다 — 차단이 점수를 바꾸지 않는다.
    expect(screen.getAllByText('31.5').length).toBeGreaterThan(0);
    expect(screen.getAllByText('GEO 준비도').length).toBeGreaterThan(0);
  });
});

describe('미리보기', () => {
  it('없는 태그는 없는 채로 그린다 — 지어내지 않는다', async () => {
    mockScan();
    await runScanThroughForm();

    expect(screen.getByText('(제목 없음)')).toBeInTheDocument();
    expect(screen.getByText('og:image 없음')).toBeInTheDocument();
  });
});
