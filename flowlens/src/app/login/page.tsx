import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await getCurrentUser();
  if (user) redirect("/dashboard");
  const { error } = await searchParams;

  return (
    <div className="auth-wrap">
      <div className="card card-pad auth-card">
        <div className="brand" style={{ marginBottom: 4 }}>
          <span className="dot" /> FlowLens
        </div>
        <p className="muted small" style={{ marginTop: 6, marginBottom: 22 }}>
          대행사 로그인 — 여러 고객사의 행동 분석을 한 곳에서.
        </p>

        {error && (
          <div className="notice" style={{ background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c", marginBottom: 16 }}>
            {error === "locked"
              ? "로그인 시도가 너무 많습니다. 15분 후 다시 시도해 주세요."
              : "이메일 또는 비밀번호가 올바르지 않습니다."}
          </div>
        )}

        <form action="/api/auth/login" method="post">
          <div className="field">
            <label>이메일</label>
            <input name="email" type="email" placeholder="you@company.com" required />
          </div>
          <div className="field">
            <label>비밀번호</label>
            <input name="password" type="password" placeholder="••••••••" required />
          </div>
          <button className="btn primary" type="submit" style={{ width: "100%", justifyContent: "center", marginTop: 6 }}>
            로그인
          </button>
        </form>

        <div className="hr" />
        <p className="small muted" style={{ margin: 0 }}>
          계정이 없으신가요? <Link href="/signup" style={{ color: "var(--accent)" }}>대행사 워크스페이스 만들기</Link>
        </p>
      </div>
    </div>
  );
}
