/**
 * Scoring specs currently published in `packages/scoring-specs`.
 *
 * These identifiers are display metadata only — VEO never hard-codes weights,
 * severities or caps in the frontend. When `@veo/api-client` exists this list
 * is replaced by the API's spec registry.
 */
/*
 * PUBLISHED_SCORING_SPECS 하드코딩 목록은 2026-08-02 에 제거됐다.
 *
 * 화면이 1.0.0 이라고 말하는 동안 실제 발행본은 1.9.0 이었다 — 같은 값을 두 곳이
 * 들고 있으면 한쪽만 고쳐도 나머지가 조용히 틀린다. 발행 명세는 이제
 * lib/scoring-specs.ts 가 API 에서 실시간으로 읽는다. 버전·가중치·상한을 이
 * 파일에 다시 적지 말 것.
 */

/** Severity vocabulary defined by the scoring specs. */
export const SEVERITIES: readonly { readonly id: string; readonly label: string; readonly meaning: string }[] = [
  { id: 'BLOCKER', label: '차단', meaning: '색인 자체를 막을 수 있는 문제입니다.' },
  { id: 'CRITICAL', label: '치명', meaning: '해석·제공에 큰 영향을 주는 문제입니다.' },
  { id: 'MAJOR', label: '중대', meaning: '품질에 눈에 띄는 영향을 주는 문제입니다.' },
  { id: 'MINOR', label: '경미', meaning: '영향이 제한적인 개선 항목입니다.' },
  { id: 'INFO', label: '참고', meaning: '감점 없이 참고로만 남기는 항목입니다.' },
];
