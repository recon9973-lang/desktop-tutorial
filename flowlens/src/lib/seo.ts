// SEO/GEO/AEO 구조화 데이터(JSON-LD) 생성기.
// venom seo-geo-aeo.php의 GEO/AEO 스키마 전략(Organization·Article+Speakable·FAQPage·BreadcrumbList)을
// FlowLens(홈페이지·전환율·행동분석)에 맞춰 이식.

import type { PostMeta } from "./blog";

const BASE = "https://flow.seokorea.org";
const ORG_ID = `${BASE}/#organization`;

// ── 사이트 공통: Organization + WebSite (모든 페이지 <head>에 1회) ──
export function siteJsonLd(): string {
  return JSON.stringify([
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      "@id": ORG_ID,
      name: "FlowLens",
      legalName: "주식회사 베놈",
      alternateName: ["플로우렌즈", "FlowLens 히트맵"],
      description:
        "개인정보 보호형 웹 행동분석(히트맵·스크롤맵·세션 리플레이)으로 홈페이지·쇼핑몰의 전환율을 높이는 SaaS. 주식회사 베놈 운영.",
      url: BASE,
      logo: `${BASE}/icon.svg`,
      sameAs: ["https://pf.kakao.com/_jxjxdcxj"],
      contactPoint: {
        "@type": "ContactPoint",
        telephone: "+82-1661-4142",
        email: "venomad@naver.com",
        contactType: "customer service",
        areaServed: "KR",
        availableLanguage: ["Korean"],
      },
      knowsAbout: [
        "히트맵",
        "전환율 최적화",
        "CRO",
        "웹 행동분석",
        "랜딩페이지",
        "상세페이지",
        "쇼핑몰 전환",
        "소비자 행동패턴",
        "홈페이지 제작",
      ],
    },
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "@id": `${BASE}/#website`,
      name: "FlowLens",
      url: BASE,
      inLanguage: "ko-KR",
      publisher: { "@id": ORG_ID },
    },
  ]);
}

// ── FAQ 추출: 렌더된 본문 HTML에서 '자주 묻는 질문' 섹션의 Q/A 쌍 파싱 ──
// AI 생성 글은 <h3>Q. 질문</h3><p>A. 답변</p> 형식으로 나오도록 유도(generator).
function stripTags(s: string): string {
  return s
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

export function extractFaqs(html: string): { q: string; a: string }[] {
  if (!html) return [];
  const startRe = /<h2[^>]*>[^<]*자주\s*묻는\s*질문[\s\S]*?<\/h2>/i;
  const startM = html.match(startRe);
  if (!startM || startM.index === undefined) return [];
  let region = html.slice(startM.index + startM[0].length);
  // 다음 <h2>(예: 참고자료) 전까지로 제한
  const nextH2 = region.search(/<h2\b/i);
  if (nextH2 >= 0) region = region.slice(0, nextH2);

  const items: { q: string; a: string }[] = [];
  // 형식1: <h3>Q. 질문</h3><p>A. 답변</p>
  const re1 = /<h3[^>]*>([\s\S]*?)<\/h3>\s*<p[^>]*>([\s\S]*?)<\/p>/gi;
  let m: RegExpExecArray | null;
  while ((m = re1.exec(region)) !== null) {
    const q = stripTags(m[1]).replace(/^Q\s*[.).:]?\s*/i, "").trim();
    const a = stripTags(m[2]).replace(/^A\s*[.).:]?\s*/i, "").trim();
    if (q && a && q.length <= 200) items.push({ q, a });
  }
  // 형식2(폴백): <p><strong>Q. 질문</strong> 답변</p> 또는 <p>Q. 질문</p><p>A. 답변</p>
  if (items.length === 0) {
    const re2 = /<p[^>]*>\s*(?:<strong>)?\s*Q\s*[.).:]?\s*([\s\S]*?)(?:<\/strong>)?\s*<\/p>\s*<p[^>]*>\s*(?:A\s*[.).:]?\s*)?([\s\S]*?)<\/p>/gi;
    while ((m = re2.exec(region)) !== null) {
      const q = stripTags(m[1]).trim();
      const a = stripTags(m[2]).trim();
      if (q && a && q.length <= 200) items.push({ q, a });
    }
  }
  return items.slice(0, 10);
}

// ── 블로그 글: Article(+Speakable) + BreadcrumbList + FAQPage ──
export function postJsonLd(meta: PostMeta, renderedHtml: string): string {
  const url = `${BASE}/blog/${meta.slug}`;
  const schemas: Record<string, unknown>[] = [];

  schemas.push({
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": `${url}#article`,
    headline: meta.seoTitle || meta.title,
    description: meta.description,
    inLanguage: "ko-KR",
    datePublished: meta.date,
    dateModified: meta.date,
    author: { "@id": ORG_ID },
    publisher: { "@id": ORG_ID },
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    keywords: (meta.keywords || []).join(", "),
    // AEO — 음성/AI 답변엔진이 읽을 핵심 영역
    speakable: {
      "@type": "SpeakableSpecification",
      cssSelector: [".post-head h1", ".post-body h2"],
    },
  });

  schemas.push({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: BASE + "/" },
      { "@type": "ListItem", position: 2, name: "블로그", item: `${BASE}/blog` },
      { "@type": "ListItem", position: 3, name: meta.title, item: url },
    ],
  });

  const faqs = extractFaqs(renderedHtml);
  if (faqs.length >= 2) {
    schemas.push({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqs.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    });
  }

  return JSON.stringify(schemas);
}
