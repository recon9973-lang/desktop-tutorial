'use strict';

const { chatComplete } = require('./openai-client');
const { validateMedicalAd, autoFix } = require('./medical-ad-validator');
const { reviewContent } = require('./content-validator');
const { designPost } = require('./post-designer');

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

// ── 카테고리별 반드시 다뤄야 할 핵심 주제 (일반론 방지) ──
const CAT_CORE = {
  geo:      'GEO/AEO 개념, ChatGPT·Perplexity가 병원을 추천하는 원리, Schema.org 마크업, 엔티티 구축, 구글 AI Overviews 대응',
  seo:      '네이버 C-Rank·D.I.A+ 알고리즘, 구글 E-E-A-T, Core Web Vitals, 키워드 전략, 백링크/내부링크',
  dental:   '임플란트·교정·심미 등 고객단가 시술 키워드, 네이버 플레이스 최적화, 의료광고법 준수 후기 운영, 지역 SEO',
  skin:     '보톡스·필러·레이저 키워드, 비포·애프터 금지 등 의료광고 규제 대응, SNS·정보형 콘텐츠 전략',
  oriental: '첩약·다이어트·추나·통증 키워드, 비급여 포지셔닝, 계절별 키워드, 네이버 플레이스',
  ortho:    '척추·관절·도수치료·체외충격파 키워드, 비급여 단가 전략, 재활 콘텐츠, 지역 상위노출',
  plastic:  '쌍꺼풀·코·안면윤곽 키워드, 의료광고 사전심의, 원장 전문성 브랜딩, 회복·절차 정보 콘텐츠',
  naegwa:   '건강검진·내시경·만성질환(당뇨·고혈압) 키워드, 재진율 관리, 카카오 채널 재방문 유도',
  angwa:    '라식·라섹·백내장·노안 키워드, 지역+시술 조합 SEO, 비교 콘텐츠(AEO), 유튜브',
  shimui:   '의료광고 사전심의 대상 매체, 금지 표현, 심의 절차, 합법 콘텐츠 기준, 위반 시 과태료',
  geo_local:'지역 검색 패턴 분석, 네이버 플레이스·지도 최적화, 지역+진료과 키워드, 로컬 백링크',
};

// ── 인용 가능한 "실제" 공신력 출처 (날조 방지: GPT는 아래 목록만 인용·링크) ──
// 정부·공공기관 (검증된 안정 도메인)
const SRC_GOV = [
  { n: '보건복지부', u: 'https://www.mohw.go.kr' },
  { n: '식품의약품안전처', u: 'https://www.mfds.go.kr' },
  { n: '건강보험심사평가원(심평원)', u: 'https://www.hira.or.kr' },
  { n: '국민건강보험공단', u: 'https://www.nhis.or.kr' },
  { n: '통계청 국가통계포털(KOSIS)', u: 'https://kosis.kr' },
];
// 검색·AI 공식 문서 (GEO/SEO 카테고리)
const SRC_SEARCH = [
  { n: '네이버 서치어드바이저', u: 'https://searchadvisor.naver.com' },
  { n: 'Google 검색 센터', u: 'https://developers.google.com/search' },
];
// 진료과별 학회·협회 (기관명만 인용 — URL은 변동 가능성 있어 링크 생략, 명칭으로 출처 명기)
const SRC_ASSOC = {
  dental:   ['대한치과의사협회'],
  skin:     ['대한피부과학회', '대한피부과의사회'],
  ortho:    ['대한정형외과학회'],
  oriental: ['대한한의사협회'],
  plastic:  ['대한성형외과학회', '대한미용성형외과학회'],
  naegwa:   ['대한내과학회'],
  angwa:    ['대한안과학회'],
  shimui:   ['의료광고 자율심의기구', '대한의사협회'],
};

// 카테고리별 인용 가능 출처 목록 생성
function sourcesFor(category) {
  const list = SRC_GOV.slice();
  if (/geo|seo/.test(category)) SRC_SEARCH.forEach(s => list.push(s));
  (SRC_ASSOC[category] || []).forEach(n => list.push({ n, u: '' }));
  return list;
}

