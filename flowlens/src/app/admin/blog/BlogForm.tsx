import { SubmitButton } from "./SubmitButton";

// 블로그 글 작성/수정 공용 폼 (서버 컴포넌트에서 사용)
export function BlogForm({
  action,
  post,
  today,
}: {
  action: (form: FormData) => void;
  post?: {
    slug: string;
    title: string;
    seoTitle: string;
    description: string;
    keywords: string;
    category: string;
    body: string;
    author: string;
    date: string;
    published: boolean;
  };
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

      <label style={L}>본문 (마크다운 또는 HTML) — ## 소제목, **굵게**, - 목록, [링크](주소) 사용 가능</label>
      <textarea style={{ ...I, minHeight: 320, fontFamily: "ui-monospace, monospace", lineHeight: 1.6 }} name="body" defaultValue={post?.body} placeholder={"## 소제목\n\n본문을 작성하세요.\n\n- 핵심 1\n- 핵심 2"} />

      <label style={{ display: "flex", alignItems: "center", gap: 8, margin: "16px 0 4px", fontSize: 14, fontWeight: 700 }}>
        <input type="checkbox" name="published" defaultChecked={post?.published} value="on" style={{ width: 16, height: 16 }} />
        지금 발행하기 (체크 안 하면 임시저장)
      </label>

      <div style={{ marginTop: 16, display: "flex", gap: 8, alignItems: "center" }}>
        <SubmitButton pending="저장 중…">저장</SubmitButton>
        <a className="btn" href="/admin/blog">취소</a>
      </div>
    </form>
  );
}
