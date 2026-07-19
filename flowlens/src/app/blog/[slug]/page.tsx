import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getPost, getPostSlugs } from "@/lib/blog";

export function generateStaticParams() {
  return getPostSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return { title: "글을 찾을 수 없습니다 — FlowLens" };
  return {
    title: post.meta.seoTitle || `${post.meta.title} — FlowLens`,
    description: post.meta.description,
    keywords: post.meta.keywords,
    openGraph: { title: post.meta.title, description: post.meta.description, type: "article" },
  };
}

export default async function Post({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  return (
    <article className="post">
      {post.jsonld && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: post.jsonld }} />
      )}
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

      <p className="small" style={{ marginTop: 20 }}>
        <Link href="/blog" style={{ color: "var(--accent)" }}>← 다른 글 보기</Link>
      </p>
    </article>
  );
}
