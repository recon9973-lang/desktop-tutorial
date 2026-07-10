'use strict';

// ============================================================
// geo-probe — 병원의 생성형 AI(GEO/AEO) 노출 진단  (P1: 실 프로빙)
// ------------------------------------------------------------
// 환자 의도 프롬프트를 ChatGPT·Perplexity·Gemini·Claude에 실제로 던져
// 답변에 병원명이 언급/인용되는지 집계 → 인용률·SoV·감성 → 등급(A~F).
//
// 두 모드:
//   preview()  종합 카드용 — 호출 없이 엔진 가용성 + 프롬프트셋만(즉시).
//   probe()    'geo' 명령용 — 실제 다중 질의(느림·유료). 비용/지연은 여기에 격리.
//
// 원칙: 실측 결과만 수치화. 미설정/실패는 status로 정직 표기(허위수치 없음).
// 엔진 asker는 lib/ai-engines 단일 소스 재사용.
// ============================================================

// 진료과 카테고리 → 환자 의도 프롬프트 시드
function simplifyDept(category) {
  const c = String(category || '');
  const m = c.match(/(치과|피부과|성형외과|정형외과|한의원|한방|안과|내과|이비인후과|산부인과|비뇨기과|치아교정|임플란트|통증|재활)/);
  return m ? m[1] : (c.split('>').pop() || '병원').trim();
}

function buildPromptSet(name, category, region) {
  const dept = simplifyDept(category);
  const loc = region || '';
  const q = [
    `${loc} ${dept} 잘하는 곳 추천해줘`,
    `${loc} ${dept} 어디가 좋아?`,
    `${loc}에서 ${dept} 유명한 병원 알려줘`,
    `${loc} ${dept} 후기 좋은 곳`,
    `${name} 평판 어때?`,
    `${loc} ${dept} 비용 합리적인 곳`,
  ].map((s) => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return Array.from(new Set(q));
}

// 병원명에서 브랜드 토큰 추출(지역·진료과·법인격 접미 제거)
const DEPT_SUFFIX = /(치과병원|한방병원|치과의원|치과|피부과|성형외과|정형외과|이비인후과|산부인과|비뇨기과|가정의학과|한의원|안과|내과|의원|병원|클리닉|의료재단)/g;
function brandToken(name, region) {
  let s = String(name || '');
  if (region) s = s.split(region).join('');
  s = s.replace(DEPT_SUFFIX, '').replace(/[^가-힣A-Za-z0-9]/g, '').trim();
  return s;
}

// 답변 텍스트에 병원 언급 여부
function mentionInText(text, name, region) {
  if (!text || !name) return false;
  const t = String(text);
  if (t.includes(name)) return true;
  const brand = brandToken(name, region);
  // 브랜드 토큰이 충분히 고유(2자+)할 때만 부분매칭 — '치과'만으로 오탐 방지
  if (brand && brand.length >= 2 && t.includes(brand)) return true;
  return false;
}

function gradeFromRate(rate) {
  if (rate == null) return null;
  if (rate >= 0.6) return 'A';
  if (rate >= 0.4) return 'B';
  if (rate >= 0.25) return 'C';
  if (rate > 0) return 'D';
  return 'F';
}

// 답변들에서 병원명류를 뽑아 우리 vs 경쟁 언급 점유율(SoV) 근사
const CLINIC_RE = /[가-힣A-Za-z0-9]{2,12}(?:치과병원|한방병원|치과의원|치과|피부과|성형외과|정형외과|이비인후과|산부인과|비뇨기과|한의원|안과|내과|의원|병원|클리닉)/g;
function computeShareOfVoice(answers, name, region) {
  const brand = brandToken(name, region);
  let ours = 0, total = 0;
  const others = {};
  answers.forEach((a) => {
    const found = String(a || '').match(CLINIC_RE) || [];
    found.forEach((f) => {
      total++;
      const isOurs = (name && f.includes(brand) && brand.length >= 2) || (name && name.includes(f));
      if (isOurs) ours++;
      else others[f] = (others[f] || 0) + 1;
    });
  });
  if (total === 0) return { sov: null, competitors: [] };
  const competitors = Object.entries(others).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([n, c]) => ({ name: n, mentions: c }));
  return { sov: ours / total, competitors };
}

