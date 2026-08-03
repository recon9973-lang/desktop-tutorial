import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';

import type { GeoImprovement, GeoReadiness } from '@/lib/observations';

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
    lookup: null,
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
    // (표기는 게이지로 바뀌었다 — 숫자와 등급이 나뉘어 있다. 지키는 뜻은 그대로:
    //  차단이 점수를 건드리지 않는다.)
    expect(screen.getByText('95.2')).toBeInTheDocument();
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

describe('참고 조회 결과', () => {
  const lookup = {
    engine: 'NAVER',
    totals: { local: 5, blog: 346, news: 2, cafearticle: 20 },
    considered: 25,
    accepted: 7,
    rejected_as_another_business: 18,
    unavailable: {},
  };

  const withReference = () => {
    const base = report();
    return {
      ...base,
      lookup,
      readiness: {
        ...base.readiness,
        categories: [
          ...base.readiness.categories,
          {
            category_id: 'external_verifiability',
            name_ko: '외부 검증 가능성',
            weight: 10,
            contributes_to_score: false,
            outside_score_reason_ko: '참고 항목입니다.',
            status: 'NOT_APPLICABLE' as const,
            score: null,
            coverage: 0,
            confidence: 0,
            failing_check_ids: [],
            unknown_check_ids: [],
            not_applicable_check_ids: ['a'],
          },
        ],
      },
    };
  };

  it('무엇을 버렸는지 함께 보여준다', () => {
    render(<ReadinessReport report={withReference()} />);

    // 검색은 수백 건인데 보고서엔 7건뿐이다. 이유를 말하지 않으면 "못 찾았다" 로 읽힌다.
    expect(screen.getByText(/18건/)).toBeInTheDocument();
    expect(screen.getByText(/이름이 비슷한 다른 업체로 보여/)).toBeInTheDocument();
  });

  it('네이버만 봤다는 사실을 적는다', () => {
    render(<ReadinessReport report={withReference()} />);

    expect(screen.getByText(/네이버만 조회했습니다/)).toBeInTheDocument();
    expect(screen.getByText(/구글·다음은 보지 않았습니다/)).toBeInTheDocument();
  });

  it('눈으로 확인해 달라고 말한다', () => {
    render(<ReadinessReport report={withReference()} />);

    expect(screen.getByText(/눈으로 한 번 확인/)).toBeInTheDocument();
  });

  it('조회하지 않았으면 이 구역을 띄우지 않는다', () => {
    render(<ReadinessReport report={report()} />);

    expect(screen.queryByText(/네이버만 조회했습니다/)).toBeNull();
  });
});

/**
 * 항목별 판정 — GEO 도 SEO 처럼 "무엇을 보고 그렇게 판정했나" 와 "어떻게 고치나" 를 준다.
 *
 * 엔진은 처음부터 이 자료를 보내고 있었는데 화면이 읽지 않아, GEO 는 영역 점수만 보이고
 * 담당자가 그 화면을 보고 할 수 있는 일이 없었다. 여기서 지키는 것은 **판정과 근거와
 * 고침 방법이 한 화면에서 이어진다**는 것이다.
 */
