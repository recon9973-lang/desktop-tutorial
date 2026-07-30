import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { GeoReadiness } from '@/lib/observations';

import { ReadinessReport } from './ReadinessReport';

/**
 * 준비도 화면이 지켜야 하는 것.
 *
 * 가장 중요한 하나: **점수와 노출 차단을 섞지 않는다.** 95점이면서 동시에 차단일 수
 * 있다 — 구조는 훌륭한데 robots 로 막아 둔 사이트가 그 모습이다. 차단을 점수에 반영해
 * 깎아 버리면 "무엇을 고쳐야 하는가" 가 사라진다. 하나는 설정 한 줄이고 다른 하나는
 * 몇 주짜리 작업이다.
 */

function report(over: Partial<GeoReadiness> = {}): GeoReadiness {
  return {
    target_url: 'https://clinic.example/',
    readiness: {
      spec_id: 'veo.geo.readiness',
      spec_version: '1.0.0',
      status: 'SCORED',
      score: 95.2,
      band_label_ko: '우수',
      coverage: 0.9,
      confidence: 0.95,
      categories: [
        {
          category_id: 'geo.access',
          name_ko: '접근·검색 적격성',
          weight: 20,
          status: 'SCORED',
          contributes_to_score: true,
          outside_score_reason_ko: null,
          score: 88,
          coverage: 1,
          confidence: 1,
          failing_check_ids: ['geo.access.a'],
          unknown_check_ids: [],
          not_applicable_check_ids: [],
        },
      ],
    },
    exposure: { blocked: false, status_codes: [], gates: [] },
    summary_ko: '구조적으로 준비돼 있습니다.',
    scope_notice_ko: '이 점수는 구조적 준비도입니다.',
    notes_ko: [],
    ...over,
  };
}

describe('점수와 노출 차단', () => {
  it('높은 점수와 차단이 동시에 표시된다', () => {
    render(
      <ReadinessReport
        report={report({
          exposure: {
            blocked: true,
            status_codes: ['ROBOTS_BLOCKED'],
            gates: [
              {
                gate_id: 'g1',
                status_code: 'ROBOTS_BLOCKED',
                label_ko: 'robots.txt 가 검색봇을 막고 있습니다',
                description_ko: '색인될 수 없습니다.',
                triggered_by: [],
              },
            ],
          },
        })}
      />,
    );

    // 점수는 그대로 95.2 다. 차단 때문에 깎지 않는다.
    expect(screen.getByText('95.2점')).toBeInTheDocument();
    expect(screen.getByText(/robots.txt 가 검색봇을 막고 있습니다/)).toBeInTheDocument();
    expect(screen.getByText(/별개의 사실/)).toBeInTheDocument();
  });

  it('차단이 없으면 차단 블록을 띄우지 않는다', () => {
    render(<ReadinessReport report={report()} />);

    expect(screen.queryByLabelText('노출 차단')).toBeNull();
  });
});

describe('점수를 낼 수 없을 때', () => {
  it('0점이라고 적지 않는다', () => {
    render(
      <ReadinessReport
        report={report({
          readiness: { ...report().readiness, status: 'UNKNOWN', score: null, band_label_ko: null },
        })}
      />,
    );

    expect(screen.getByText('점수를 낼 수 없습니다')).toBeInTheDocument();
    expect(screen.queryByText('0.0점')).toBeNull();
  });
});

describe('영역별', () => {
  it('측정 불가 항목 수를 실패 항목 수와 같은 자리에 둔다', () => {
    render(
      <ReadinessReport
        report={report({
          readiness: {
            ...report().readiness,
            categories: [
              {
                ...report().readiness.categories[0]!,
                failing_check_ids: ['a'],
                unknown_check_ids: ['b', 'c'],
                not_applicable_check_ids: ['d'],
              },
            ],
          },
        })}
      />,
    );

    // 측정 불가를 빼고 보여주면 그 영역이 실제보다 잘 나온 것처럼 읽힌다.
    expect(screen.getByText(/실패 1개/)).toBeInTheDocument();
    expect(screen.getByText(/측정 불가 2개/)).toBeInTheDocument();
    expect(screen.getByText(/해당 없음 1개/)).toBeInTheDocument();
  });
});

describe('저장되지 않는다는 사실', () => {
  it('결과가 사라진다는 것을 알린다', () => {
    render(<ReadinessReport report={report()} />);

    expect(screen.getByText(/저장되지 않습니다/)).toBeInTheDocument();
  });
});

describe('참고 · 별도 확인 필요', () => {
  const reference = {
    category_id: 'external_verifiability',
    name_ko: '외부 검증 가능성',
    weight: 10,
    contributes_to_score: false,
    outside_score_reason_ko:
      '참고 항목입니다. 네이버 한 곳만 조회하고 이름이 비슷한 업체가 섞일 수 있습니다.',
    status: 'NOT_APPLICABLE' as const,
    score: null,
    coverage: 0,
    confidence: 0,
    failing_check_ids: [],
    unknown_check_ids: [],
    not_applicable_check_ids: ['a', 'b', 'c', 'd'],
  };

  function withReference() {
    const base = report();
    return {
      ...base,
      readiness: {
        ...base.readiness,
        categories: [...base.readiness.categories, reference],
      },
    };
  }

  it('점수 영역과 섞지 않는다', () => {
    render(<ReadinessReport report={withReference()} />);

    // 참고 항목이 "영역별" 목록에 끼면 감점처럼 읽힌다.
    const scoredList = screen.getByText('영역별').closest('section, div');
    expect(scoredList?.textContent).not.toContain('외부 검증 가능성');
  });

  it('점수에 반영되지 않는다고 분명히 말한다', () => {
    render(<ReadinessReport report={withReference()} />);

    expect(screen.getByText('참고 · 별도 확인 필요')).toBeInTheDocument();
    expect(screen.getByText(/점수에 반영되지 않습니다/)).toBeInTheDocument();
  });

  it('왜 점수 밖인지 이유를 그대로 보여준다', () => {
    render(<ReadinessReport report={withReference()} />);

    expect(screen.getByText(/이름이 비슷한 업체가 섞일 수 있습니다/)).toBeInTheDocument();
  });

  it('참고 항목이 없으면 구역 자체를 띄우지 않는다', () => {
    render(<ReadinessReport report={report()} />);

    expect(screen.queryByText('참고 · 별도 확인 필요')).toBeNull();
  });
});
