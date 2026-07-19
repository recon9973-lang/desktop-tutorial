import type { MetadataRoute } from "next";

const BASE = "https://flow.seokorea.org";

// 검색엔진 크롤러 정책. 공개 콘텐츠는 허용하고, 로그인·관리·API 등 비공개 영역은 차단.
// GEO(생성형 AI 최적화): GPTBot·ClaudeBot·PerplexityBot·Google-Extended 등 AI 크롤러가
// 공개 콘텐츠를 답변 소스로 수집하도록 명시 허용(비공개 영역은 동일하게 차단).
const PRIVATE = ["/dashboard", "/admin", "/settings", "/sites", "/api/", "/login", "/signup", "/share"];
const AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-Web", "anthropic-ai", "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot"];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: PRIVATE },
      ...AI_BOTS.map((bot) => ({ userAgent: bot, allow: "/", disallow: PRIVATE })),
    ],
    sitemap: `${BASE}/sitemap.xml`,
    host: BASE,
  };
}
