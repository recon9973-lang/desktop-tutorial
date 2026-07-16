import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import TopBar from "@/components/TopBar";
import LogoUploader from "@/components/LogoUploader";

export const dynamic = "force-dynamic";

const PW_ERRORS: Record<string, string> = {
  short: "새 비밀번호는 8자 이상이어야 합니다.",
  mismatch: "새 비밀번호 확인이 일치하지 않습니다.",
  current: "현재 비밀번호가 올바르지 않습니다.",
  same: "기존과 다른 비밀번호를 입력해 주세요.",
};

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ saved?: string; error?: string; pwsaved?: string; pwerror?: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { saved, error, pwsaved, pwerror } = await searchParams;

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container" style={{ maxWidth: 640 }}>
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>설정</h1>
        <p className="muted small" style={{ marginBottom: 20 }}>대행사 브랜드 · 화이트라벨 리포트 표시를 관리합니다.</p>

        {saved && <div className="notice" style={{ marginBottom: 16 }}>저장되었습니다.</div>}
        {error === "role" && <div className="notice" style={{ marginBottom: 16, background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c" }}>브랜드 설정은 OWNER 권한만 가능합니다.</div>}

        <div className="card card-pad" style={{ marginBottom: 18 }}>
          <h4 style={{ marginBottom: 4 }}>화이트라벨 로고</h4>
          <p className="muted small" style={{ marginTop: 0, marginBottom: 16 }}>고객 공유 리포트 상단에 표시될 로고입니다.</p>
          <LogoUploader currentUrl={user.agency.logoUrl} logoText={user.agency.logoText} />
        </div>

        <div className="card card-pad" style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 4 }}>내 계정</h4>
          <div className="between" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}><span className="muted small">이름</span><b className="small">{user.name}</b></div>
          <div className="between" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}><span className="muted small">로그인 이메일</span><b className="small">{user.email}</b></div>
          <div className="between" style={{ padding: "10px 0" }}><span className="muted small">권한</span><b className="small">{user.role}</b></div>
        </div>

        <div className="card card-pad" style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 4 }}>비밀번호 변경</h4>
          <p className="muted small" style={{ marginTop: 0, marginBottom: 14 }}>주기적으로 변경하고, 임시 비밀번호를 쓰고 있다면 지금 바꾸세요.</p>
          {pwsaved && <div className="notice" style={{ marginBottom: 14 }}>비밀번호가 변경되었습니다.</div>}
          {pwerror && (
            <div className="notice" style={{ marginBottom: 14, background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c" }}>
              {PW_ERRORS[pwerror] || "비밀번호를 확인해 주세요."}
            </div>
          )}
          <form action="/api/settings/password" method="post" className="stack" style={{ gap: 12, maxWidth: 360 }}>
            <div className="field">
              <label className="small" style={{ fontWeight: 700 }}>현재 비밀번호</label>
              <input name="current" type="password" required autoComplete="current-password" style={{ width: "100%" }} />
            </div>
            <div className="field">
              <label className="small" style={{ fontWeight: 700 }}>새 비밀번호 (8자 이상)</label>
              <input name="next" type="password" required minLength={8} autoComplete="new-password" style={{ width: "100%" }} />
            </div>
            <div className="field">
              <label className="small" style={{ fontWeight: 700 }}>새 비밀번호 확인</label>
              <input name="confirm" type="password" required minLength={8} autoComplete="new-password" style={{ width: "100%" }} />
            </div>
            <button className="btn primary" type="submit" style={{ width: "fit-content" }}>비밀번호 변경</button>
          </form>
        </div>

        <div className="card card-pad">
          <h4 style={{ marginBottom: 4 }}>대행사 정보</h4>
          <div className="between" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}><span className="muted small">대행사명</span><b className="small">{user.agency.name}</b></div>
          <div className="between" style={{ padding: "10px 0" }}><span className="muted small">요금제</span><b className="small">{user.agency.plan}</b></div>
        </div>
      </div>
    </>
  );
}
