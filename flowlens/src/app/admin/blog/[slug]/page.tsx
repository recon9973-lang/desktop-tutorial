import { notFound } from "next/navigation";
import { getAdminUser } from "@/lib/admin";
import { getDbPost } from "@/lib/blog";
import { saveBlogPost } from "../actions";
import { BlogForm } from "../BlogForm";

export const dynamic = "force-dynamic";
export const metadata = { title: "글 수정 — FlowLens 운영자" };

export default async function EditBlog({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ new?: string }>;
}) {
  const admin = await getAdminUser();
  if (!admin) notFound();

  const { slug } = await params;
  const { new: isNew } = await searchParams;
  const p = await getDbPost(slug);
  if (!p) notFound();

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="admin-wrap" style={{ maxWidth: 900, margin: "0 auto", padding: "28px 18px 80px" }}>
      <a href="/admin/blog" className="muted small">← 블로그 관리</a>
      <h1 style={{ fontSize: 22, margin: "8px 0 20px" }}>글 수정</h1>
      {isNew && (
        <div className="card card-pad" style={{ marginBottom: 16, background: "var(--accent-soft)", border: "1px solid var(--accent)", color: "var(--text)" }}>
          🤖 <b>AI 초안이 생성되었습니다.</b> 내용을 검토·수정한 뒤, 아래 <b>“지금 발행하기”</b>를 체크하고 저장하면 공개됩니다. 본문은 HTML 형식입니다.
        </div>
      )}
      <div className="card card-pad">
        <BlogForm
          action={saveBlogPost}
          today={today}
          post={{
            slug: p.slug,
            title: p.title,
            seoTitle: p.seoTitle,
            description: p.description,
            keywords: p.keywords,
            category: p.category,
            body: p.body,
            author: p.author,
            date: p.date,
            published: p.published,
          }}
        />
      </div>
    </div>
  );
}
