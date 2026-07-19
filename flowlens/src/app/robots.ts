import type { MetadataRoute } from "next";

const BASE = "https://flow.seokorea.org";

// 검색엔진 크롤러 정책. 공개 콘텐츠는 허용하고, 로그인·관리·API 등 비공개 영역은 차단.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/admin", "/settings", "/sites", "/api/", "/login", "/signup", "/share"],
    },
    sitemap: `${BASE}/sitemap.xml`,
    host: BASE,
  };
}
