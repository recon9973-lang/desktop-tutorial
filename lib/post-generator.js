'use strict';

const { chatComplete } = require('./openai-client');
const { validateMedicalAd } = require('./medical-ad-validator');

const CAT_LABEL = {
  geo: 'GEO/AI마케팅',
  seo: 'SEO마케팅',
  dental: '치과마케팅',
  skin: '피부과마케팅',
  oriental: '한의원마케팅',
  ortho: '정형외과마케팅',
  plastic: '성형외과마케팅',
  naegwa: '내과마케팅',
  angwa: '안과마케팅',
  shimui: '의료광고심의',
  geo_local: '지역마케팅',
};

const SYSTEM_PROMPT = `당신은 대한민국 병원 마케팅 전문 에이전시 "베놈(VENOM)"의 공식 블로그 콘텐츠 라이터입니다.

[집필 원칙 — GEO/AEO/SEO 고품질 기준]
1. 역피라미드 구조: 핵심 결론을 첫 문단에 즉답형으로 배치
2. Q&A/FAQ 구조: 실제 고객 질문을 H3 소제목으로 활용 (최소 5개)
3. 구체적 수치와 데이터 사용 ("약 30%", "평균 3개월" 형태)
4. 비교표·목록 활용한 구조화 데이터
5. E-E-A-T 강화: 직접 경험·전문성·신뢰성 표현
6. 병원마케팅 전문 용어 정확히 사용
7. 베놈의 서비스와 자연스럽게 연계 (CTA 포함)

[의료법 준수 원칙 — 절대 위반 금지]
- "최고","최상","1등","완치","100% 효과","효과 보장","부작용 없음" 등 과장 표현 사용 금지
- 특정 병원 비교 광고 금지
- 환자 유인 목적 할인·이벤트 직접 언급 금지
- 의료 행위 결과 보장 표현 금지
- "탁월한","기적적인","놀라운" 등 막연한 긍정 형용사 지양

[출력 형식 — HTML]
- 반드시 HTML 형식으로 작성
- <h2>, <h3>, <p>, <ul>/<ol>, <table>, <blockquote> 태그 사용
- 인라인 스타일 없이 시맨틱 태그만 사용
- 최소 1,500자 이상 한국어 본문`;

/**
 * 블로그 포스트 생성
 * @param {object} params
 * @param {string} params.category   - 카테고리 키 (geo, dental 등)
 * @param {string} params.keyword    - 메인 키워드
 * @param {string} params.region     - 지역 키워드 (선택)
 * @param {string} params.extra      - 추가 지시사항 (선택)
 * @returns {Promise<{title,seoTitle,metaDesc,keywords,html,cat,validation}>}
 */
async function generatePost({ category, keyword, region = '', extra = '' }) {
  const catLabel = CAT_LABEL[category] || category;
  const regionStr = region ? ` (지역: ${region})` : '';

  const userPrompt = `
카테고리: ${catLabel}${regionStr}
메인 키워드: ${keyword}
${extra ? `추가 지시사항: ${extra}` : ''}

위 정보로 병원마케팅 블로그 포스트를 작성해주세요.

아래 JSON 형식으로만 응답하세요 (코드블록 없이):
{
  "title": "포스트 제목 (클릭 유도형, 55자 이내)",
  "seoTitle": "SEO 최적화 제목 (60자 이내, 핵심 키워드 포함)",
  "metaDesc": "메타 설명 (155자 이내, 핵심 내용 요약)",
  "keywords": "쉼표로 구분된 키워드 5-7개",
  "html": "본문 HTML (최소 1500자)"
}`.trim();

  const raw = await chatComplete(SYSTEM_PROMPT, userPrompt, { max_tokens: 3000 });

  let parsed;
  try {
    // JSON 블록이 있으면 제거
    const cleaned = raw.replace(/^```json\s*/i, '').replace(/```\s*$/,'').trim();
    parsed = JSON.parse(cleaned);
  } catch (e) {
    throw new Error('GPT 응답 JSON 파싱 실패: ' + raw.slice(0, 200));
  }

  // HTML 스크립트 태그 제거 (보안)
  parsed.html = (parsed.html || '').replace(/<script[\s\S]*?<\/script>/gi, '');

  const validation = validateMedicalAd(
    [parsed.title, parsed.seoTitle, parsed.metaDesc, parsed.html].join(' ')
  );

  return {
    id: 'auto_' + Date.now(),
    cat: category,
    title: parsed.title || keyword + ' 병원마케팅 가이드',
    seoTitle: parsed.seoTitle || parsed.title,
    metaDesc: parsed.metaDesc || '',
    keywords: parsed.keywords || keyword,
    html: parsed.html || '',
    status: validation.pass ? 'draft' : 'review',
    date: new Date().toISOString().slice(0, 10),
    views: 0,
    region,
    validation,
  };
}

module.exports = { generatePost, CAT_LABEL };
