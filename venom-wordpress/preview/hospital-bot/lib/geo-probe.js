'use strict';

// ============================================================
// geo-probe — 병원의 생성형 AI(GEO/AEO) 노출 진단
// ------------------------------------------------------------
// P0(현재): 인터페이스 확정 + 프롬프트셋 생성만. 실제 LLM 다중 프로빙은 P1에서 구현.
// P1(예정): 환자 의도 프롬프트 12개 × {ChatGPT, Perplexity, Gemini} 질의 →
//           병원명 언급/인용 여부 집계 → 인용률·SoV·감성 → 등급(A~F).
// 지금은 status:'pending'을 반환해 오케스트레이터가 진단서에 "P1 예정"으로 표기한다.
// (환각·허위수치 방지: 미구현 지표를 임의로 만들지 않는다 — CLAUDE.md 준수)
// ============================================================

// 진료과 카테고리 → 환자 의도 프롬프트 시드
function buildPromptSet(name, category, region) {
  const dept = simplifyDept(category);
  const loc = region || '';
  const q = [
    `${loc} ${dept} 잘하는 곳 추천해줘`,
    `${loc} ${dept} 어디가 좋아?`,
    `${loc}에서 ${dept} 유명한 병원 알려줘`,
    `${loc} ${dept} 후기 좋은 곳`,
    `${name} 어때? 평판 알려줘`,
    `${loc} ${dept} 비용 저렴한 곳`,
  ].map((s) => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return Array.from(new Set(q));
}

function simplifyDept(category) {
  const c = String(category || '');
  const m = c.match(/(치과|피부과|성형외과|정형외과|한의원|한방|안과|내과|이비인후과|산부인과|비뇨기과|치아교정|임플란트)/);
  return m ? m[1] : (c.split('>').pop() || '병원').trim();
}

// P0 스텁: 실제 프로빙 없이 상태/프롬프트셋만 반환
async function probe(name, { category = '', region = '' } = {}) {
  const prompts = buildPromptSet(name, category, region);
  return {
    status: 'pending',          // P1에서 'done'으로 전환
    grade: null,                // A~F (미측정)
    citationRate: null,         // 언급 프롬프트 / 전체
    shareOfVoice: null,         // 자병원 언급 / (자+경쟁)
    sentiment: null,            // positive|neutral|negative
    engines: ['chatgpt', 'perplexity', 'gemini'],
    prompts,                    // 실제 질의에 쓸 프롬프트셋(P1 입력)
    note: 'GEO 프로빙은 P1에서 활성화됩니다. 현재는 프롬프트셋만 준비합니다.',
  };
}

module.exports = { probe, buildPromptSet, simplifyDept };
