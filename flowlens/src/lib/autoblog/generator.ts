// FlowLens 블로그용 AI 초안 생성기.
// venom post-generator.js의 파이프라인(프롬프트→구분자 파싱→의료광고 검수→콘텐츠 정리)을 재사용하되,
// 주제·톤을 FlowLens(히트맵·전환율 최적화 실무 가이드)로 교체하고,
// 결과는 FlowLens 블로그 CMS(BlogPost) 저장에 맞는 시맨틱 HTML로 반환한다(venom 브랜드 디자인 미적용).

import { chatComplete } from "./openai";
import { validateMedicalAd, autoFix } from "./medical-validator";
import { reviewContent } from "./content-validator";

// FlowLens 블로그 카테고리 (홈페이지 제작·전환율·행동분석 중심)
export const CAT_LABEL: Record<string, string> = {
  heatmap: "히트맵 분석",
  cro: "전환율 최적화",
  landing: "랜딩페이지",
  detail: "상세페이지",
  ecommerce: "쇼핑몰 전환",
  behavior: "소비자 행동패턴",
  website: "홈페이지 제작",
};

// 카테고리별 반드시 깊이 있게 다룰 핵심 (일반론 방지)
const CAT_CORE: Record<string, string> = {
  heatmap: "클릭·스크롤·주목 히트맵 해석, 이탈 지점 찾기, 죽은 클릭(rage click)·오해 클릭, 첫 화면 이탈, 데이터로 개선 우선순위 정하기",
  cro: "전환 퍼널 분석, CTA·카피 개선, A/B 테스트 설계, 마이크로카피, 신뢰요소(후기·보증) 배치, 가설→검증 루프",
  landing: "랜딩페이지 구조(히어로·혜택·증거·CTA), 첫 화면 3초 룰, 메시지 매칭(광고↔랜딩), 폼·CTA 위치, 이탈 원인 진단",
  detail: "상품 상세페이지 구성과 정보 위계, 스크롤 이탈 지점, 후기·상세컷·비교표 배치, 구매 버튼 노출, 모바일 상세페이지 가독성",
  ecommerce: "장바구니·결제 단계 이탈, 상품상세 스크롤·이탈, 결제 폼 최적화, 모바일 전환율, 재방문·장바구니 회복",
  behavior: "소비자 행동패턴 분석, 클릭·스크롤·체류 데이터 해석, 이탈·전환 심리, 사용자 여정(journey) 설계, 정량+정성 결합",
  website: "홈페이지 제작 시 전환을 고려한 설계, 정보구조(IA), 반응형·로딩속도, CTA 설계, 제작 후 행동데이터로 개선하는 루프",
};

// 인용 가능한 "실제" 공신력 출처 (날조 방지: 아래 목록만 인용)
const SRC = [
  { n: "네이버 서치어드바이저", u: "https://searchadvisor.naver.com" },
  { n: "Google 검색 센터", u: "https://developers.google.com/search" },
  { n: "통계청 국가통계포털(KOSIS)", u: "https://kosis.kr" },
  { n: "한국인터넷진흥원(KISA)", u: "https://www.kisa.or.kr" },
  { n: "통계청 온라인쇼핑동향", u: "https://kostat.go.kr" },
];

