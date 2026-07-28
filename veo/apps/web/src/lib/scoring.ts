/**
 * Scoring specs currently published in `packages/scoring-specs`.
 *
 * These identifiers are display metadata only — VEO never hard-codes weights,
 * severities or caps in the frontend. When `@veo/api-client` exists this list
 * is replaced by the API's spec registry.
 */
export interface ScoringSpecSummary {
  readonly specId: string;
  readonly version: string;
  readonly domain: string;
  readonly status: string;
  readonly effectiveAt: string;
  readonly methodologyOwner: string;
  readonly implementationOwner: string;
  readonly meaning: string;
}

export const PUBLISHED_SCORING_SPECS: readonly ScoringSpecSummary[] = [
  {
    specId: 'veo.seo.readiness',
    version: '1.0.0',
    domain: 'SEO 기술 준비도',
    status: '발행됨',
    effectiveAt: '2026-07-28T00:00:00+09:00',
    methodologyOwner: 'VEO-LAB',
    implementationOwner: 'VENOM',
    meaning:
      '검색엔진이 사이트를 발견·크롤링·해석·제공할 수 있는 기술·운영 준비도입니다. 검색 순위 예측값이 아닙니다.',
  },
  {
    specId: 'veo.geo.readiness',
    version: '1.0.0',
    domain: 'GEO 준비도',
    status: '발행됨',
    effectiveAt: '2026-07-28T00:00:00+09:00',
    methodologyOwner: 'VEO-LAB',
    implementationOwner: 'VENOM',
    meaning:
      'AI 답변 엔진이 페이지에 접근·추출·검증할 수 있는 구조 준비도입니다. 실제 AI 노출·인용 여부는 별도의 AI 가시성 관측 결과로만 확인합니다.',
  },
];

export function specLabel(spec: ScoringSpecSummary): string {
  return `${spec.specId} ${spec.version}`;
}

/** Severity vocabulary defined by the scoring specs. */
export const SEVERITIES: readonly { readonly id: string; readonly label: string; readonly meaning: string }[] = [
  { id: 'BLOCKER', label: '차단', meaning: '색인 자체를 막을 수 있는 문제입니다.' },
  { id: 'CRITICAL', label: '치명', meaning: '해석·제공에 큰 영향을 주는 문제입니다.' },
  { id: 'MAJOR', label: '중대', meaning: '품질에 눈에 띄는 영향을 주는 문제입니다.' },
  { id: 'MINOR', label: '경미', meaning: '영향이 제한적인 개선 항목입니다.' },
  { id: 'INFO', label: '참고', meaning: '감점 없이 참고로만 남기는 항목입니다.' },
];
