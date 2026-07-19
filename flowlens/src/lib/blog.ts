import fs from "fs";
import path from "path";
import { marked } from "marked";
import { prisma } from "./db";

// 블로그 콘텐츠 = 파일 글(content/blog/*.md) + 관리자에서 쓴 DB 글(published=true) 병합.
const DIR = path.join(process.cwd(), "content", "blog");

export type PostMeta = {
  slug: string;
  title: string;
  seoTitle?: string;
  description: string;
  keywords: string[];
  category?: string;
  date: string;
  author?: string;
  source?: "file" | "db";
};

// ---- 공통: 마크다운 렌더(외부 링크는 새 탭) ----
function renderMarkdown(body: string): string {
  const noH1 = body.replace(/^\s*#\s+.*(\r?\n|$)/, ""); // 첫 H1 제거(제목 별도 렌더)
  let html = marked.parse(noH1, { async: false }) as string;
  html = html.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a href="$1" target="_blank" rel="noopener noreferrer"');
  return html;
}

// ---- 파일 글 ----
function parseFrontMatter(raw: string): { meta: Record<string, unknown>; body: string } {
  const m = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!m) return { meta: {}, body: raw };
  const meta: Record<string, unknown> = {};
  for (const line of m[1].split(/\r?\n/)) {
    const idx = line.indexOf(":");
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    let val = line.slice(idx + 1).trim();
    if (val.startsWith("[")) {
      try {
        meta[key] = JSON.parse(val);
        continue;
      } catch {
        /* fall through */
      }
    }
    meta[key] = val.replace(/^["']|["']$/g, "");
  }
  return { meta, body: m[2] };
}

function fileSlugs(): string[] {
  if (!fs.existsSync(DIR)) return [];
  return fs.readdirSync(DIR).filter((f) => f.endsWith(".md")).map((f) => f.replace(/\.md$/, ""));
}

function fileMeta(slug: string): PostMeta {
  const raw = fs.readFileSync(path.join(DIR, `${slug}.md`), "utf8");
  const { meta } = parseFrontMatter(raw);
  return { slug, keywords: [], source: "file", ...(meta as object) } as unknown as PostMeta;
}

// ---- DB 글 ----
type DbPost = { slug: string; title: string; seoTitle: string; description: string; keywords: string; category: string; body: string; author: string; date: string };

function dbToMeta(p: DbPost): PostMeta {
  return {
    slug: p.slug,
    title: p.title,
    seoTitle: p.seoTitle || undefined,
    description: p.description,
    keywords: p.keywords ? p.keywords.split(",").map((k) => k.trim()).filter(Boolean) : [],
    category: p.category || undefined,
    date: p.date,
    author: p.author,
    source: "db",
  };
}

function dbJsonld(p: DbPost): string {
  return JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Article",
    headline: p.title,
    description: p.description,
    author: { "@type": "Organization", name: p.author },
    publisher: {
      "@type": "Organization",
      name: "FlowLens",
      url: "https://flow.seokorea.org",
      sameAs: ["https://pf.kakao.com/_jxjxdcxj"],
      contactPoint: { "@type": "ContactPoint", telephone: "+82-1661-4142", email: "venomad@naver.com", contactType: "customer service" },
    },
    datePublished: p.date,
    inLanguage: "ko",
    keywords: p.keywords,
  });
}

// ---- 공개 API (병합) ----
export async function getAllPosts(): Promise<PostMeta[]> {
  const filePosts = fileSlugs().map(fileMeta);
  let dbPosts: PostMeta[] = [];
  try {
    const rows = await prisma.blogPost.findMany({ where: { published: true } });
    dbPosts = rows.map(dbToMeta);
  } catch {
    /* DB 미가용 시 파일 글만 */
  }
  return [...filePosts, ...dbPosts].sort((a, b) => (a.date < b.date ? 1 : -1));
}

export async function getRelatedPosts(slug: string, limit = 3): Promise<PostMeta[]> {
  const all = await getAllPosts();
  const current = all.find((p) => p.slug === slug);
  const others = all.filter((p) => p.slug !== slug);
  if (!current) return others.slice(0, limit);
  const kw = new Set(current.keywords || []);
  return others
    .map((p) => ({ p, score: (p.category && p.category === current.category ? 10 : 0) + (p.keywords || []).filter((k) => kw.has(k)).length }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((x) => x.p);
}

export async function getPost(slug: string): Promise<{ meta: PostMeta; html: string; jsonld: string | null } | null> {
  // DB 글(발행됨) 우선
  try {
    const db = await prisma.blogPost.findFirst({ where: { slug, published: true } });
    if (db) return { meta: dbToMeta(db), html: renderMarkdown(db.body), jsonld: dbJsonld(db) };
  } catch {
    /* ignore */
  }
  // 파일 글
  const file = path.join(DIR, `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  const { meta, body } = parseFrontMatter(raw);
  const html = renderMarkdown(body);
  const ldFile = path.join(DIR, `${slug}.jsonld`);
  const jsonld = fs.existsSync(ldFile) ? fs.readFileSync(ldFile, "utf8") : null;
  return { meta: { slug, keywords: [], source: "file", ...(meta as object) } as unknown as PostMeta, html, jsonld };
}

// ---- 관리자용 (미발행 포함) ----
export async function getAllDbPosts() {
  return prisma.blogPost.findMany({ orderBy: { date: "desc" } });
}
export async function getDbPost(slug: string) {
  return prisma.blogPost.findUnique({ where: { slug } });
}