const SYSTEM_PROMPT = `FlowLens(주식회사 베놈이 만든 개인정보 보호형 웹 행동분석 도구)의 수석 콘텐츠 전략가. 홈페이지·랜딩페이지·상세페이지·쇼핑몰의 전환율을 높이는 실무 "심층 가이드"를 작성한다. 독자는 홈페이지·쇼핑몰 운영자와 마케팅 대행사다.

★FlowLens란★: 방문자의 클릭·스크롤·마우스 이동을 히트맵·스크롤맵·세션으로 시각화해 "방문자가 어디서 이탈하고 무엇을 무시하는지"를 보여주는 도구. 쿠키·개인식별정보 없이 동작하는 개인정보 보호형 분석이다. 실무 방법을 설명할 때 FlowLens(히트맵·스크롤맵·행동분석)를 자연스럽게 1~2회 언급한다.

★분량 최우선★: 본문 HTML 순수텍스트(공백·태그 제외) 반드시 3000~4000자. 짧으면 재작성.

★집필 원칙★
- 즉답형(역피라미드): 첫 문장=핵심 결론+구체 수치, '~입니다' 확정 종결
- 도구 자랑이 아니라 "실무자가 오늘 바로 적용할 방법" 중심
- 구조화: 비교는 표(table), 절차는 순번 리스트(ol), 핵심은 불릿(ul)
- 고유 프레임워크: "3단계 진단법", "5가지 이탈 신호" 등 숫자 부여한 자체 분석틀을 명명해 사용
- 반대 관점 1회 이상: "흔히 A라고 하지만, 실제 행동 데이터는 B입니다" 형태의 통찰
- E-E-A-T: "히트맵으로 실제 분석해 보면", "행동 데이터 기준" 등 경험 표현 + 정량 근거
- 신뢰성: 성공 사례만이 아니라 "잘못 해석했던 사례와 그로부터의 교훈"을 1개 이상 포함
- 수치는 구체적으로 — 단, 없는 통계는 지어내지 말 것

★출처·근거★
- 주요 주장·통계는 "제공된 공신력 출처 목록"의 기관만 근거로 인용하고 본문에 기관명을 명기.
- ★절대 금지★: 제공 목록에 없는 URL·논문·보고서명·구체 통계를 지어내지 말 것. 불확실하면 "일반적으로/추정" 표현 사용.

★본문 구조(반드시 이 순서)★
①즉답형 리드 <p>: 핵심 결론+수치 (약 180자)
②<h2>왜 이 문제가 생기나</h2>: 배경·맥락 (약 450자)
③<h2>핵심 인사이트 — [고유 프레임워크명]</h2> 아래 <h3> 3개로 인사이트 3가지 (각 약 300자)
④<table> 비교표 1개 (4열 이상, 5행 이상)
⑤<h2>단계별 실행 방법</h2>: <ol> 5단계 이상, 각 단계 구체 액션
⑥<h2>실제 분석 사례와 교훈</h2>: 히트맵/행동분석 사례 1개(성공 + 잘못 해석에서 얻은 교훈 포함)
⑦<h2>자주 묻는 질문(FAQ)</h2>: 5개 Q&A. 각 항목은 반드시 <h3>Q. 질문?</h3><p>A. 답변(120자 이상)</p> 형식으로. (이 섹션에만 Q&A 배치 — 구조화 데이터 추출용)
⑧<h2>참고자료</h2>: 본문에서 인용한 공신력 기관을 <ul>로 명기(URL 있으면 <a href=URL target=_blank rel=nofollow>기관명</a>). 최소 2개. 목록 밖 출처 금지.
⑨마지막 <p>: FlowLens 무료 히트맵 데모(주소만 입력, 가입·카드 불필요)로 부드럽게 유도. 전화번호 절대 금지.

★과장광고 금지(광고 신뢰성)★: 최고·최상·100%효과·효과보장·탁월한·기적·놀라운 등 과장 표현 금지
대체표현: 효과적→체계적, 탁월→전문적, 우수→데이터기반

★연락처 규칙★: 전화번호(010·02·1588 등)를 절대 만들어 쓰지 말 것. 유도는 "FlowLens 무료 데모" 문구로만.`;

const DELIMS = {
  TITLE: "<<<TITLE>>>",
  SEO: "<<<SEO>>>",
  META: "<<<META>>>",
  KEYWORDS: "<<<KEYWORDS>>>",
  HTML: "<<<HTML>>>",
  END: "<<<END>>>",
} as const;

function parseDelimited(raw: string) {
  const keys = Object.keys(DELIMS) as (keyof typeof DELIMS)[];
  const get = (key: keyof typeof DELIMS): string => {
    const marker = DELIMS[key];
    const start = raw.indexOf(marker);
    if (start === -1) return "";
    let end = raw.length;
    for (const k of keys) {
      if (DELIMS[k] === marker) continue;
      const idx = raw.indexOf(DELIMS[k], start + marker.length);
      if (idx > -1 && idx < end) end = idx;
    }
    return raw.slice(start + marker.length, end).trim();
  };
  return {
    title: get("TITLE"),
    seoTitle: get("SEO"),
    metaDesc: get("META"),
    keywords: get("KEYWORDS"),
    html: get("HTML"),
  };
}

