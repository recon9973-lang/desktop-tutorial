/**
 * 항목별 판정 — 접혀 있다가, 열면 원인과 수정 방향이 나온다.
 *
 * 경쟁 도구는 판정 옆에 **무엇을 보고 그렇게 판정했는지** 를 함께 보여준다. 제목 구조
 * 검사라면 실제 H2·H5 목록을 그대로 펼쳐 놓는 식이다. 우리 화면은 지금까지 상태와
 * `seo.onpage.heading_hierarchy` 같은 식별자만 찍었고, 그 줄을 본 직원이 할 수 있는
 * 일이 없었다.
 *
 * 그렇다고 54개 항목의 근거를 전부 펼쳐 두면 화면이 읽히지 않는다. 그래서 각 항목은
 * 접힌 채로 한 줄만 보이고, 열었을 때 두 가지가 나온다 — **원인 상세**(수집기가 실제로
 * 본 값)와 **수정 방향**(무엇을 어떻게 바꾸는가).
 *
 * `details`/`summary` 를 쓰는 이유: 자바스크립트 없이 열리고, 키보드로 다룰 수 있으며,
 * 브라우저의 페이지 내 검색이 닫힌 내용까지 찾아 준다. 직접 만든 토글은 셋 다 잃는다.
 */

import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';

import { ScanReport } from './ScanReport';
import type { ConsoleScanResult, Outcome } from '@/lib/console-scan';

const BANDS = [
  { id: 'ready', label: '준비됨', min: 90, max: 100, description: null },
  { id: 'at_risk', label: '위험', min: 50, max: 70, description: null },
];

function outcome(overrides: Partial<Outcome> = {}): Outcome {
  return {
    checkId: 'seo.onpage.heading_hierarchy',
    title: '제목 단계가 순서대로인가',
    categoryId: 'onpage_semantics',
    categoryName: '온페이지 시맨틱',
    severity: 'MINOR',
    remediationOwner: 'DEVELOPER',
    availability: 'SELF_SERVICE',
    reference: null,
    status: 'FAIL',
    confidenceLevel: 'DIRECT_OBSERVATION',
    note: '2개 페이지의 제목 단계가 건너뜁니다.',
    evidenceIds: [],
    observed: { 'https://a.example.kr/': 'H2 다음에 H5가 옵니다 (H3, H4 건너뜀)' },
    ...overrides,
  };
}

function result(overrides: Partial<ConsoleScanResult> = {}): ConsoleScanResult {
  return {
    targetUrl: 'https://a.example.kr/',
    summary: '요약',
    specId: 'veo.seo.readiness',
    specVersion: '1.3.0',
    specChecksum: 'abc123def456789',
    status: 'SCORED',
    score: 72.5,
    scoreBeforeCaps: 72.5,
    bandId: 'at_risk',
    coverage: 0.8,
    confidence: 0.9,
    categories: [
      {
        categoryId: 'onpage_semantics',
        name: '온페이지 시맨틱',
        weight: 18.75,
        status: 'SCORED',
        score: 80,
        coverage: 1,
        confidence: 1,
        failingCheckIds: ['seo.onpage.heading_hierarchy'],
        unknownCheckIds: [],
        notApplicableCheckIds: [],
      },
    ],
    appliedCaps: [],
    outcomes: [outcome()],
    issues: [],
    improvements: [],
    evidence: [],
    unknownChecks: [],
    notes: [],
    generatedAt: '2026-07-30T09:00:00+09:00',
    ...overrides,
  };
}

function detailed(overrides: Partial<ConsoleScanResult> = {}) {
  return render(<ScanReport result={result(overrides)} bands={BANDS} view="detailed" />);
}

describe('항목별 판정', () => {
  it('식별자가 아니라 사람이 읽는 이름을 보여준다', () => {
    detailed();

    expect(screen.getByText('제목 단계가 순서대로인가')).toBeInTheDocument();
  });

  it('기본으로 접혀 있다', () => {
    const { container } = detailed();

    const panels = container.querySelectorAll('details');
    expect(panels.length).toBeGreaterThan(0);
    for (const panel of panels) {
      expect(panel.open).toBe(false);
    }
  });

  it('열면 수집기가 실제로 본 값을 보여준다', () => {
    detailed();

    expect(screen.getByText(/H2 다음에 H5가 옵니다/)).toBeInTheDocument();
  });

  it('원인과 수정 방향을 각각 이름 붙여 나눈다', () => {
    detailed({
      issues: [
        {
          checkId: 'seo.onpage.heading_hierarchy',
          title: '제목 단계가 건너뜁니다',
          summary: 'H2 다음에 H5가 옵니다',
          affectedUrls: ['https://a.example.kr/'],
          evidenceIds: [],
          remediation: 'H3, H4를 채우거나 H5를 H3으로 올리십시오.',
          remediationOwner: 'DEVELOPER',
          businessImpact: '본문 구조를 읽기 어려워집니다.',
          fixExample: '<h3>소제목</h3>',
          reverificationNote: '수정 후 재수집합니다.',
        },
      ],
    });

    const panel = screen.getByText('제목 단계가 순서대로인가').closest('details');
    expect(panel).not.toBeNull();
    expect(within(panel!).getByText('이렇게 판정한 근거')).toBeInTheDocument();
    expect(within(panel!).getByText('어떻게 고치나')).toBeInTheDocument();
    expect(
      within(panel!).getByText(/H3, H4를 채우거나 H5를 H3으로 올리십시오/),
    ).toBeInTheDocument();
  });

  it('통과한 항목에는 고치라고 하지 않는다', () => {
    detailed({
      outcomes: [outcome({ status: 'PASS', note: '모든 페이지의 제목 단계가 순서대로입니다.' })],
    });

    const panel = screen.getByText('제목 단계가 순서대로인가').closest('details');
    expect(within(panel!).queryByText('어떻게 고치나')).not.toBeInTheDocument();
  });

  it('영역별로 묶어 보여준다', () => {
    detailed();

    expect(screen.getAllByText('온페이지 시맨틱').length).toBeGreaterThan(0);
  });
});

describe('진단 범위 밖', () => {
  const gated = outcome({
    checkId: 'seo.integration.gsc_verified',
    title: 'Google Search Console 소유권이 확인됐는가',
    categoryId: 'search_engine_integration',
    categoryName: '검색엔진 연동',
    availability: 'CUSTOMER_GRANTED',
    status: 'NOT_APPLICABLE',
    note: '사이트 소유자가 권한을 연결해야 측정됩니다. 연결 전까지는 배점에서 제외하며, 점수를 깎지 않습니다.',
    observed: null,
  });

  it('연동이 필요한 항목을 배점 항목과 섞지 않는다', () => {
    detailed({ outcomes: [outcome(), gated] });

    expect(screen.getByText(/이 진단의 배점 밖/)).toBeInTheDocument();
  });

  it('무엇을 연결하면 측정되는지 말해 준다', () => {
    detailed({ outcomes: [outcome(), gated] });

    expect(screen.getByText(/권한을 연결해야 측정됩니다/)).toBeInTheDocument();
  });

  it('연동 항목이 없으면 그 구역을 만들지 않는다', () => {
    detailed({ outcomes: [outcome()] });

    expect(screen.queryByText(/이 진단의 배점 밖/)).not.toBeInTheDocument();
  });
});
