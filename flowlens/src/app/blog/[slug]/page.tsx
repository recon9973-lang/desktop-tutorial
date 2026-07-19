import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getPost, getRelatedPosts } from "@/lib/blog";
import { postJsonLd } from "@/lib/seo";

// DB에서 쓴 글도 즉시 반영되도록 동적 렌더 (파일 글 + DB 글 병합)
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return { title: "글을 찾을 수 없습니다 — FlowLens" };
  return {
    title: post.meta.seoTitle || post.meta.title,
    description: post.meta.description,
    keywords: post.meta.keywords,
    alternates: { canonical: `/blog/${slug}` },
    openGraph: {
      title: post.meta.title,
      description: post.meta.description,
      type: "article",
      url: `/blog/${slug}`,
    },
  };
}

export default async function Post({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) notFound();
  const related = await getRelatedPosts(slug, 3);
  // Article + BreadcrumbList + FAQPage(있으면) 구조화 데이터 — 렌더된 본문에서 FAQ 자동 추출
  const jsonld = postJsonLd(post.meta, post.html);

  return (
    <article className="post">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonld }} />

      <div className="post-head">
        <Link href="/blog" className="muted small">← 블로그</Link>
        {post.meta.category && <span className="blog-cat">{post.meta.category}</span>}
        <h1>{post.meta.title}</h1>
        <p className="post-meta muted small">{post.meta.date}{post.meta.author ? ` · ${post.meta.author}` : ""}</p>
      </div>

      <div className="post-body" dangerouslySetInnerHTML={{ __html: post.html }} />

      <div className="post-cta">
        <div>
          <p className="big">내 홈페이지에선 방문자가 어디서 떠날까요?</p>
          <span className="muted small">주소만 넣으면 히트맵 데모 — 가입·카드 필요 없음</span>
        </div>
        <Link href="/" className="btn primary">무료로 진단하기</Link>
      </div>

      {related.length > 0 && (
        <div className="post-related">
          <h2>관련 글</h2>
          <div className="post-related-list">
            {related.map((r) => (
              <Link key={r.slug} href={`/blog/${r.slug}`} className="post-related-card">
                {r.category && <span className="blog-cat">{r.category}</span>}
                <span className="rt">{r.title}</span>
                <span className="rd">{r.description}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <p className="small" style={{ marginTop: 20 }}>
        <Link href="/blog" style={{ color: "var(--accent)" }}>← 다른 글 보기</Link>
      </p>
    </article>
  );
}
