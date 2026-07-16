import type { SiteMetrics } from "./metrics";
import type { Suggestion } from "./rules";

export type Report = {
  headline: string;
  summary: string;
  actions: { title: string; why: string; how: string; priority: number }[];
  outlook: string;
  generatedNote: string;
};

const INDUSTRY_FRAME: Record<string, { goal: string; unit: string }> = {
  ECOMMERCE: { goal: "구매 전환", unit: "구매" },
  CLINIC: { goal: "예약·문의 전환", unit: "예약/문의" },
  EDU: { goal: "수강 신청 전환", unit: "신청" },
  B2B: { goal: "문의·리드 전환", unit: "문의" },
  ETC: { goal: "핵심 전환", unit: "전환" },
};

// 룰 엔진 결과 + 지표를 고객 보고용 한국어 서술형 리포트로 합성한다.
// 결정론적 생성이므로 API 키 없이 동작한다. LLM 문장 다듬기는 lib/llm.ts의 polishKorean 참고.
export function generateReport(siteName: string, industry: string, m: SiteMetrics, suggestions: Suggestion[]): Report {
  const frame = INDUSTRY_FRAME[industry] ?? INDUSTRY_FRAME.ETC;
  const real = suggestions.filter((s) => s.id !== "low-data");

  // 헤드라인: 가장 우선순위 높은 과제 기준
  const top = real[0];
  const headline = top
    ? `${frame.goal}을 높이려면 "${top.title}"부터 개선하는 것을 권장합니다.`
    : `현재 큰 이상 신호는 없습니다. 데이터를 더 쌓아 세밀한 개선점을 찾아보세요.`;

  // 현황 요약
  const summary =
    `분석 기간 동안 ${m.sessions.toLocaleString()}개의 세션이 수집되었고, ` +
    `이 중 모바일 방문이 ${m.device.mobilePct}%로 ${m.device.mobilePct >= 50 ? "다수를 차지합니다" : "일부를 차지합니다"}. ` +
    `단일 페이지 이탈률은 ${m.bounceRate}%, 평균 스크롤 도달은 ${m.avgScroll}%이며, ` +
    `${frame.unit} 전환은 ${m.conversions.toLocaleString()}건 발생했습니다. ` +
    (m.deadClicks + m.rageClicks > 0
      ? `또한 반응 없는 클릭 ${m.deadClicks}건, 좌절 클릭 ${m.rageClicks}건이 감지되어 인터랙션 개선 여지가 있습니다.`
      : `주목할 만한 좌절 클릭은 관찰되지 않았습니다.`);

  // 우선 조치 (상위 3개를 why/how로 풀어씀)
  const actions = real.slice(0, 3).map((s, i) => ({
    title: s.title,
    why: s.evidence,
    how: s.detail,
    priority: i + 1,
  }));

  // 기대 효과 / 다음 점검
  const outlook =
    real.length > 0
      ? `위 ${Math.min(3, real.length)}가지를 먼저 적용하고 2~4주 뒤 같은 지표를 재측정하면, ` +
        `${top?.area ?? "핵심"} 영역의 개선 효과를 이탈률·스크롤 도달률·${frame.unit} 전환 변화로 확인할 수 있습니다. ` +
        `개선 전/후 비교는 다음 리포트에서 자동으로 제공됩니다.`
      : `현재는 관찰 단계입니다. 세션이 500개 이상 쌓이면 제안 신뢰도가 높아집니다.`;

  const confidenceWord = m.sessions >= 500 ? "높음" : m.sessions >= 100 ? "보통" : "낮음(표본 부족)";
  const generatedNote = `이 리포트는 수집 지표에서 룰 엔진으로 자동 생성되었습니다. 데이터 신뢰도: ${confidenceWord} (세션 ${m.sessions.toLocaleString()}개 기준).`;

  return { headline, summary, actions, outlook, generatedNote };
}
