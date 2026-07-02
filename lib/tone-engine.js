'use strict';

/**
 * tone-engine.js — 원고작성 프로젝트 "이중 톤 + 타겟 페르소나" 레이어
 *
 * 베놈 기본 SYSTEM_PROMPT(마케팅 voice) 위에 얹어, 독자(타겟)에 맞춘
 * "다정한 구어체 + 신뢰의 문어체" 지시를 생성한다.
 *
 * 설계 원칙:
 *  - 비침투(non-invasive): generatePost에서 target/tone이 없으면 빈 문자열을 반환 → 기존 동작 그대로.
 *  - 구조 불변: 베놈 10단 구조(①~⑩)는 유지하고 '목소리(voice)'만 조정한다.
 *  - studio.html의 페르소나/톤 정의와 1:1 동기화.
 */

// ── 타겟 페르소나 (studio.html TARGETS와 동기화) ──
const TARGET_PERSONAS = {
  '직장인': {
    detail: '하루 8시간 앉아 일하는 30대 직장인',
    pains: ['바빠서 병원 갈 시간이 없다', '증상이 일상에 자꾸 끼어든다', '큰 병일까 막연히 불안하다'],
    questions: ['일하면서도 관리할 수 있나요?', '병원 한 번이면 끝나나요?', '지금 안 가도 괜찮을까요?'],
    action: '점심시간 10분, 가까운 곳에서 간단 체크 예약',
  },
  '환자 본인': {
    detail: '이미 증상이 뚜렷해 진단·치료가 궁금한 분',
    pains: ['치료가 얼마나 걸릴지 모르겠다', '재발이 두렵다', '일상으로 돌아갈 수 있을까'],
    questions: ['치료법은 뭐가 있나요?', '회복까지 얼마나 걸리나요?', '재발을 막으려면?'],
    action: '내 상태에 맞는 치료 계획 상담받기',
  },
  '보호자·가족': {
    detail: '부모님/배우자를 걱정하는 가족',
    pains: ['대신 알아봐 드리고 싶다', '어디부터 시작할지 모르겠다', '괜히 겁만 줄까 조심스럽다'],
    questions: ['어떤 병원에 모셔야 하나요?', '집에서 뭘 도와드릴 수 있나요?', '지금 상태가 위험한가요?'],
    action: '보호자가 함께 보는 체크리스트로 첫 진료 준비',
  },
  '예방 관심층': {
    detail: '아직 증상은 없지만 미리 챙기려는 분',
    pains: ['지금 괜찮아도 나중이 걱정', '뭘 해야 예방되는지 모른다', '검진이 필요한지 헷갈린다'],
    questions: ['예방하려면 뭘 하나요?', '검진은 언제 받나요?', '생활습관만으로 충분한가요?'],
    action: '나에게 맞는 예방수칙·검진주기 확인',
  },
};

// ── 톤 프리셋 (0~100 슬라이더 → 3구간, studio.html 톤 믹서와 동기화) ──
const TONE_PRESETS = {
  warm: {
    label: '다정함 우선',
    mix: '다정한 구어체의 비중을 높여 따뜻하게',
    ratio: '공감·말걸기 문장(구어체)을 정보 문장보다 자주 배치',
  },
  balanced: {
    label: '균형',
    mix: '공감(구어체)과 정보(문어체)를 비슷한 비중으로',
    ratio: '한 단락 안에서도 공감 한 문장 → 정보 한 문장의 리듬을 살려',
  },
  professional: {
    label: '전문성 우선',
    mix: '신뢰감 있는 문어체의 비중을 높여 전문적으로',
    ratio: '정보·근거 문장(문어체) 위주로, 공감 문장은 도입·마무리에 절제해서',
  },
};

/**
 * 숫자 톤(0~100) 또는 프리셋 키를 정규화해 프리셋 키를 반환.
 * @param {number|string} tone
 * @returns {'warm'|'balanced'|'professional'}
 */
function resolveTonePreset(tone) {
  if (typeof tone === 'string' && TONE_PRESETS[tone]) return tone;
  const n = Number(tone);
  if (!Number.isFinite(n)) return 'balanced';
  if (n < 33) return 'warm';
  if (n < 67) return 'balanced';
  return 'professional';
}

/**
 * 타겟 키를 정규화 (부분 일치 허용: '환자' → '환자 본인').
 * @param {string} target
 * @returns {string|null} 정규 키 또는 null
 */
function resolveTarget(target) {
  if (!target) return null;
  if (TARGET_PERSONAS[target]) return target;
  const t = String(target).trim();
  const hit = Object.keys(TARGET_PERSONAS).find(k => k.includes(t) || t.includes(k.replace(/·.*/, '')));
  return hit || null;
}

/**
 * 생성 프롬프트에 주입할 "독자 페르소나 + 이중 톤" 지시 블록을 만든다.
 * target과 tone이 모두 비어 있으면 빈 문자열(기존 동작 유지).
 *
 * @param {object} opts
 * @param {string} [opts.target]  - '직장인' | '환자 본인' | '보호자·가족' | '예방 관심층'
 * @param {string} [opts.detail]  - 타겟 한 줄 묘사(있으면 우선)
 * @param {number|string} [opts.tone] - 0~100 또는 프리셋 키
 * @returns {string} userPrompt에 끼울 지시 블록(앞뒤 개행 포함) 또는 ''
 */
function buildToneDirective({ target, detail, tone } = {}) {
  const tKey = resolveTarget(target);
  const hasTone = tone !== undefined && tone !== null && tone !== '';
  if (!tKey && !hasTone) return '';

  const persona = tKey ? TARGET_PERSONAS[tKey] : null;
  const preset = TONE_PRESETS[resolveTonePreset(hasTone ? tone : 'balanced')];

  const lines = ['★독자 페르소나 & 말투(베놈 구조는 유지하되 목소리를 이 지시에 맞춰라 — 최우선)★'];

  if (persona) {
    lines.push(`- 이 글의 독자: ${tKey} — ${detail || persona.detail}`);
    lines.push(`- 독자가 느끼는 불안: ${persona.pains.join(' · ')}`);
    lines.push(`- 독자가 궁금한 것: ${persona.questions.join(' · ')} (소제목·FAQ에 자연스럽게 반영)`);
    lines.push(`- 유도할 행동(CTA 방향): ${persona.action}`);
  } else if (detail) {
    lines.push(`- 이 글의 독자: ${detail}`);
  }

  lines.push(
    `- 말투: ${preset.mix} 쓴다. ${preset.ratio}.`,
    '  · 공감·말 걸기·전환·마무리 = 다정한 구어체("~하시죠?", "~거든요", "~해요")',
    '  · 증상·통계·치료법 등 핵심 정보 = 신뢰의 문어체("~입니다", "~합니다")',
    '- 도입부 리드는 핵심 결론·수치를 담되, 독자의 일상 장면으로 공감하며 다정하게 연다.',
    '- 독자를 환자/고객이 아니라 "내가 아끼는 사람"처럼 대한다. 겁주지 말고 안심시킨다.',
    '- 어려운 의학 용어는 괄호로 쉽게 풀어준다. 예: 경추(목뼈).',
    '- 과장·공포 마케팅, 단정적 효능 보장은 금지(의료광고법 준수).'
  );

  return '\n' + lines.join('\n') + '\n';
}

module.exports = {
  TARGET_PERSONAS,
  TONE_PRESETS,
  resolveTonePreset,
  resolveTarget,
  buildToneDirective,
};
