import Link from "next/link";
import { getAllPosts } from "@/lib/blog";

export const metadata = {
  title: "블로그 — FlowLens",
  description: "히트맵·행동 분석으로 홈페이지 전환율과 매출을 올리는 실무 가이드. FlowLens 활용법과 개선 노하우를 정리합니다.",
};

export default function Blog() {
  const posts = getAllPosts();
  return (
    <div className="blog-wrap">
      <div className="blog-head">
        <Link href="/" className="muted small">← FlowLens 홈</Link>
        <h1>블로그</h1>
        <p className="muted">히트맵·행동 분석으로 <b>전환율과 매출을 올리는 법</b>, 그리고 FlowLens를 실무에서 쓰는 방법을 정리합니다.</p>
      </div>

      <div className="blog-list">
        {posts.length === 0 && <p className="muted">아직 게시된 글이 없습니다.</p>}
        {posts.map((p) => (
          <Link key={p.slug} href={`/blog/${p.slug}`} className="blog-card">
            {p.category && <span className="blog-cat">{p.category}</span>}
            <h2>{p.title}</h2>
            <p className="blog-desc">{p.description}</p>
            <span className="blog-meta">{p.date}{p.author ? ` · ${p.author}` : ""}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
