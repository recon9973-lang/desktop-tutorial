import { notFound } from "next/navigation";
import { getAdminUser } from "@/lib/admin";
import { getAllDbPosts } from "@/lib/blog";
import { saveBlogPost, toggleBlogPublish, deleteBlogPost } from "./actions";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const metadata = { title: "블로그 관리 — FlowLens 운영자" };

// 파일(코드) 기반 글 목록 — 읽기 전용 표시용
function fileSlugs(): string[] {
  const dir = path.join(process.cwd(), "content", "blog");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".md")).map((f) => f.replace(/\.md$/, ""));
}

export default async function AdminBlog() {
  const admin = await getAdminUser();
  if (!admin) notFound();

  const dbPosts = await getAllDbPosts();
  const files = fileSlugs();
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="admin-wrap" style={{ maxWidth: 900, margin: "0 auto", padding: "28px 18px 80px" }}>
      <a href="/admin" className="muted small">← 운영자 홈</a>
      <h1 style={{ fontSize: 22, margin: "8px 0 4px" }}>블로그 관리</h1>
      <p className="muted small" style={{ margin: "0 0 24px" }}>
        여기서 블로그 글을 직접 쓰고 발행할 수 있습니다. <b>발행</b>을 켜면 즉시 <a href="/blog" target="_blank" style={{ color: "var(--accent)" }}>공개 블로그</a>와 사이트맵에 반영됩니다.
      </p>

      {/* 새 글 작성 */}
      <details className="card card-pad" style={{ marginBottom: 26 }} open={dbPosts.length === 0}>
        <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: 15 }}>+ 새 글 작성</summary>
        <BlogForm action={saveBlogPost} today={today} />
      </details>

      {/* DB 글(관리자 작성) 목록 */}
      <h2 style={{ fontSize: 15, margin: "0 0 10px", color: "var(--text-2)" }}>내가 쓴 글 ({dbPosts.length}편)</h2>
      {dbPosts.length === 0 && <p className="muted small" style={{ marginBottom: 24 }}>아직 작성한 글이 없습니다. 위에서 새 글을 써보세요.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 34 }}>
        {dbPosts.map((p) => (
          <div key={p.slug} className="card card-pad" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span className="badge" style={{ background: p.published ? "var(--accent)" : "var(--border)", color: p.published ? "#fff" : "var(--text-3)", padding: "1px 8px", borderRadius: 999, fontSize: 11, fontWeight: 700 }}>
                  {p.published ? "발행됨" : "임시저장"}
                </span>
                <b style={{ fontSize: 14 }}>{p.title}</b>
              </div>
              <div className="muted small" style={{ marginTop: 3 }}>
                {p.date}{p.category ? ` · ${p.category}` : ""} · /blog/{p.slug}
              </div>
            </div>
            <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
              <a className="btn sm" href={`/admin/blog/${p.slug}`}>수정</a>
              {p.published && <a className="btn sm" href={`/blog/${p.slug}`} target="_blank">보기</a>}
              <form action={toggleBlogPublish}>
                <input type="hidden" name="slug" value={p.slug} />
                <button className="btn sm" type="submit">{p.published ? "발행취소" : "발행"}</button>
              </form>
              <form action={deleteBlogPost}>
                <input type="hidden" name="slug" value={p.slug} />
                <button className="btn sm" type="submit" style={{ color: "var(--red, #d33)", borderColor: "var(--red, #d33)" }}>삭제</button>
              </form>
            </div>
          </div>
        ))}
      </div>

      {/* 파일 글(코드 관리) — 읽기 전용 */}
      <h2 style={{ fontSize: 15, margin: "0 0 10px", color: "var(--text-2)" }}>코드로 관리되는 글 ({files.length}편)</h2>
      <p className="muted small" style={{ margin: "0 0 10px" }}>초기 콘텐츠로, 파일(content/blog)로 관리됩니다. 여기서는 수정할 수 없습니다.</p>
      <div className="card card-pad" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {files.map((s) => (
          <a key={s} href={`/blog/${s}`} target="_blank" className="badge" style={{ padding: "3px 10px", borderRadius: 999, border: "1px solid var(--border)", fontSize: 12, color: "var(--text-2)" }}>{s}</a>
        ))}
        {files.length === 0 && <span className="muted small">없음</span>}
      </div>
    </div>
  );
}

// 작성/수정 공용 폼
export function BlogForm({
  action,
  post,
  today,
}: {
  action: (form: FormData) => void;
  post?: { slug: string; title: string; seoTitle: string; description: string; keywords: string; category: string; body: string; author: string; date: string; published: boolean };
  today: string;
}) {
  const L: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 700, color: "var(--text-2)", margin: "14px 0 4px" };
  const I: React.CSSProperties = { width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)", fontSize: 13, boxSizing: "border-box" };
  return (
    <form action={action} style={{ marginTop: 12 }}>
      <label style={L}>제목 *</label>
      <input style={I} name="title" required defaultValue={post?.title} placeholder="예) 병원 홈페이지 예약 전환율 높이는 법" />

      <label style={L}>주소(slug) * — 영문·숫자·하이픈만. 예: hospital-booking-tips</label>
      <input style={I} name="slug" required defaultValue={post?.slug} readOnly={!!post} placeholder="hospital-booking-tips" />
      {post && <div className="muted small" style={{ marginTop: 3 }}>주소는 발행 후 변경할 수 없습니다(SEO 보호).</div>}

      <label style={L}>카테고리</label>
      <input style={I} name="category" defaultValue={post?.category} placeholder="예) 전환율 · 병원마케팅" />

      <label style={L}>요약(설명) — 목록·검색 결과에 노출</label>
      <input style={I} name="description" defaultValue={post?.description} placeholder="한 줄 요약" />

      <label style={L}>검색 키워드 — 쉼표로 구분</label>
      <input style={I} name="keywords" defaultValue={post?.keywords} placeholder="히트맵, 전환율, 병원마케팅" />

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 160px" }}>
          <label style={L}>발행일</label>
          <input style={I} name="date" defaultValue={post?.date || today} placeholder={today} />
        </div>
        <div style={{ flex: "1 1 160px" }}>
          <label style={L}>작성자</label>
          <input style={I} name="author" defaultValue={post?.author || "FlowLens (주식회사 베놈)"} />
        </div>
      </div>

      <label style={L}>SEO 제목(선택) — 비우면 제목 사용</label>
      <input style={I} name="seoTitle" defaultValue={post?.seoTitle} placeholder="검색 결과 제목" />

      <label style={L}>본문 (마크다운) — ## 소제목, **굵게**, - 목록, [링크](주소) 사용 가능</label>
      <textarea style={{ ...I, minHeight: 320, fontFamily: "ui-monospace, monospace", lineHeight: 1.6 }} name="body" defaultValue={post?.body} placeholder={"## 소제목\n\n본문을 작성하세요.\n\n- 핵심 1\n- 핵심 2"} />

      <label style={{ display: "flex", alignItems: "center", gap: 8, margin: "16px 0 4px", fontSize: 14, fontWeight: 700 }}>
        <input type="checkbox" name="published" defaultChecked={post?.published} value="on" style={{ width: 16, height: 16 }} />
        지금 발행하기 (체크 안 하면 임시저장)
      </label>

      <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
        <button className="btn primary" type="submit">저장</button>
        <a className="btn" href="/admin/blog">취소</a>
      </div>
    </form>
  );
}
