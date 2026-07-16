// 요금제 정의 (2026-07 확정). 표시·제한의 단일 기준(single source of truth).
export type Feature =
  | "maps_all" // 히트맵 5종 전부 (없으면 클릭맵만)
  | "funnel"
  | "replay" // 세션 리플레이
  | "suggestions" // 진단 · 개선 제안 분석 (대행사 전용)
  | "whitelabel" // 화이트라벨 로고/리포트
  | "share" // 고객 공유 링크
  | "compare"; // 전/후 비교

export type Plan = {
  key: "FREE" | "GROWTH" | "AGENCY";
  name: string;
  priceLabel: string;
  price: number; // 월, 원
  sessionsPerMonth: number; // 월 세션 한도
  overagePer10k: number; // 초과 1만 세션당 원 (0이면 초과 시 수집 정지)
  sites: number;
  retentionDays: number; // 원시 데이터 보관일
  snapshotDays: number; // 집계 스냅샷 보관일 (원시 삭제 후에도 히트맵 유지)
  trialDays: number; // 0이면 체험 아님
  features: Feature[];
  highlights: string[];
  target: string;
};

export const PLANS: Plan[] = [
  {
    key: "FREE",
    name: "무료 체험",
    priceLabel: "0원",
    price: 0,
    sessionsPerMonth: 500,
    overagePer10k: 0, // 초과 시 수집 정지
    sites: 1,
    retentionDays: 14,
    snapshotDays: 14,
    trialDays: 14,
    features: [],
    target: "체험 (14일)",
    highlights: ["14일 체험", "월 500 세션", "1개 사이트", "14일 보관", "클릭 히트맵"],
  },
  {
    key: "GROWTH",
    name: "그로우",
    priceLabel: "19,800원",
    price: 19800,
    sessionsPerMonth: 20000,
    overagePer10k: 9900,
    sites: 3,
    retentionDays: 90,
    snapshotDays: 180,
    trialDays: 0,
    features: ["maps_all", "funnel", "replay"],
    target: "쇼핑몰 / 소상공인",
    highlights: ["월 20,000 세션", "3개 사이트", "90일 보관", "히트맵 5종 · 퍼널 · 세션 리플레이"],
  },
  {
    key: "AGENCY",
    name: "에이전시",
    priceLabel: "88,000원",
    price: 88000,
    sessionsPerMonth: 100000,
    overagePer10k: 8800,
    sites: 30,
    retentionDays: 90,
    snapshotDays: 365,
    trialDays: 0,
    features: ["maps_all", "funnel", "replay", "suggestions", "whitelabel", "share", "compare"],
    target: "대행사",
    highlights: ["월 100,000 세션", "30개 사이트", "원시 90일 + 집계 1년", "진단 · 화이트라벨 · 공유링크 · 전후비교"],
  },
];

export function getPlan(key: string | undefined | null): Plan {
  return PLANS.find((p) => p.key === key) ?? PLANS[0];
}

// 해당 플랜이 기능을 쓸 수 있는지
export function can(planKey: string | undefined | null, feature: Feature): boolean {
  return getPlan(planKey).features.includes(feature);
}
