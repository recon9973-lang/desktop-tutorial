/**
 * 작업 큐 (재설계 ③) — 성질.
 *
 * 1. 순서를 다시 계산하지 않는다 — 엔진이 매긴 순서 그대로.
 * 2. 상한에 막힌 항목은 "+0점"이 아니라 "상한 해제 후"로.
 * 3. 담당 칩은 세고, 거른다 — 숨긴 건수가 칩에 보인다.
 * 4. 행을 열면 조치·코드가 나오고, 본문 **아래의** 접기 버튼으로 닫힌다.
 */

import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { WorkQueue } from './WorkQueue';
import type { ConsoleScanResult, Improvement, Issue, Outcome } from '@/lib/console-scan';

function improvement(overrides: Partial<Improvement>): Improvement {
  return {
    checkId: 'seo.x',
    categoryId: 'cat',
    title: '항목',
    gainPoints: 1,
    blockedByCap: false,
    severity: 'MAJOR',
    remediationOwner: 'DEVELOPER',
    ...overrides,
  };
}

function issue(overrides: Partial<Issue>): Issue {
  return {
    checkId: 'seo.x',
    title: '항목',
    summary: '진단 요약',
    affectedUrls: [],
    evidenceIds: [],
    remediation: '이렇게 고치세요',
    remediationOwner: 'DEVELOPER',
    businessImpact: '',
    fixExample: null,
    reverificationNote: '',
    ...overrides,
  };
}

function outcome(overrides: Partial<Outcome>): Outcome {
  return {
    checkId: 'seo.x',
    title: '항목',
    categoryId: 'cat',
    categoryName: '영역',
    severity: 'MAJOR',
    remediationOwner: 'DEVELOPER',
    availability: 'SELF_SERVICE',
    reference: null,
    status: 'FAIL',
    confidenceLevel: null,
    note: null,
    evidenceIds: [],
    observed: null,
    ...overrides,
  };
}

function result(overrides: Partial<ConsoleScanResult>): ConsoleScanResult {
  return {
    targetUrl: 'https://a.example.kr/',
    summary: '요약',
    specId: 'veo.seo.readiness',
    specVersion: '1.9.0',
    specChecksum: 'abc',
    status: 'SCORED',
    score: 70,
    scoreBeforeCaps: 70,
    bandId: 'at_risk',
    coverage: 0.9,
    confidence: 0.9,
    reach: 1,
    gateUnverified: [],
    categories: [],
    appliedCaps: [],
    outcomes: [],
    issues: [],
    improvements: [],
    evidence: [],
    unknownChecks: [],
    notes: [],
    generatedAt: '2026-08-03T09:00:00+09:00',
    geo: null,
    ...overrides,
  };
}

const FIXTURE = result({
  improvements: [
    improvement({ checkId: 'seo.a', title: '게시판 제목 중복', gainPoints: 5.9 }),
    improvement({
      checkId: 'seo.b',
      title: '메타 설명 짧음',
      gainPoints: 1.6,
      remediationOwner: 'MARKETER',
    }),
    improvement({
      checkId: 'seo.c',
      title: '상한에 걸린 항목',
      gainPoints: 0,
      blockedByCap: true,
    }),
  ],
  issues: [
    issue({
      checkId: 'seo.a',
      title: '게시판 제목 중복',
      summary: '103장이 같은 제목을 씁니다',
      remediation: '템플릿의 title 에 글 제목을 넣으십시오',
      fixExample: '<title>글 제목 — 병원명</title>',
      affectedUrls: ['https://a.example.kr/bbs/1', 'https://a.example.kr/bbs/2'],
    }),
  ],
  outcomes: [
    outcome({ checkId: 'seo.a', status: 'FAIL' }),
    outcome({ checkId: 'seo.b', status: 'WARNING' }),
  ],
});

describe('순서와 숫자는 엔진의 것', () => {
  it('엔진이 매긴 순서 그대로 그린다', () => {
    render(<WorkQueue result={FIXTURE} />);
    const titles = screen
      .getAllByRole('button', { expanded: undefined })
      .map((node) => node.textContent ?? '');
    const rows = screen.getAllByRole('article');
    expect(rows[0]!.textContent).toContain('게시판 제목 중복');
    expect(rows[1]!.textContent).toContain('메타 설명 짧음');
    expect(rows[2]!.textContent).toContain('상한에 걸린 항목');
    expect(titles.join(' ')).toContain('+5.9점');
  });

  it('상한에 막힌 항목은 +0점이 아니라 "상한 해제 후"', () => {
    render(<WorkQueue result={FIXTURE} />);
    const blocked = screen.getAllByRole('article')[2]!;
    expect(blocked.textContent).toContain('상한 해제 후');
    expect(blocked.textContent).not.toContain('+0.0점');
  });
});

describe('담당 칩', () => {
  it('세고, 거른다 — 숨긴 건수가 칩에 남는다', async () => {
    render(<WorkQueue result={FIXTURE} />);
    expect(screen.getByRole('button', { name: '전체 3' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '마케팅 1' }));

    expect(screen.getByText('메타 설명 짧음')).toBeInTheDocument();
    expect(screen.queryByText('게시판 제목 중복')).not.toBeInTheDocument();
    // 거른 뒤에도 다른 담당의 건수는 칩에 그대로 보인다.
    expect(screen.getByRole('button', { name: '개발 2' })).toBeInTheDocument();
  });
});

describe('행 확장', () => {
  it('열면 진단·조치·코드가 나오고, 본문 아래 접기로 닫힌다', async () => {
    render(<WorkQueue result={FIXTURE} />);

    await userEvent.click(screen.getByRole('button', { name: /게시판 제목 중복/ }));

    expect(screen.getByText('103장이 같은 제목을 씁니다')).toBeInTheDocument();
    expect(screen.getByText('템플릿의 title 에 글 제목을 넣으십시오')).toBeInTheDocument();
    expect(screen.getByText('<title>글 제목 — 병원명</title>')).toBeInTheDocument();

    const body = screen.getByText('103장이 같은 제목을 씁니다').closest('div')!;
    await userEvent.click(within(body).getByRole('button', { name: '접기 ▴' }));
    expect(screen.queryByText('103장이 같은 제목을 씁니다')).not.toBeInTheDocument();
  });
});
