import { notFound } from "next/navigation";
import { getAdminUser } from "@/lib/admin";
import { getAllDbPosts } from "@/lib/blog";
import { saveBlogPost, toggleBlogPublish, deleteBlogPost, generateBlogDraft } from "./actions";
import { CAT_LABEL } from "@/lib/autoblog/generator";
import { BlogForm } from "./BlogForm";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const maxDuration = 60; // AI 생성이 오래 걸릴 수 있어 여유 확보
export const metadata = { title: "블로그 관리 — FlowLens 운영자" };

// 파일(코드) 기반 글 목록 — 읽기 전용 표시용
function fileSlugs(): string[] {
  const dir = path.join(process.cwd(), "content", "blog");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".md")).map((f) => f.replace(/\.md$/, ""));
}

export default async function AdminBlog({ searchParams }: { searchParams: Promise<{ err?: string }> }) {
  const admin = await getAdminUser();
  if (!admin) notFound();

  const { err } = await searchParams;
  const dbPosts = await getAllDbPosts();
  const files = fileSlugs();
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="admin-wrap" style={{ maxWidth: 900, margin: "0 auto", padding: "28px 18px 80px" }}>
      <a href="/admin" className="muted small">← 운영자 홈</a>
      <h1 style={{ fontSize: 22, margin: "8px 0 4px" }}>블로그 관리</h1>
      <p className="muted small" style={{ margin: "0 0 24px" }}>
        여기서 블로그 글을 직접 쓰거나 <b>AI로 초안을 생성</b>해 발행할 수 있습니다. <b>발행</b>을 켜면 즉시 <a href="/blog" target="_blank" style={{ color: "var(--accent)" }}>공개 블로그</a>와 사이트맵에 반영됩니다.
      </p>

      {err && (
        <div className="card card-pad" style={{ marginBottom: 18, background: "#3d1a1a", border: "1px solid #7f2c2c", color: "#f8b4b4" }}>
          ❌ {err}
        </div>
      )}

      {/* AI 초안 생성 */}
      <details className="card card-pad" style={{ marginBottom: 18 }}>
        <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: 15 }}>🤖 AI로 초안 생성</summary>
        <p className="muted small" style={{ margin: "10px 0 0" }}>
          키워드를 넣으면 AI가 초안을 쓰고 <b>의료광고법 금지어를 자동 검수</b>합니다. 결과는 <b>임시저장(초안)</b>으로 저장되며, 검토·수정 후 직접 발행합니다. (OpenAI API 키 필요 · 글 1편당 약 수십~수백 원)
        </p>
        <AiForm />
      </details>

      {/* 새 글 직접 작성 */}
      <details className="card card-pad" style={{ marginBottom: 26 }} open={dbPosts.length === 0}>
        <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: 15 }}>+ 새 글 직접 작성</summary>
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

// AI 초안 생성 폼
function AiForm() {
  const L: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 700, color: "var(--text-2)", margin: "14px 0 4px" };
  const I: React.CSSProperties = { width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)", fontSize: 13, boxSizing: "border-box" };
  return (
    <form action={generateBlogDraft} style={{ marginTop: 12 }}>
      <label style={L}>카테고리(주제)</label>
      <select style={I} name="category" defaultValue="heatmap">
        {Object.entries(CAT_LABEL).map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </select>

      <label style={L}>키워드 * — 글의 핵심 주제</label>
      <input style={I} name="keyword" required placeholder="예) 병원 홈페이지 예약 전환율" />

      <label style={L}>지역(선택) — 지역 맥락을 넣고 싶을 때</label>
      <input style={I} name="region" placeholder="예) 강남, 부산 서면" />

      <label style={L}>추가 지시(선택)</label>
      <input style={I} name="extra" placeholder="예) 모바일 위주로, 초보자 대상으로" />

      <div style={{ marginTop: 16 }}>
        <button className="btn primary" type="submit">🤖 초안 생성 (30초~1분 소요)</button>
      </div>
      <p className="muted small" style={{ marginTop: 8 }}>생성 후 수정 화면으로 이동합니다. 내용을 확인한 뒤 발행하세요.</p>
    </form>
  );
}
