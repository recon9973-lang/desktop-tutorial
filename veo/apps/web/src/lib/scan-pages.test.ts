import { describe, expect, it } from 'vitest';

import { toPageDetail, toScanPages } from './scan-pages';

/**
 * 페이지별 보기의 데이터층 — 서버가 준 것만 나르고, 없는 것은 없다고 말한다.
 *
 * 여기서 지키는 것: 점수를 계산하거나 보정하지 않는다(숫자는 발행 명세의 것),
 * 표본 밖 문구는 서버 것을 그대로, 모르는 필드 형태는 조용히 기본값으로 접되
 * 목록을 지어내지 않는다.
 */
describe('toScanPages', () => {
  it('페이지 행과 점수를 그대로 나른다', () => {
    const data = toScanPages({
      measured_at: '2026-08-02T12:00:00Z',
      pages: [
        {
          url: 'https://clinic.example/sub/',
          failed: ['seo.a'],
          warned: [],
          passed_count: 20,
          problem_count: 1,
          score: 91.3,
          score_status: 'SCORED',
        },
      ],
      site_checks: [{ check_id: 'seo.site', status: 'UNKNOWN', reason_ko: '잘림' }],
      recorded_before_page_lists: false,
      notes_ko: [],
    });

    expect(data.pages[0]?.score).toBe(91.3);
    expect(data.pages[0]?.failed).toEqual(['seo.a']);
    expect(data.siteChecks[0]?.reasonKo).toBe('잘림');
    expect(data.measuredAt).toBe('2026-08-02T12:00:00Z');
  });

  it('점수 없는 실행(1.9.0 이전)은 null 로 남는다 — 지어내지 않는다', () => {
    const data = toScanPages({
      pages: [{ url: 'https://a/', failed: [], warned: [], passed_count: 3, problem_count: 0 }],
      notes_ko: ['이 실행은 채점 명세 1.9.0 이전 판으로 저장되어 페이지 점수가 없습니다.'],
    });

    expect(data.pages[0]?.score).toBeNull();
    expect(data.notesKo).toHaveLength(1);
  });
});

describe('toPageDetail', () => {
  it('점수 블록 전체 — 단계·손실·표본 밖 문구까지 그대로', () => {
    const detail = toPageDetail({
      url: 'https://clinic.example/',
      failed: ['seo.a'],
      warned: [],
      passed: ['seo.b'],
      score: {
        spec_id: 'veo.seo.readiness',
        spec_version: '1.9.0',
        status: 'SCORED',
        score: 94.6,
        reach: 1.0,
        quality: 94.6,
        stages: [
          { category_id: 's1', name_ko: '색인 차단', weight: 30, is_gate: true, score: 100 },
        ],
        losses: [{ check_id: 'seo.a', category_id: 's3', status: 'FAIL', lost: 5.4 }],
        gate_unverified: [],
        unmeasured: [],
        not_sampled: ['seo.perf.lcp_lab'],
        not_applicable: [],
        not_sampled_note_ko: '표본 밖 — 요청 시 측정',
      },
    });

    expect(detail.score?.score).toBe(94.6);
    expect(detail.score?.stages[0]?.isGate).toBe(true);
    expect(detail.score?.losses[0]?.lost).toBe(5.4);
    expect(detail.score?.notSampled).toEqual(['seo.perf.lcp_lab']);
    expect(detail.score?.notSampledNoteKo).toBe('표본 밖 — 요청 시 측정');
  });

  it('score 가 null 이면 null — 옛 실행에 숫자를 만들어 붙이지 않는다', () => {
    const detail = toPageDetail({ url: 'https://a/', failed: [], warned: [], passed: [], score: null });
    expect(detail.score).toBeNull();
  });
});