describe('GEO 항목별 판정', () => {
  const check = {
    check_id: 'geo.sd.declared',
    title_ko: '구조화 데이터가 선언돼 있는가',
    category_id: 'geo.sd',
    category_name_ko: '구조화 데이터·메타',
    remediation_owner: 'DEVELOPER',
    status: 'FAIL',
    confidence_level: 'DIRECT_OBSERVATION',
    note_ko: 'JSON-LD 를 찾지 못했습니다.',
    evidence_ids: [],
    observed: { 'https://clinic.example/': '없음' },
  };

  it('판정과 실측값을 함께 보여준다 — 펼치지 않아도', () => {
    render(<ReadinessReport report={report({ checks: [check] })} />);

    const row = screen
      .getByText('구조화 데이터가 선언돼 있는가')
      .closest('summary') as HTMLElement;

    // 실측값이 **줄에** 함께 올라온다(확정 시안 v2.2 §11). 펼친 상세에도 같은 값이
    // 있으므로 화면 전체가 아니라 줄 안에서 찾는다.
    expect(within(row).getByText('없음')).toBeInTheDocument();
  });

  it('영역 머리줄이 볼지 말지를 먼저 말한다', () => {
    render(<ReadinessReport report={report({ checks: [check] })} />);

    const group = screen.getByRole('region', { name: '구조화 데이터·메타' });

    expect(screen.getByText('실패 1')).toBeInTheDocument();
    expect(group).toBeInTheDocument();
  });

  it('고침 방법과 붙여넣을 코드가 판정 옆에 있다', () => {
    render(
      <ReadinessReport
        report={report({
          checks: [check],
          issues: [
            {
              check_id: 'geo.sd.declared',
              title_ko: '구조화 데이터 없음',
              summary_ko: 'JSON-LD 가 없습니다.',
              remediation_ko: 'MedicalClinic 스키마를 head 에 넣으십시오.',
              remediation_owner: 'DEVELOPER',
              business_impact_ko: 'AI 가 병원 정보를 확인하지 못합니다.',
              affected_urls: ['https://clinic.example/'],
              evidence_ids: [],
              fix_example: '<script type="application/ld+json">…</script>',
              reverification_note_ko: '다시 진단해 확인합니다.',
            },
          ],
        })}
      />,
    );

    expect(screen.getByText('MedicalClinic 스키마를 head 에 넣으십시오.')).toBeInTheDocument();
    // 예시 코드가 실데이터로 읽히지 않게 라벨이 함께 있다(v0.3.2 에서 고친 오해).
    expect(
      screen.getByText('예시 코드 — 업체명·내용은 우리 것으로 바꿔 쓰세요'),
    ).toBeInTheDocument();
  });

  it('판정이 없던 예전 실행은 그 구역을 그리지 않는다', () => {
    /** 없는 것을 빈 목록으로 꾸미지 않는다 — 필드가 생기기 전에 저장된 실행이 있다. */
    render(<ReadinessReport report={report()} />);

    expect(screen.queryByText(/항목별 판정/)).not.toBeInTheDocument();
  });
});

/**
 * 심각도 배지 — **발행 명세에서 읽어 온 것만** 그린다.
 *
 * GEO 응답에는 심각도가 없다. 일부러 없다: GEO 엔진은 관측만 하고 점수를 정하지 않는다는
 * 경계가 있고(`tests/geo/test_engine_boundaries.py`), 심각도는 채점 어휘다. 그렇다고
 * 화면이 대신 지어내면 경계를 우회한 것이 된다 — 명세가 말하지 않은 검사는 배지가 없다.
 */
describe('GEO 심각도 배지', () => {
  const check = {
    check_id: 'geo.sd.declared',
    title_ko: '구조화 데이터가 선언돼 있는가',
    category_id: 'geo.sd',
    category_name_ko: '구조화 데이터·메타',
    remediation_owner: 'DEVELOPER',
    status: 'FAIL',
    confidence_level: 'DIRECT_OBSERVATION',
    note_ko: null,
    evidence_ids: [],
    observed: null,
  };

  it('명세가 정한 심각도를 한국어로 단다', () => {
    render(
      <ReadinessReport
        report={report({ checks: [check] })}
        severities={new Map([['geo.sd.declared', 'BLOCKER']])}
      />,
    );

    expect(screen.getByText('치명')).toBeInTheDocument();
  });

  it('명세에 없는 검사는 배지를 그리지 않는다 — 지어내지 않는다', () => {
    render(<ReadinessReport report={report({ checks: [check] })} severities={new Map()} />);

    for (const label of ['치명', '심각', '중요', '경미', '참고']) {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    }
  });

  it('심각도를 아예 넘기지 않아도 화면은 그려진다', () => {
    /** 예전 화면·시험이 이 값을 모른다. 없다고 판정 목록이 사라지면 안 된다. */
    render(<ReadinessReport report={report({ checks: [check] })} />);

    expect(screen.getByText('구조화 데이터가 선언돼 있는가')).toBeInTheDocument();
  });
});

