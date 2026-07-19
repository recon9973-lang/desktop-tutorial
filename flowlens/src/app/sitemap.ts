import type { MetadataRoute } from "next";
import { getAllPosts } from "@/lib/blog";

const BASE = "https://flow.seokorea.org";

// 검색엔진 수집용 사이트맵. 공개 페이지 + 블로그 글 전체를 자동 포함한다.
export default function sitemap(): MetadataRoute.Sitemap {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${BASE}/blog`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE}/privacy`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${BASE}/terms`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${BASE}/dpa`, changeFrequency: "yearly", priority: 0.3 },
  ];

  const posts: MetadataRoute.Sitemap = getAllPosts().map((p) => ({
    url: `${BASE}/blog/${p.slug}`,
    lastModified: p.date ? new Date(p.date) : undefined,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  return [...staticPages, ...posts];
}
