/**
 * 공유 결과 읽기(readSharedResult)의 성질.
 *
 * 1. 종류를 지어내지 않는다 — SEO/GEO 는 저장된 응답의 키(`score`/`readiness`)로
 *    판별한다. 저장할 때 종류를 따로 적지 않았으므로 이것이 유일한 근거다.
 * 2. 404 는 NOT_FOUND 다 — 엔진이 "없음"과 "만료"를 구분해 주지 않으므로 여기서도
 *    구분을 만들지 않는다.
 * 3. 실패는 실패로 — 연결 실패·설정 없음이 빈 성공으로 변하지 않는다.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { readSharedResult } from './scan-api';

const SCORE_BLOCK = {
  spec_id: 'veo.seo.readiness',
  spec_version: '1.8.0',
  spec_checksum: 'abc',
  status: 'SCORED',
  score: 31.5,
  band_label_ko: '취약',
  coverage: 0.8,
  confidence: 0.9,
};

const SEO_DATA = {
  target_url: 'https://grand1.co.kr/',
  summary_ko: '요약',
  scope_notice_ko: '이 결과는 입력한 1장 기준입니다.',
  score: SCORE_BLOCK,
  reach: 0.99,
  stages: [],
  checks: [],
  counts: { failed: 0, warned: 0, passed: 0, unknown: 0, not_applicable: 0 },
  top_findings: [],
  total_finding_count: 0,
  unmeasured_check_count: 0,
  result_token: 'tok',
  result_expires_at: '2026-08-09T00:00:00Z',
};

function engineResponds(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('readSharedResult', () => {
  it('저장된 SEO 결과를 화면 타입으로 매핑한다', async () => {
    vi.stubEnv('VEO_API_BASE_URL', 'https://engine.example');
    const fetchImpl = engineResponds(200, { data: SEO_DATA });

    const outcome = await readSharedResult('tok', fetchImpl);

    expect(fetchImpl).toHaveBeenCalledWith(
      'https://engine.example/public/v1/results/tok',
      expect.objectContaining({ cache: 'no-store' }),
    );
    if (!outcome.ok) {
      throw new Error(`expected ok, got ${outcome.reason}`);
    }
    expect(outcome.result.kind).toBe('SEO');
    expect(outcome.result.targetUrl).toBe('https://grand1.co.kr/');
    expect(outcome.result.score.value).toBe(31.5);
    expect(outcome.result.resultToken).toBe('tok');
  });

  it('readiness 키가 있으면 GEO 로 판별한다', async () => {
    vi.stubEnv('VEO_API_BASE_URL', 'https://engine.example');
    const { score: _score, ...rest } = SEO_DATA;
    const geoData = {
      ...rest,
      readiness: SCORE_BLOCK,
      exposure: { is_blocked: false, status_codes: [], labels_ko: [] },
    };

    const outcome = await readSharedResult('tok', engineResponds(200, { data: geoData }));

    if (!outcome.ok) {
      throw new Error(`expected ok, got ${outcome.reason}`);
    }
    expect(outcome.result.kind).toBe('GEO');
    expect(outcome.result.exposure).toEqual({ isBlocked: false, labels: [] });
  });

  it('404 는 NOT_FOUND 다 — 만료와 부재를 여기서도 구분하지 않는다', async () => {
    vi.stubEnv('VEO_API_BASE_URL', 'https://engine.example');

    const outcome = await readSharedResult('gone', engineResponds(404, { data: null }));

    expect(outcome).toEqual({ ok: false, reason: 'NOT_FOUND' });
  });

  it('엔진 주소가 없으면 NOT_CONFIGURED — 조용히 성공하지 않는다', async () => {
    // 개발 셸에 변수가 있어도 시험은 "설정 없음"을 본다.
    vi.stubEnv('VEO_API_BASE_URL', '');
    vi.stubEnv('NEXT_PUBLIC_VEO_API_BASE_URL', '');

    const outcome = await readSharedResult('tok', engineResponds(200, { data: SEO_DATA }));

    expect(outcome).toEqual({ ok: false, reason: 'NOT_CONFIGURED' });
  });

  it('연결이 끊기면 UNAVAILABLE — 만료로 위장하지 않는다', async () => {
    vi.stubEnv('VEO_API_BASE_URL', 'https://engine.example');
    const fetchImpl = vi.fn(async () => {
      throw new Error('connect refused');
    });

    const outcome = await readSharedResult('tok', fetchImpl);

    expect(outcome).toEqual({ ok: false, reason: 'UNAVAILABLE' });
  });
});