// ── 시스템 프롬프트 (AI 콘텐츠 제작 지침서 기반) ──
const SYSTEM_PROMPT = `병원마케팅 에이전시 베놈(VENOM)의 수석 콘텐츠 전략가. GEO/AEO/SEO 기반 고품질 "심층 분석" 콘텐츠 작성.

★분량 최우선★: 본문 HTML 순수텍스트(공백·태그 제외) 반드시 3500~4500자. 짧으면 재작성.

★집필 원칙★
- 즉답형(역피라미드): 첫 문장=핵심 결론+구체 수치, '~입니다' 확정 종결
- 의미·맥락 중심: 키워드 기계적 반복 금지, 검색 의도에 맞춘 스토리 설계
- 구조화: 비교는 표(table), 절차는 순번 리스트(ol), 핵심은 불릿(ul)
- 고유 프레임워크: "3단계 모델", "5가지 원칙" 등 숫자 부여한 자체 분석틀을 명명해 사용
- 반대 관점 1회 이상: "흔히 A라고 하지만, 실제 집행 데이터는 B입니다" 형태의 통찰
- E-E-A-T: "베놈이 직접 집행한 사례", "실제 광고 집행 결과 기준" 등 경험 표현 + 정량 근거
- 신뢰성: 성공담만이 아니라 "실패 사례와 그를 통한 개선 교훈"을 1개 이상 포함
- 모든 수치는 구체적으로: 평균 3개월, 약 30%, 월 8,500건 검색 등

★출처·근거 (E-E-A-T 신뢰성)★
- 주요 주장·통계·규정은 "제공된 공신력 출처 목록"의 기관(정부·학회·검색 공식문서)을 근거로 인용하고 본문에 기관명을 명기(예: "보건복지부 자료 기준", "대한치과의사협회에 따르면", "네이버 서치어드바이저 공식 문서").
- ★절대 금지★: 제공 목록에 없는 URL·논문 제목·보고서명·구체 통계 수치를 지어내지 말 것. 근거가 불확실하면 단정 대신 "일반적으로/추정" 같은 신중한 표현 사용.
- 본문 중 최소 2~3회 공신력 기관을 출처로 자연스럽게 언급.

★본문 구조(반드시 이 순서)★
①즉답형 리드 <p>: 핵심 결론+수치 (약 200자)
②<h2>현황과 배경</h2>: 시장·지역 맥락 분석 (약 500자, 수치 포함, 공신력 출처 1회 이상 인용)
③<h2>핵심 인사이트 — [고유 프레임워크명]</h2> 아래 <h3> 3개로 인사이트 3가지 (각 약 300자)
④<table> 비교표 1개 (4열 이상, 5행 이상: 채널/전략/비용/기대효과 등)
⑤<h2>단계별 실행 방안</h2>: <ol> 5단계 이상, 각 단계 구체 액션+수치
⑥<h2>실제 사례와 교훈</h2>: 베놈 집행 사례 1개(성공 + 실패에서 얻은 교훈 포함)
⑦<h2>예상 성과와 ROI</h2>: 구체 수치 지표 (약 200자)
⑧<h2>자주 묻는 질문(FAQ)</h2>: 5~7개 Q&A, 각 답변 150자 이상 (이 섹션에만 Q&A 배치)
⑨<h2>참고자료</h2>: 본문에서 인용한 공신력 기관을 <ul>로 명기(제공된 URL이 있으면 <a href=URL target=_blank rel=nofollow>기관명</a> 링크, URL 없으면 기관명만). 최소 3개. 목록 밖 출처 금지.
⑩베놈 CTA 1회(구체 연락처 유도)

★의료광고법 절대금지★: 최고·최상·완치·100%효과·효과보장·부작용없음·탁월한·기적·놀라운
대체표현: 효과적→체계적, 탁월→전문적, 우수→데이터기반

★연락처 규칙★: 전화번호·휴대폰번호(010·02·1588 등)를 절대 만들어 쓰지 말 것(전부 가짜임). 연락 유도는 오직 "카카오 상담" 문구로만. CTA에 전화번호 표기 금지.`;

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
  const catCore = CAT_CORE[category] || '';
  const srcList = sourcesFor(category)
    .map(s => s.u ? `${s.n}|${s.u}` : s.n).join(', ');

  // 유저 프롬프트
  const userPrompt = `${regionStr}카테고리:${catLabel}, 키워드:${keyword}${extra ? ', 추가:'+extra : ''}
${catCore ? `이 카테고리에서 반드시 깊이 있게 다룰 핵심 내용: ${catCore}` : ''}
${region ? `'${region}' 지역 맥락(상권·검색 패턴·지역 키워드)을 구체적으로 반영할 것.` : ''}
인용 가능한 공신력 출처(이 목록만 사용, '기관명|URL' 형식 — URL 없으면 기관명만 인용): ${srcList}

아래 구분자 형식으로만 출력 (JSON 없이):
${DELIMITER.TITLE}제목(55자이내,숫자포함)
${DELIMITER.SEO}SEO제목(60자이내)
${DELIMITER.META}메타설명(155자이내,즉답형)
${DELIMITER.KEYWORDS}키워드1,키워드2,키워드3,키워드4,키워드5,키워드6
${DELIMITER.HTML}본문HTML(공백제외 순수텍스트 3500~4500자 필수, 시스템 지정 10단 구조(참고자료 포함) 준수, h2 7개+, h3 3개+, table 1개+, ol 1개+, ul 2개+)
${DELIMITER.END}`;

  const { text: raw, usage: tokenUsage } = await chatComplete(SYSTEM_PROMPT, userPrompt, {
    model: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini',
    max_tokens: 9000,  // 한글 공백제외 4500자 ≈ 토큰 6800 + HTML태그/구조 여유
    temperature: 0.72,
  });

  const parsed = parseDelimited(raw);

  // 파싱 실패 시 폴백
  if (!parsed.title || !parsed.html) {
    throw new Error('콘텐츠 파싱 실패 — 출력 형식 오류: ' + raw.slice(0, 200));
  }

  // 스크립트 태그 제거
  parsed.html = parsed.html.replace(/<script[\s\S]*?<\/script>/gi, '');

  // 콘텐츠 오류 검수 + 자동 정리 (깨진 문자·구분자 잔존·빈 태그 등 발행 전 수정)
  const contentReview = reviewContent(parsed.html);
  parsed.html = contentReview.cleaned;

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

  // 디자인 빌더: GPT 평문 HTML → 베놈 브랜드 디자인(인라인 스타일) 적용
  // (검증/검수는 정리된 평문 기준으로 이미 완료 — 디자인은 텍스트를 바꾸지 않음)
  parsed.html = designPost(parsed.html);

  const postId  = 'auto_' + Date.now();
  const isoDate = new Date().toISOString();
  const articleSchema = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'Article',
    'headline': parsed.seoTitle || parsed.title,
    'description': parsed.metaDesc || '',
    'keywords': parsed.keywords || keyword,
    'datePublished': isoDate,
    'dateModified': isoDate,
    'author': {
      '@type': 'Organization',
      'name': '병원마케팅 베놈',
      'url': 'https://desktop-tutorial-chi-peach.vercel.app/'
    },
    'publisher': {
      '@type': 'Organization',
      'name': '병원마케팅 베놈',
      'logo': { '@type': 'ImageObject', 'url': 'https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/logo_venomad_hospital%20marketing.png' }
    },
    'mainEntityOfPage': { '@type': 'WebPage', '@id': `https://desktop-tutorial-chi-peach.vercel.app/#blog-${postId}` },
  });

  const htmlWithSchema = `<script type="application/ld+json">${articleSchema}</script>\n` + parsed.html;

  // 발행 차단 여부: 의료광고 검증 통과 + 콘텐츠 오류 없음일 때만 발행 가능
  const publishable = validation.pass && !contentReview.hasBlockingErrors;

  return {
    id: postId,
    cat: category,
    title:     parsed.title,
    seoTitle:  parsed.seoTitle || parsed.title,
    metaDesc:  parsed.metaDesc || '',
    keywords:  parsed.keywords || keyword,
    imagePrompt: IMAGE_PROMPT[category] || IMAGE_PROMPT.geo,
    html:      htmlWithSchema,
    status:    publishable ? 'draft' : 'review',
    date:      isoDate.slice(0, 10),
    createdAt: isoDate,
    views:     0,
    region,
    validation,
    contentErrors: contentReview.errors,
    hasBlockingErrors: contentReview.hasBlockingErrors,
    publishable,
    autoFixed,
    tokenUsage: {
      promptTokens: tokenUsage.prompt_tokens,
      completionTokens: tokenUsage.completion_tokens,
      totalTokens: tokenUsage.total_tokens,
      model: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini',
    },
  };
}

module.exports = { generatePost, CAT_LABEL };
