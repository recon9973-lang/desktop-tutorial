import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";

const ERRORS: Record<string, string> = {
  invalid: "입력값을 확인하세요. 비밀번호는 8자 이상이어야 합니다.",
  email: "이미 가입된 이메일입니다.",
  agree: "약관·개인정보처리방침·처리위탁 계약(DPA)에 동의해야 가입할 수 있습니다.",
};

export default async function SignupPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await getCurrentUser();
  if (user) redirect("/dashboard");
  const { error } = await searchParams;

  return (
    <div className="auth-wrap">
      <div className="card card-pad auth-card">
        <div className="brand" style={{ marginBottom: 4 }}>
          <span className="dot" /> FlowLens
        </div>
        <p className="muted small" style={{ marginTop: 6, marginBottom: 22 }}>대행사 워크스페이스 만들기 — 무료로 시작.</p>

        {error && (
          <div className="notice" style={{ background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c", marginBottom: 16 }}>
            {ERRORS[error] ?? "가입 중 오류가 발생했습니다."}
          </div>
        )}

        <form action="/api/auth/signup" method="post">
          <div className="field"><label>대행사 / 회사 이름</label><input name="agencyName" placeholder="그로스랩" required /></div>
          <div className="field"><label>이름</label><input name="name" placeholder="홍길동" required /></div>
          <div className="field"><label>이메일</label><input name="email" type="email" placeholder="you@company.com" required /></div>
          <div className="field"><label>비밀번호 (8자 이상)</label><input name="password" type="password" minLength={8} required /></div>
          <label className="small muted" style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "10px 0 2px", lineHeight: 1.5 }}>
            <input name="agree" type="checkbox" value="1" required style={{ marginTop: 3 }} />
            <span>
              <Link href="/terms" style={{ color: "var(--accent)" }}>이용약관</Link>,{" "}
              <Link href="/privacy" style={{ color: "var(--accent)" }}>개인정보처리방침</Link>,{" "}
              <Link href="/dpa" style={{ color: "var(--accent)" }}>개인정보 처리위탁 계약(DPA)</Link>에 동의합니다. (필수)
            </span>
          </label>
          <button className="btn primary" type="submit" style={{ width: "100%", justifyContent: "center", marginTop: 10 }}>
            무료로 시작하기
          </button>
        </form>

        <div className="hr" />
        <p className="small muted" style={{ margin: 0 }}>
          이미 계정이 있으신가요? <Link href="/login" style={{ color: "var(--accent)" }}>로그인</Link>
        </p>
      </div>
    </div>
  );
}
