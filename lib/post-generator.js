'use strict';

const { chatComplete } = require('./openai-client');
const { validateMedicalAd } = require('./medical-ad-validator');

const CAT_LABEL = {
  geo: 'GEO/AI마케팅', seo: 'SEO마케팅', dental: '치과마케팅',
  skin: '피부과마케팅', oriental: '한의원마케팅', ortho: '정형외과마케팅',
  plastic: '성형외과마케팅', naegwa: '내과마케팅', angwa: '안과마케팅',
  shimui: '의료광고심의', geo_local: '지역마케팅',
};

const SYSTEM_PROMPT = `당신은 대한민국 병원마케팅 전문 에이전시 "베놈(VENOM)"의 공식 블로그 콘텐츠 전략가입니다.
아래 GEO/AEO/SEO 고품질 콘텐츠 지침을 철저히 따라 집필하십시오.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[콘텐츠 구조 필수 원칙]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 역피라미드(즉답형) 구조
   - 첫 문단에 핵심 결론을 완전한 문장으로 즉시 제시
   - 첫 문장: 핵심 키워드 + 주어 + 목적어 + 서술어 완결형
   - 모호한 수식어("빠르게", "많이") 대신 구체적 수치("평균 3개월", "약 30%") 사용
   - 어미는 반드시 "~입니다", "~습니다" 확정형으로 종결

2. Executive Summary 섹션 필수 포함
   - <h2>핵심 요약</h2> 으로 시작하는 200~300자 요약 박스
   - 핵심 인사이트 3가지를 <ul>로 나열

3. Q&A / FAQ 구조 (최소 7개)
   - 실제 고객이 검색할 자연어 질문을 <h3>으로 소제목화
   - 각 질문 아래 직관적이고 수치화된 답변 배치
   - FAQ 섹션: <h2>자주 묻는 질문 (FAQ)</h2> 아래 7개 이상

4. 데이터 구조화
   - 비교 분석 → <table> 사용 (기능/가격/사용성 비교)
   - 프로세스 설명 → <ol> 순번 리스트
   - 강점/특징 → <ul> 리스트

5. E-E-A-T 강화
   - Experience: "베놈이 직접 운영한 사례에서는", "실제 집행 결과 기준으로" 표현 포함
   - Expertise: 전문 용어 정의, 통계 수치, 출처 명시
   - Authoritativeness: 베놈 에이전시 실적/경험 자연스럽게 언급
   - Trustworthiness: 성공 사례뿐 아니라 주의할 점도 균형있게 기술

6. 베놈 CTA 자연스럽게 1~2회 포함
   - "병원마케팅 베놈과 함께하면..." 형태로 자연스럽게
   - 과장 없이 서비스 가치 전달

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[의료광고법 준수 — 절대 위반 금지]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "최고", "최상", "1등", "완치", "100% 효과", "효과 보장", "부작용 없음" 절대 사용 금지
- "탁월한", "놀라운", "기적적인" 등 막연한 과장 형용사 금지
- 특정 병원 비교 광고 금지
- 의료 행위 결과 보장 표현 금지
- "효과적인" 대신 "체계적인", "전략적인", "데이터 기반의" 사용

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[분량 목표]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 한글 기준 2,500자 ~ 3,500자 (HTML 태그 제외 순수 텍스트 기준)
- <h2> 섹션 최소 5개
- <h3> 소제목 최소 7개 (Q&A 포함)
- <table> 최소 1개
- <ol> 또는 <ul> 최소 3개`;

/**
 * @param {object} params
 * @returns {Promise<object>}
 */
async function generatePost({ category, keyword, region = '', extra = '' }) {
  const catLabel = CAT_LABEL[category] || category;
  const regionStr = region ? ` (지역 타겟: ${region})` : '';

  const userPrompt = `
카테고리: ${catLabel}${regionStr}
메인 키워드: ${keyword}
${extra ? `추가 지시사항: ${extra}` : ''}

위 정보로 병원마케팅 블로그 포스트를 작성하세요.
반드시 한글 2,500~3,500자 분량의 고품질 콘텐츠를 작성하세요.

아래 JSON 형식으로만 응답하세요 (코드블록 없이 순수 JSON):
{
  "title": "클릭 유도형 제목 (55자 이내, 숫자/구체적 표현 포함)",
  "seoTitle": "SEO 최적화 제목 (60자 이내, 핵심 키워드 첫 배치)",
  "metaDesc": "메타 설명 (155자 이내, 즉답형으로 핵심 내용 요약)",
  "keywords": "핵심키워드, 연관키워드1, 연관키워드2, 롱테일키워드1, 롱테일키워드2, 지역키워드, LSI키워드",
  "imagePrompt": "DALL-E용 이미지 프롬프트 (영어, 병원마케팅 관련 전문적인 실사 사진 스타일, 50단어 이내)",
  "html": "본문 HTML (2500~3500자, h2/h3/table/ul/ol/blockquote 사용)"
}`.trim();

  const raw = await chatComplete(SYSTEM_PROMPT, userPrompt, {
    model: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini',
    max_tokens: 4000,
    temperature: 0.72,
  });

  let parsed;
  try {
    const cleaned = raw.replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/```\s*$/,'').trim();
    parsed = JSON.parse(cleaned);
  } catch (e) {
    // JSON 파싱 실패 시 raw에서 추출 시도
    const match = raw.match(/\{[\s\S]*\}/);
    if (match) {
      try { parsed = JSON.parse(match[0]); } catch { throw new Error('GPT 응답 JSON 파싱 실패: ' + raw.slice(0, 300)); }
    } else {
      throw new Error('GPT 응답 JSON 파싱 실패: ' + raw.slice(0, 300));
    }
  }

  // 보안: 스크립트 태그 제거
  parsed.html = (parsed.html || '').replace(/<script[\s\S]*?<\/script>/gi, '');

  const validation = validateMedicalAd(
    [parsed.title, parsed.seoTitle, parsed.metaDesc, parsed.html].join(' ')
  );

  return {
    id: 'auto_' + Date.now(),
    cat: category,
    title: parsed.title || keyword + ' 가이드',
    seoTitle: parsed.seoTitle || parsed.title,
    metaDesc: parsed.metaDesc || '',
    keywords: parsed.keywords || keyword,
    imagePrompt: parsed.imagePrompt || '',
    html: parsed.html || '',
    status: validation.pass ? 'draft' : 'review',
    date: new Date().toISOString().slice(0, 10),
    views: 0,
    region,
    validation,
  };
}

module.exports = { generatePost, CAT_LABEL };