const POS = ['추천', '유명', '잘하', '친절', '좋은', '만족', '인기', '신뢰', '평판이 좋'];
const NEG = ['불친절', '별로', '실망', '비싸', '논란', '주의', '비추'];
function computeSentiment(mentionAnswers, name, region) {
  const brand = brandToken(name, region);
  let pos = 0, neg = 0;
  mentionAnswers.forEach((txt) => {
    const t = String(txt);
    const idx = t.indexOf(name) >= 0 ? t.indexOf(name) : (brand ? t.indexOf(brand) : -1);
    if (idx < 0) return;
    const win = t.slice(Math.max(0, idx - 40), idx + 40);
    if (POS.some((w) => win.includes(w))) pos++;
    if (NEG.some((w) => win.includes(w))) neg++;
  });
  if (pos === 0 && neg === 0) return 'neutral';
  return pos >= neg ? 'positive' : 'negative';
}

// ── preview: 종합 카드용(호출 없음) ──────────────────
function preview(name, { category = '', region = '', deps } = {}) {
  const ai = (deps && deps.ai) || require('../../lib/ai-engines');
  const engines = ai.availableEngines();
  const prompts = buildPromptSet(name, category, region);
  return {
    status: engines.length ? 'ready' : 'unconfigured',
    mode: 'preview',
    grade: null, citationRate: null, shareOfVoice: null, sentiment: null,
    engines, prompts,
    note: engines.length
      ? `'geo' 명령으로 ${engines.length}개 AI 엔진 실측을 실행할 수 있습니다.`
      : 'AI 엔진 키(PERPLEXITY/OPENAI/GEMINI/ANTHROPIC) 미설정 — 실측 불가.',
  };
}

// ── probe: 실 프로빙(느림·유료) ──────────────────────
async function probe(name, { category = '', region = '', deps, maxPrompts = 4, maxEngines = 3 } = {}) {
  const ai = (deps && deps.ai) || require('../../lib/ai-engines');
  const prompts = buildPromptSet(name, category, region).slice(0, maxPrompts);
  const engines = ai.availableEngines().slice(0, maxEngines);
  if (!engines.length) {
    return Object.assign(preview(name, { category, region, deps }), { mode: 'probe' });
  }

  const results = [];
  for (const eng of engines) {
    for (const q of prompts) {
      try {
        const out = await ai.ask(eng, q);
        const answer = (out && out.answer) || '';
        results.push({ engine: eng, prompt: q, answer, mentioned: mentionInText(answer, name, region), citations: (out && out.citations) || [] });
      } catch (e) {
        results.push({ engine: eng, prompt: q, error: e.message, mentioned: false, answer: '' });
      }
    }
  }

  const valid = results.filter((r) => !r.error);
  const mentions = valid.filter((r) => r.mentioned);
  const citationRate = valid.length ? mentions.length / valid.length : null;

  // 엔진별 인용률
  const perEngine = {};
  engines.forEach((e) => {
    const v = valid.filter((r) => r.engine === e);
    perEngine[e] = { asked: v.length, mentioned: v.filter((r) => r.mentioned).length,
      rate: v.length ? v.filter((r) => r.mentioned).length / v.length : null };
  });

  const { sov, competitors } = computeShareOfVoice(valid.map((r) => r.answer), name, region);
  const sentiment = computeSentiment(mentions.map((r) => r.answer), name, region);

  return {
    status: 'done', mode: 'probe',
    grade: gradeFromRate(citationRate),
    citationRate, shareOfVoice: sov, sentiment,
    engines, perEngine, competitors,
    asked: valid.length, mentionedCount: mentions.length,
    prompts,
    errors: results.filter((r) => r.error).map((r) => ({ engine: r.engine, error: r.error })),
    samples: mentions.slice(0, 2).map((r) => ({ engine: r.engine, prompt: r.prompt, excerpt: String(r.answer).slice(0, 160) })),
    note: '공개 AI 검색 실측 결과(참고용).',
  };
}

module.exports = { preview, probe, buildPromptSet, simplifyDept, brandToken, mentionInText, gradeFromRate, computeShareOfVoice, computeSentiment };
