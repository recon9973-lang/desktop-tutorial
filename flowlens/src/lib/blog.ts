import fs from "fs";
import path from "path";
import { marked } from "marked";

// 블로그 콘텐츠는 content/blog/*.md (+ 선택적 동명 .jsonld 구조화데이터).
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
};

// 간단한 프론트매터 파서(자체 작성 콘텐츠 형식에 맞춤). key: value + 배열(JSON) 지원.
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
        /* fall through to string */
      }
    }
    meta[key] = val.replace(/^["']|["']$/g, "");
  }
  return { meta, body: m[2] };
}

export function getPostSlugs(): string[] {
  if (!fs.existsSync(DIR)) return [];
  return fs
    .readdirSync(DIR)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""));
}

export function getAllPosts(): PostMeta[] {
  return getPostSlugs()
    .map((slug) => {
      const raw = fs.readFileSync(path.join(DIR, `${slug}.md`), "utf8");
      const { meta } = parseFrontMatter(raw);
      return { slug, keywords: [], ...(meta as object) } as unknown as PostMeta;
    })
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

export function getPost(slug: string): { meta: PostMeta; html: string; jsonld: string | null } | null {
  const file = path.join(DIR, `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  const { meta, body } = parseFrontMatter(raw);
  // 본문의 첫 H1(제목)은 페이지에서 별도 렌더하므로 제거해 중복을 막는다.
  const bodyNoH1 = body.replace(/^\s*#\s+.*(\r?\n|$)/, "");
  const html = marked.parse(bodyNoH1, { async: false }) as string;
  const ldFile = path.join(DIR, `${slug}.jsonld`);
  const jsonld = fs.existsSync(ldFile) ? fs.readFileSync(ldFile, "utf8") : null;
  return { meta: { slug, keywords: [], ...(meta as object) } as unknown as PostMeta, html, jsonld };
}