export type GeneratedDraft = {
  title: string;
  seoTitle: string;
  metaDesc: string;
  keywords: string;
  category: string;
  categoryLabel: string;
  bodyHtml: string;
  validation: { pass: boolean; forbidden: string[]; risky: string[] };
  contentErrors: { type: string; severity: string; msg: string }[];
  hasBlockingErrors: boolean;
  publishable: boolean;
  autoFixed: boolean;
  tokenUsage: { totalTokens: number; model: string };
};

export async function generateFlowLensPost({
  category,
  keyword,
  region = "",
  extra = "",
}: {
  category: string;
  keyword: string;
  region?: string;
  extra?: string;
}): Promise<GeneratedDraft> {
  const catLabel = CAT_LABEL[category] || category;
  const catCore = CAT_CORE[category] || "";
  const srcList = SRC.map((s) => `${s.n}|${s.u}`).join(", ");

  const userPrompt = `카테고리:${catLabel}, 키워드:${keyword}${region ? `, 지역:${region}` : ""}${extra ? `, 추가:${extra}` : ""}
${catCore ? `이 카테고리에서 반드시 깊이 다룰 핵심: ${catCore}` : ""}
${region ? `'${region}' 지역 맥락을 구체적으로 반영할 것.` : ""}
인용 가능한 공신력 출처(이 목록만 사용, '기관명|URL' 형식): ${srcList}

아래 구분자 형식으로만 출력 (JSON 없이):
${DELIMS.TITLE}제목(55자이내,숫자포함)
${DELIMS.SEO}SEO제목(60자이내)
${DELIMS.META}메타설명(155자이내,즉답형)
${DELIMS.KEYWORDS}키워드1,키워드2,키워드3,키워드4,키워드5,키워드6
${DELIMS.HTML}본문HTML(공백제외 순수텍스트 3000~4000자 필수, 지정 9단 구조 준수, h2 6개+, h3 3개+, table 1개+, ol 1개+, ul 2개+)
${DELIMS.END}`;

  const { text: raw, usage } = await chatComplete(SYSTEM_PROMPT, userPrompt, {
    model: process.env.OPENAI_TEXT_MODEL || "gpt-4o-mini",
    max_tokens: 8000,
    temperature: 0.72,
  });

  const parsed = parseDelimited(raw);
  if (!parsed.title || !parsed.html) {
    throw new Error("콘텐츠 파싱 실패 — 출력 형식 오류: " + raw.slice(0, 200));
  }

  // 스크립트 태그 제거 + 콘텐츠 정리
  parsed.html = parsed.html.replace(/<script[\s\S]*?<\/script>/gi, "");
  const contentReview = reviewContent(parsed.html);
  parsed.html = contentReview.cleaned;

  // 의료광고법 검수 → 실패 시 자동수정 후 재검증
  let validation = validateMedicalAd([parsed.title, parsed.seoTitle, parsed.metaDesc, parsed.html].join(" "));
  let autoFixed = false;
  if (!validation.pass) {
    parsed.title = autoFix(parsed.title);
    parsed.seoTitle = autoFix(parsed.seoTitle);
    parsed.metaDesc = autoFix(parsed.metaDesc);
    parsed.html = autoFix(parsed.html);
    autoFixed = true;
    validation = validateMedicalAd([parsed.title, parsed.seoTitle, parsed.metaDesc, parsed.html].join(" "));
  }

  const publishable = validation.pass && !contentReview.hasBlockingErrors;

  return {
    title: parsed.title,
    seoTitle: parsed.seoTitle || parsed.title,
    metaDesc: parsed.metaDesc || "",
    keywords: parsed.keywords || keyword,
    category,
    categoryLabel: catLabel,
    bodyHtml: parsed.html,
    validation,
    contentErrors: contentReview.errors,
    hasBlockingErrors: contentReview.hasBlockingErrors,
    publishable,
    autoFixed,
    tokenUsage: { totalTokens: usage.total_tokens, model: process.env.OPENAI_TEXT_MODEL || "gpt-4o-mini" },
  };
}
