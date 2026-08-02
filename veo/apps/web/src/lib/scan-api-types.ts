/**
 * 공개 진단 응답의 타입 — 서버(scan-api)와 클라이언트 화면이 공유한다.
 *
 * scan-api.ts 는 `server-only` 라 클라이언트 컴포넌트가 임포트할 수 없다. 타입은
 * 런타임이 없으므로 여기 따로 두고 양쪽에서 쓴다.
 */

/** 한 항목의 판정. 엔진의 `status` 와 같은 어휘를 쓴다. */
export type ScanVerdict = 'PASS' | 'WARNING' | 'FAIL' | 'NOT_APPLICABLE' | 'UNKNOWN';

export type ScanKind = 'SEO' | 'GEO';

export interface ScanFinding {
  readonly checkId: string;
  readonly title: string;
  readonly categoryId: string;
  readonly categoryName: string;
  readonly severity: string;
  /** 누가 고치는 항목인가 — 개발자 몫과 마케터 몫을 섞으면 아무도 안 고친다. */
  readonly owner: string;
  readonly verdict: ScanVerdict;
}

export interface ScanScore {
  readonly specId: string;
  readonly specVersion: string;
  readonly specChecksum: string;
  /** 채점되지 않았으면 `null`. 0 이 아니다. */
  readonly value: number | null;
  readonly bandLabel: string | null;
  readonly coverage: number;
  readonly confidence: number;
  readonly meaning: string;
}

export interface ScanStage {
  readonly categoryId: string;
  readonly name: string;
  /** 채점되지 않았으면 null. 0 이 아니다. */
  readonly score: number | null;
  readonly weight: number;
  /** 관문 — 가중 평균이 아니라 곱셈으로 들어가는 단계. */
  readonly isGate: boolean;
}

export interface ScanCheckRow {
  readonly checkId: string;
  readonly title: string;
  readonly categoryId: string;
  readonly categoryName: string;
  readonly severity: string;
  readonly owner: string;
  readonly verdict: ScanVerdict;
  readonly note: string | null;
  /** 고치면 오르는 폭 — 채점기가 실제 산식으로 계산. 화면이 어림하지 않는다. */
  readonly gainPoints: number | null;
  readonly blockedByCap: boolean;
  /** 점수를 이루지 않는 영역(연동 필요·보안 헤더류). 섞어 그리면 안 된다. */
  readonly outsideScore: boolean;
  /** 붙여넣을 수 있는 조치 코드. 정답이 하나로 정해지는 검사에만 있다. */
  readonly codeExample: string | null;
}

export interface ScanCounts {
  readonly failed: number;
  readonly warned: number;
  readonly passed: number;
  readonly unknown: number;
  readonly notApplicable: number;
}

export interface ScanPreviews {
  readonly serpTitle: string | null;
  readonly serpDescription: string | null;
  readonly ogTitle: string | null;
  readonly ogDescription: string | null;
  readonly hasOgImage: boolean;
}

export interface ScanResult {
  readonly kind: ScanKind;
  readonly targetUrl: string;
  readonly summary: string;
  readonly scopeNotice: string;
  readonly score: ScanScore;
  /** 검색에 들어갈 수 있는 비율. "도달률 × 품질" 줄이 이 값으로 그려진다. */
  readonly reach: number;
  readonly stages: readonly ScanStage[];
  readonly checks: readonly ScanCheckRow[];
  readonly counts: ScanCounts;
  readonly previews: ScanPreviews | null;
  /** GEO 전용 — 노출 차단 상태. 준비도 점수와 절대 합치지 않는다. */
  readonly exposure: { readonly isBlocked: boolean; readonly labels: readonly string[] } | null;
  readonly findings: readonly ScanFinding[];
  readonly findingCount: number;
  /** 판정에 필요한 근거를 못 모은 항목 수. 감점이 아니라 측정 범위에 반영된다. */
  readonly unmeasuredCount: number;
  /** 결과 공유 링크의 토큰. 만료된다. */
  readonly resultToken: string;
  readonly resultExpiresAt: string;
}

export type ScanFailureReason =
  | 'INVALID_URL'
  | 'RATE_LIMITED'
  | 'UNREACHABLE'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED'
  | 'SERVER_ERROR';

export type ScanOutcome =
  | { readonly ok: true; readonly result: ScanResult }
  | {
      readonly ok: false;
      readonly reason: ScanFailureReason;
      readonly retryAfterSeconds: number | null;
    };
