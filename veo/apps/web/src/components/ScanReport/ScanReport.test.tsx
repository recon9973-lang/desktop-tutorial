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
import userEvent from '@testing-library/user-event';

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
    reach: 1,
    gateUnverified: [],
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
    geo: null,
    ...overrides,
  };
}

function detailed(overrides: Partial<ConsoleScanResult> = {}) {
  return render(<ScanReport result={result(overrides)} bands={BANDS} view="detailed" />);
}

function simple(overrides: Partial<ConsoleScanResult> = {}) {
  return render(<ScanReport result={result(overrides)} bands={BANDS} view="simple" />);
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

    // 접힌 줄에도 같은 값이 요약으로 올라간다(확정 시안 v2.2 §11). 그래서 근거 구역
    // 안에서 찾는다 — 화면 어딘가에 있다가 아니라 **근거로서** 있어야 한다.
    const reason = screen.getByRole('heading', { name: '이렇게 판정한 근거' })
      .parentElement as HTMLElement;

    expect(within(reason).getByText(/H2 다음에 H5가 옵니다/)).toBeInTheDocument();
  });

  it('펼치지 않아도 실측값이 줄에 함께 보인다', () => {
    /**
     * 확정 시안 v2.2 §11 — "통과" 라는 판정보다 "200 · 리다이렉트 1회" 라는 사실이
     * 신뢰를 만든다. 펼쳐야만 근거가 보이면, 펼치지 않은 40여 줄은 근거 없는 단정이다.
     */
    detailed();

    const row = screen.getByText('제목 단계가 순서대로인가').closest('summary') as HTMLElement;

    expect(within(row).getByText(/H2 다음에 H5가 옵니다/)).toBeInTheDocument();
  });

  it('값이 여럿이면 줄에는 개수로 말한다', () => {
    /** 스무 곳의 URL 을 한 줄에 이어 붙이면 읽히지 않는다 — 자세한 것은 펼치면 있다. */
    detailed({
      outcomes: [
        outcome({
          observed: { 'https://a.example.kr/': '건너뜀', 'https://b.example.kr/': '건너뜀' },
        }),
      ],
    });

    const row = screen.getByText('제목 단계가 순서대로인가').closest('summary') as HTMLElement;

    expect(within(row).getByText('2건')).toBeInTheDocument();
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

describe('관측값을 읽을 수 있게 편다', () => {
  it('빈 목록은 이름만 남기지 않고 없다고 말한다', () => {
    detailed({
      outcomes: [outcome({ observed: { robots_declared: [], fetched: [] } })],
    });

    const panel = screen.getByText('제목 단계가 순서대로인가').closest('details');
    expect(within(panel!).getAllByText('없음')).toHaveLength(2);
  });

  it('참·거짓을 그대로 내보내지 않는다', () => {
    detailed({ outcomes: [outcome({ observed: { 'https://a.example.kr/': false } })] });

    // 값이 하나뿐이면 접힌 줄에도 같은 글자가 올라간다 — 둘 다 사람 말이어야 한다.
    for (const shown of screen.getAllByText('아니오')) {
      expect(shown).toBeInTheDocument();
    }
    expect(screen.queryByText('false')).not.toBeInTheDocument();
  });
});

describe('영역별 점수', () => {
  it('배점 밖 영역을 측정 불가로 끼워 넣지 않는다', () => {
    /**
     * 나란히 서면 우리가 재려다 실패한 것처럼 읽힌다. 실제로는 애초에 이 점수의
     * 일부가 아니다 — 그 사실은 아래 전용 구역에서 말한다.
     */
    detailed({
      outcomes: [
        outcome(),
        outcome({
          checkId: 'seo.integration.gsc_verified',
          categoryId: 'search_engine_integration',
          categoryName: '검색엔진 연동',
          availability: 'CUSTOMER_GRANTED',
          status: 'NOT_APPLICABLE',
        }),
      ],
      categories: [
        {
          categoryId: 'onpage_semantics',
          name: '온페이지 시맨틱',
          weight: 18.75,
          status: 'SCORED',
          score: 80,
          coverage: 1,
          confidence: 1,
          failingCheckIds: [],
          unknownCheckIds: [],
          notApplicableCheckIds: [],
        },
        {
          categoryId: 'search_engine_integration',
          name: '검색엔진 연동',
          weight: 10,
          status: 'NOT_APPLICABLE',
          score: null,
          coverage: 0,
          confidence: 0,
          failingCheckIds: [],
          unknownCheckIds: [],
          notApplicableCheckIds: ['seo.integration.gsc_verified'],
        },
      ],
    });

    const section = screen.getByLabelText('영역별 점수');
    expect(within(section).queryByText('측정 불가')).not.toBeInTheDocument();
    expect(within(section).queryByText('검색엔진 연동')).not.toBeInTheDocument();
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

describe('좁히기', () => {
  /**
   * 실제로 렌더해 재 봤을 때 상세 보기가 화면 7.2개 높이였고 항목이 44개인데 좁힐
   * 수단이 하나도 없었다. 그중 실패는 5개인데 그 5개를 찾으려면 눈으로 훑어야 했다.
   */
  const failing = outcome({ checkId: 'a.b.c', title: '실패한 항목', status: 'FAIL' });
  const passing = outcome({ checkId: 'd.e.f', title: '통과한 항목', status: 'PASS' });

  it('상태별 칩에 건수가 붙어 있다', () => {
    detailed({ outcomes: [failing, passing] });

    expect(screen.getByRole('button', { name: /전체/ })).toHaveTextContent('2');
    expect(screen.getByRole('button', { name: /실패/ })).toHaveTextContent('1');
  });

  it('칩을 누르면 그 상태만 남는다', async () => {
    const user = userEvent.setup();
    detailed({ outcomes: [failing, passing] });

    expect(screen.getByText('통과한 항목')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /실패/ }));

    expect(screen.getByText('실패한 항목')).toBeInTheDocument();
    expect(screen.queryByText('통과한 항목')).not.toBeInTheDocument();
  });

  it('0건인 기준은 누를 수 없다', () => {
    /** 눌러도 빈 화면이 된다. 막아 두고 이유는 숫자가 말한다. */
    detailed({ outcomes: [passing] });

    expect(screen.getByRole('button', { name: /실패/ })).toBeDisabled();
  });

  it('선택 상태를 색이 아니라 aria-pressed 로도 알린다', async () => {
    const user = userEvent.setup();
    detailed({ outcomes: [failing, passing] });

    const chip = screen.getByRole('button', { name: /실패/ });
    expect(chip).toHaveAttribute('aria-pressed', 'false');
    await user.click(chip);
    expect(chip).toHaveAttribute('aria-pressed', 'true');
  });
});

describe('할 일 우선순위', () => {
  const many = Array.from({ length: 6 }, (_, i) => ({
    checkId: `c${i}`,
    categoryId: 'onpage_semantics',
    title: `할 일 ${i + 1}`,
    gainPoints: 6 - i,
    blockedByCap: false,
    severity: 'MAJOR',
    remediationOwner: 'DEVELOPER',
  }));

  // 상세(직원용)의 조치 목록은 재설계 ③ 부터 작업 큐가 정본이다 — 그 성질은
  // WorkQueue.test.tsx 가 지킨다. 아래 접기 규칙은 간소화(업체 전달용)의 것.
  it('간소화 보기는 상위 셋만 펼쳐 두고 나머지는 접는다', () => {
    /** 열몇 줄을 같은 무게로 늘어놓으면 우선순위가 사라진다. */
    const { container } = simple({ improvements: many });

    expect(screen.getByText('할 일 1')).toBeInTheDocument();
    expect(screen.getByText('나머지 3건 더 보기')).toBeInTheDocument();
    const rest = container.querySelector('details:has(> summary)');
    expect(rest).not.toBeNull();
  });

  it('셋 이하면 더 보기를 만들지 않는다', () => {
    simple({ improvements: many.slice(0, 2) });

    expect(screen.queryByText(/나머지 .*더 보기/)).not.toBeInTheDocument();
  });

  it('상세 보기의 조치 목록은 작업 큐다', () => {
    detailed({ improvements: many });

    expect(screen.getByText('작업 큐')).toBeInTheDocument();
    expect(screen.queryByText('나머지 3건 더 보기')).not.toBeInTheDocument();
  });
});

// --------------------------------------------------------------------------- //
// 색인 차단 — 0점의 이유가 화면에 있는가
// --------------------------------------------------------------------------- //

describe('색인 차단 안내', () => {
  it('색인이 막히지 않았으면 아무것도 그리지 않는다', () => {
    render(<ScanReport result={result()} bands={[]} view="detailed" />);
    expect(screen.queryByText(/색인에서 빠져/)).not.toBeInTheDocument();
  });

  it('막힌 비율을 적는다', () => {
    render(<ScanReport result={result({ reach: 0.4, score: 34 })} bands={[]} view="detailed" />);
    expect(screen.getByText(/60\.0%/)).toBeInTheDocument();
  });

  it('차단을 먼저 풀라고 말한다', () => {
    // 점수만 보여주면 고객은 눈에 띄는 항목부터 고친다. 색인이 막힌 동안은 그
    // 무엇을 고쳐도 점수가 거의 오르지 않으므로, 순서를 말해 주지 않으면
    // 헛수고를 시키는 셈이 된다.
    render(<ScanReport result={result({ reach: 0.4, score: 34 })} bands={[]} view="detailed" />);
    expect(screen.getByText(/색인 차단을 먼저 풀지 않으면/)).toBeInTheDocument();
  });

  it('확인하지 못한 관문을 차단과 다르게 적는다', () => {
    // 못 잰 것을 차단으로 세지 않는다. 그러나 조용히 넘어가면 "확인했고 문제없음"
    // 과 구분되지 않는다.
    render(
      <ScanReport
        result={result({ gateUnverified: ['seo.robots.txt_allows_url'] })}
        bands={[]}
        view="detailed"
      />,
    );
    expect(screen.getByText(/확인하지 못한 항목이 1건/)).toBeInTheDocument();
    expect(screen.getByText(/차단됐다는 뜻이 아니라/)).toBeInTheDocument();
  });

  it('점수에서 차감하지 않았다고 밝힌다', () => {
    render(
      <ScanReport
        result={result({ gateUnverified: ['seo.robots.txt_allows_url'] })}
        bands={[]}
        view="detailed"
      />,
    );
    expect(screen.getByText(/점수에서 차감하지\s*않았습니다/)).toBeInTheDocument();
  });
});

/**
 * 영역(카테고리)이 눈으로 잡히는가.
 *
 * 44개 항목이 같은 무게로 늘어서면 어디까지가 한 영역인지 보이지 않고, 멀쩡한 영역을
 * 건너뛸 방법이 없어 전부 훑게 된다. 그래서 영역을 카드로 묶고 **머리줄에 이 영역의
 * 상태를 요약**한다 — 볼지 말지를 그 자리에서 정할 수 있어야 한다.
 *
 * 여기서 지키는 것은 모양이 아니라 **판단에 필요한 정보가 머리줄에 있다**는 것이다.
 */
describe('영역 머리줄이 볼지 말지를 먼저 말한다', () => {
  it('고칠 것이 있으면 실패·주의 건수를 머리줄에 세운다', () => {
    detailed({
      outcomes: [
        outcome({ checkId: 'a', status: 'FAIL' }),
        outcome({ checkId: 'b', status: 'FAIL' }),
        outcome({ checkId: 'c', status: 'WARNING' }),
        outcome({ checkId: 'd', status: 'PASS' }),
      ],
    });

    const group = screen.getByRole('region', { name: '온페이지 시맨틱' });

    expect(within(group).getByText('실패 2')).toBeInTheDocument();
    expect(within(group).getByText('주의 1')).toBeInTheDocument();
  });

  it('전부 통과한 영역은 그렇다고 말한다 — 열어 보지 않아도 된다', () => {
    detailed({
      outcomes: [
        outcome({ checkId: 'a', status: 'PASS' }),
        outcome({ checkId: 'b', status: 'PASS' }),
      ],
    });

    const group = screen.getByRole('region', { name: '온페이지 시맨틱' });

    expect(within(group).getByText('모두 통과 2')).toBeInTheDocument();
    expect(within(group).queryByText(/실패/)).not.toBeInTheDocument();
  });

  it('색만으로 알리지 않는다 — 배지마다 글자가 함께 있다', () => {
    detailed({ outcomes: [outcome({ status: 'FAIL', severity: 'BLOCKER' })] });

    const group = screen.getByRole('region', { name: '온페이지 시맨틱' });

    // 심각도도 글자로 읽힌다(색 배지로만 바뀌지 않았다).
    expect(within(group).getByText('치명')).toBeInTheDocument();
    expect(within(group).getByText('실패 1')).toBeInTheDocument();
  });

  it('영역이 여럿이면 각각 자기 요약을 가진다', () => {
    detailed({
      outcomes: [
        outcome({ checkId: 'a', status: 'FAIL' }),
        outcome({
          checkId: 'b',
          status: 'PASS',
          categoryId: 'crawl',
          categoryName: '크롤 접근',
        }),
      ],
    });

    expect(
      within(screen.getByRole('region', { name: '온페이지 시맨틱' })).getByText('실패 1'),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: '크롤 접근' })).getByText('모두 통과 1'),
    ).toBeInTheDocument();
  });
});
