import type { SiteMetrics } from "./metrics";

export type Confidence = "HIGH" | "MEDIUM" | "LOW";
export type Suggestion = {
  id: string;
  title: string;
  detail: string;
  evidence: string;
  confidence: Confidence;
  impact: number; // 1~5, 우선순위 정렬용
  area: string; // 개선 영역
};

// 세션 수 기반 신뢰도. 사업계획서 8장 기준.
function confidenceOf(sessions: number): Confidence {
  if (sessions >= 500) return "HIGH";
  if (sessions >= 100) return "MEDIUM";
  return "LOW";
}

// 룰 엔진: 결정론적 규칙으로 한국어 개선 제안 생성.
// AI 문장화는 2단계. 초기에는 규칙 기반이 신뢰도 관리에 유리하다.
export function generateSuggestions(m: SiteMetrics): Suggestion[] {
  const out: Suggestion[] = [];
  const conf = confidenceOf(m.sessions);

  // 1) 모바일 CTA 노출 문제
  if (m.device.mobilePct >= 50 && m.ctaViewRate < 40) {
    out.push({
      id: "mobile-cta",
      title: "모바일 방문자가 핵심 버튼을 보기 전에 이탈합니다",
      detail: "모바일 첫 화면에 고정(sticky) CTA를 추가하거나, 핵심 버튼을 상단으로 올려 스크롤 없이 노출되게 하세요.",
      evidence: `모바일 비중 ${m.device.mobilePct}%, CTA 노출률 ${m.ctaViewRate}%.`,
      confidence: conf,
      impact: 5,
      area: "CTA / 모바일",
    });
  }

  // 2) Dead click (클릭되지 않는 요소 반복 클릭)
  if (m.deadClickRate >= 5 && m.deadClicks >= 5) {
    out.push({
      id: "dead-click",
      title: "클릭되지 않는 요소를 누르는 방문자가 있습니다",
      detail: "이미지/텍스트처럼 보이지만 클릭이 안 되는 영역을 실제 버튼·링크로 바꾸거나, 상세보기/확대 기능을 추가하세요.",
      evidence: `전체 클릭 중 반응 없는 클릭(dead click) 비율 ${m.deadClickRate}% (${m.deadClicks}건).`,
      confidence: conf,
      impact: 4,
      area: "인터랙션",
    });
  }

  // 3) Rage click (좌절 클릭)
  if (m.rageClicks >= 3) {
    out.push({
      id: "rage-click",
      title: "특정 요소에서 좌절 클릭(rage click)이 감지됩니다",
      detail: "같은 위치를 빠르게 반복 클릭하는 패턴입니다. 버튼 반응 속도, 로딩 지연, 클릭 영역 크기를 점검하세요.",
      evidence: `좌절 클릭 ${m.rageClicks}건 발생.`,
      confidence: conf,
      impact: 4,
      area: "인터랙션 / 성능",
    });
  }

  // 4) 스크롤 이탈 (핵심 메시지 하단 배치)
  if (m.scrollReach.p50 < 40) {
    out.push({
      id: "scroll-drop",
      title: "방문자 다수가 페이지 중반 이전에 이탈합니다",
      detail: "페이지 절반까지 도달하는 방문자가 적습니다. 핵심 메시지·혜택·CTA를 상단으로 끌어올리세요.",
      evidence: `50% 지점 도달률 ${m.scrollReach.p50}% (평균 스크롤 ${m.avgScroll}%).`,
      confidence: conf,
      impact: 3,
      area: "콘텐츠 배치",
    });
  }

  // 5) 폼 이탈
  if (m.formStarts >= 5 && m.formCompletionRate < 30) {
    out.push({
      id: "form-drop",
      title: "폼을 시작한 방문자의 이탈이 큽니다",
      detail: "입력 항목을 줄이거나 단계로 분리하고, 불필요한 필수값을 제거하세요. 비회원 진행/간편 로그인도 검토하세요.",
      evidence: `폼 시작 ${m.formStarts}세션 중 제출 ${m.formSubmits}건, 완료율 ${m.formCompletionRate}%.`,
      confidence: conf,
      impact: 5,
      area: "폼 / 전환",
    });
  }

  // 6) 높은 이탈률 (데스크톱 중심 사이트) — 모바일 중심이면 아래 mobile-bounce가 대신 처리
  if (m.bounceRate >= 70 && m.sessions >= 50 && m.device.mobilePct < 50) {
    out.push({
      id: "bounce",
      title: "이탈률이 높습니다",
      detail: "유입 채널과 첫 화면(광고 문구-랜딩 일치)을 점검하세요. 로딩 속도와 첫 화면 메시지가 흔한 원인입니다.",
      evidence: `이탈률 ${m.bounceRate}% (세션 ${m.sessions}).`,
      confidence: conf,
      impact: 3,
      area: "유입 / 첫인상",
    });
  }

  // 7) 모바일 이탈 — 모바일 비중이 높은데 이탈률도 높음
  if (m.device.mobilePct >= 50 && m.bounceRate >= 65 && m.sessions >= 50) {
    out.push({
      id: "mobile-bounce",
      title: "모바일 방문자 이탈이 큽니다",
      detail: "모바일 로딩 속도, 첫 화면 메시지, 버튼 크기·위치를 점검하세요. 데스크톱과 모바일은 화면이 달라 따로 봐야 합니다.",
      evidence: `모바일 비중 ${m.device.mobilePct}%, 이탈률 ${m.bounceRate}% (세션 ${m.sessions}).`,
      confidence: conf,
      impact: 4,
      area: "모바일 / 첫인상",
    });
  }

  // 8) 끝까지 읽는데 전환이 없음 — 콘텐츠는 소비하나 행동으로 안 이어짐
  if (m.conversions === 0 && m.sessions >= 100 && m.scrollReach.p75 >= 50) {
    out.push({
      id: "engaged-no-convert",
      title: "끝까지 읽는데 전환이 없습니다",
      detail: "방문자가 페이지를 깊이까지 보는데도 전환이 없습니다. CTA가 약하거나 눈에 안 띄는 경우가 많습니다 — 버튼 문구·색·위치와 오퍼를 강화하세요.",
      evidence: `75% 지점 도달률 ${m.scrollReach.p75}%인데 전환 0건 (세션 ${m.sessions}).`,
      confidence: conf,
      impact: 4,
      area: "전환 / CTA",
    });
  }

  // 9) 방문은 있는데 전환이 없음 (일반) — 위 engaged 케이스가 아닐 때
  if (m.conversions === 0 && m.sessions >= 100 && m.scrollReach.p75 < 50) {
    out.push({
      id: "no-convert",
      title: "방문은 있는데 전환이 없습니다",
      detail: "전환(구매·문의·신청)이 한 건도 없습니다. 방문자가 깊이 보기 전에 이탈하고 있으니, 첫 화면의 가치 제안과 CTA 노출부터 점검하세요.",
      evidence: `세션 ${m.sessions}개, 전환 0건 (75% 도달률 ${m.scrollReach.p75}%).`,
      confidence: conf,
      impact: 4,
      area: "전환 / 첫인상",
    });
  }

  // 데이터 부족 경고
  if (m.sessions < 100) {
    out.push({
      id: "low-data",
      title: "데이터가 더 쌓이면 제안 신뢰도가 올라갑니다",
      detail: "현재 세션 수가 적어 제안의 신뢰도가 낮습니다. 100세션 이상 수집되면 자동으로 신뢰도가 상향됩니다.",
      evidence: `현재 세션 ${m.sessions}개.`,
      confidence: "LOW",
      impact: 1,
      area: "데이터",
    });
  }

  return out.sort((a, b) => b.impact - a.impact);
}