/**
 * 오늘 고칠 것 — 확정 시안 v2.2 §1.
 *
 * 이 목록의 약속은 하나다: **위에서부터 하면 점수가 가장 빨리 오른다.** 그 약속이
 * 깨지는 순간 목록은 쓸모가 없어지고, 담당자는 다시 전체를 훑게 된다.
 */
describe('GEO 작업 큐', () => {
  function gain(over: Partial<GeoImprovement> = {}): GeoImprovement {
    return {
      check_id: 'geo.sd.declared',
      category_id: 'geo.sd',
      title_ko: '구조화 데이터를 선언하세요',
      gain_points: 5.9,
      blocked_by_cap: false,
      ...over,
    };
  }

  it('고치면 오르는 점수를 함께 보여준다', () => {
    render(<ReadinessReport report={report({ improvements: [gain()] })} />);

    expect(screen.getByText('구조화 데이터를 선언하세요')).toBeInTheDocument();
    expect(screen.getByText('+5.9점')).toBeInTheDocument();
  });

  it('상한에 걸려 지금은 오르지 않는 항목은 이 목록에 넣지 않는다', () => {
    /** 0점짜리를 섞으면 "이걸 하면 오른다" 는 약속이 깨진다. */
    render(
      <ReadinessReport
        report={{
          ...report(),
          improvements: [gain({ gain_points: 0, blocked_by_cap: true })],
        }}
      />,
    );

    expect(screen.queryByText(/오늘 고칠 것/)).not.toBeInTheDocument();
  });

  it('이득이 0인 항목도 넣지 않는다', () => {
    render(<ReadinessReport report={report({ improvements: [gain({ gain_points: 0 })] })} />);

    expect(screen.queryByText(/오늘 고칠 것/)).not.toBeInTheDocument();
  });

  it('줄을 누르면 그 영역 카드로 간다', () => {
    const { container } = render(
      <ReadinessReport report={report({ improvements: [gain()] })} />,
    );

    const link = container.querySelector('a[href="#check-geo.sd"]');
    expect(link).not.toBeNull();
  });

  it('개선 목록이 없던 예전 실행은 이 구역을 그리지 않는다', () => {
    render(<ReadinessReport report={report()} />);

    expect(screen.queryByText(/오늘 고칠 것/)).not.toBeInTheDocument();
  });
});

/**
 * 점수를 게이지로 — SEO 화면과 같은 문법.
 *
 * 두 화면이 다른 방식으로 점수를 그리면 같은 사람이 두 번 배워야 한다. 값도 방법도
 * SEO 쪽과 같은 것을 쓴다(conic-gradient, 이미지·라이브러리 없음).
 */
describe('GEO 점수 게이지', () => {
  it('점수와 등급을 한국어 라벨로 보여준다', () => {
    render(<ReadinessReport report={report()} />);

    expect(screen.getByText('95.2')).toBeInTheDocument();
    expect(screen.getByText('우수')).toBeInTheDocument();
  });

  it('점수를 낼 수 없으면 게이지를 그리지 않는다', () => {
    /** 잴 수 없었던 것을 0점짜리 게이지로 그리면 "0점" 으로 읽힌다. 그것은 거짓이다. */
    render(
      <ReadinessReport
        report={{
          ...report(),
          readiness: { ...report().readiness, status: 'UNKNOWN', score: null },
        }}
      />,
    );

    expect(screen.getByText('점수를 낼 수 없습니다')).toBeInTheDocument();
  });
});
