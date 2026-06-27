'use strict';

const { chatComplete } = require('./openai-client');
const { validateMedicalAd, autoFix } = require('./medical-ad-validator');

const CAT_LABEL = {
  geo:'GEO/AI마케팅', seo:'SEO마케팅', dental:'치과마케팅',
  skin:'피부과마케팅', oriental:'한의원마케팅', ortho:'정형외과마케팅',
  plastic:'성형외과마케팅', naegwa:'내과마케팅', angwa:'안과마케팅',
  shimui:'의료광고심의', geo_local:'지역마케팅',
};

// 이미지 프롬프트 — 카테고리별 고정 템플릿 (AI 호출 없이 토큰 절약)
const IMAGE_PROMPT = {
  geo:      'Modern hospital reception desk with digital marketing analytics dashboard on screen, professional Korean medical facility, clean white interior, warm lighting',
  seo:      'Korean medical professional reviewing SEO analytics on laptop in bright clinic office, search ranking graphs visible on screen',
  dental:   'Modern dental clinic interior with professional equipment, Korean dentist in clean white coat, bright examination room',
  skin:     'Upscale Korean dermatology clinic consultation room, professional skincare equipment, soft lighting, clean aesthetic',
  oriental: 'Traditional Korean oriental medicine clinic with modern interior, acupuncture and herb medicine elements, professional setting',
  ortho:    'Physical therapy room in Korean orthopedic clinic, rehabilitation equipment, professional medical staff',
  plastic:  'Premium Korean aesthetic clinic consultation room, professional medical staff, modern clean interior design',
  naegwa:   'Korean internal medicine clinic with professional doctor consulting patient, modern medical equipment, clean environment',
  angwa:    'Korean ophthalmology clinic with eye examination equipment, professional optometrist, bright clean medical space',
  shimui:   'Korean medical advertising compliance meeting, professionals reviewing documents, modern conference room',
  geo_local:'Local Korean hospital building exterior with city landmark background, professional medical facility, daytime professional photo',
};

// ── 시스템 프롬프트 ──
const SYSTEM_PROMPT = `병원마케팅 에이전시 베놈(VENOM) 블로그 라이터. GEO/AEO/SEO 고품질 콘텐츠 작성.

★분량 최우선★: 본문 HTML 내 순수텍스트(공백·태그 제외) 반드시 2500~3000자. 짧으면 재작성.

구조 필수:
①역피라미드: 첫 문장=핵심결론+수치(~입니다 종결)
②<h2>핵심 요약</h2>+<ul>인사이트 4개(각 2문장 이상)
③<h3>질문형 소제목 8개+각 답변 200자 이상(수치포함)
④<table>비교표 1개(4열 이상, 5행 이상)
⑤<h2>자주 묻는 질문(FAQ)</h2>+8개 Q&A(각 답변 150자 이상)
⑥베놈 CTA 1회(구체적 연락처 유도)

의료광고법 절대금지: 최고·최상·완치·100%효과·효과보장·부작용없음·탁월한·기적·놀라운
대체표현: 효과적→체계적, 탁월→전문적, 우수→데이터기반

E-E-A-T: "베놈이 직접 진행한 사례", "실제 집행 결과 기준" 표현 포함. 수치근거 명시.`;

// ── 출력 구분자 방식 (JSON 이스케이핑 오버헤드 제거, ~200토큰 절약) ──
const DELIMITER = {
  TITLE:    '<<<TITLE>>>',
  SEO:      '<<<SEO>>>',
  META:     '<<<META>>>',
  KEYWORDS: '<<<KEYWORDS>>>',
  HTML:     '<<<HTML>>>',
  END:      '<<<END>>>',
};

function parseDelimited(raw) {
  const get = (key) => {
    const start = raw.indexOf(DELIMITER[key]);
    if (start === -1) return '';
    const end = Object.values(DELIMITER).reduce((min, d) => {
      if (d === DELIMITER[key]) return min;
      const idx = raw.indexOf(d, start + DELIMITER[key].length);
      return idx > -1 && idx < min ? idx : min;
    }, raw.length);
    return raw.slice(start + DELIMITER[key].length, end).trim();
  };
  return {
    title:    get('TITLE'),
    seoTitle: get('SEO'),
    metaDesc: get('META'),
    keywords: get('KEYWORDS'),
    html:     get('HTML'),
  };
}

async function generatePost({ category, keyword, region = '', extra = '' }) {
  const catLabel = CAT_LABEL[category] || category;
  const regionStr = region ? `지역:${region}, ` : '';

  // 유저 프롬프트 (~180 토큰으로 압축)
  const userPrompt = `${regionStr}카테고리:${catLabel}, 키워드:${keyword}${extra ? ', 추가:'+extra : ''}

아래 구분자 형식으로만 출력 (JSON 없이):
${DELIMITER.TITLE}제목(55자이내,숫자포함)
${DELIMITER.SEO}SEO제목(60자이내)
${DELIMITER.META}메타설명(155자이내,즉답형)
${DELIMITER.KEYWORDS}키워드1,키워드2,키워드3,키워드4,키워드5,키워드6
${DELIMITER.HTML}본문HTML(공백제외 순수텍스트 2500~3000자 필수, h2 5개+, h3 8개+, table 1개+, ul/ol 3개+)
${DELIMITER.END}`;

  const raw = await chatComplete(SYSTEM_PROMPT, userPrompt, {
    model: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini',
    max_tokens: 5000,  // 한글 공백제외 3000자 ≈ 토큰 4500 + HTML태그 500
    temperature: 0.72,
  });

  const parsed = parseDelimited(raw);

  // 파싱 실패 시 폴백
  if (!parsed.title || !parsed.html) {
    throw new Error('콘텐츠 파싱 실패 — 출력 형식 오류: ' + raw.slice(0, 200));
  }

  // 스크립트 태그 제거
  parsed.html = parsed.html.replace(/<script[\s\S]*?<\/script>/gi, '');

  // 1차 검증
  let validation = validateMedicalAd(
    [parsed.title, parsed.seoTitle, parsed.metaDesc, parsed.html].join(' ')
  );

  // 금지어 발견 시 자동 수정 후 재검증
  let autoFixed = false;
  if (!validation.pass) {
    parsed.title    = autoFix(parsed.title);
    parsed.seoTitle = autoFix(parsed.seoTitle);
    parsed.metaDesc = autoFix(parsed.metaDesc);
    parsed.html     = autoFix(parsed.html);
    autoFixed = true;
    validation = validateMedicalAd(
      [parsed.title, parsed.seoTitle, parsed.metaDesc, parsed.html].join(' ')
    );
  }

  return {
    id: 'auto_' + Date.now(),
    cat: category,
    title:     parsed.title,
    seoTitle:  parsed.seoTitle || parsed.title,
    metaDesc:  parsed.metaDesc || '',
    keywords:  parsed.keywords || keyword,
    imagePrompt: IMAGE_PROMPT[category] || IMAGE_PROMPT.geo,
    html:      parsed.html,
    status:    validation.pass ? 'draft' : 'review',
    date:      new Date().toISOString().slice(0, 10),
    views:     0,
    region,
    validation,
    autoFixed,
  };
}

module.exports = { generatePost, CAT_LABEL };
