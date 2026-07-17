import Link from "next/link";

// isAdmin 은 서버(getAdminUser)로만 판정한 결과를 넘겨받는다. UI에서만 숨기는 게 아니라
// /admin 라우트 자체가 서버에서 재검증하므로, 이 링크는 편의용일 뿐 보안 경계가 아니다.
export default function TopBar({ agencyName, userName, isAdmin = false }: { agencyName: string; userName?: string; isAdmin?: boolean }) {
  return (
    <div className="topbar">
      <Link href="/dashboard" className="brand">
        <span className="dot" />
        FlowLens
        <span className="pill" style={{ marginLeft: 6 }}>{agencyName}</span>
      </Link>
      <div className="row">
        {isAdmin && (
          <Link href="/admin" className="btn sm" style={{ borderColor: "var(--red)", color: "var(--red)" }}>운영자</Link>
        )}
        <Link href="/settings" className="btn sm">설정</Link>
        <Link href="/billing" className="btn sm">요금제</Link>
        {userName && <span className="muted small">{userName}</span>}
        <form action="/api/auth/logout" method="post">
          <button className="btn sm" type="submit">로그아웃</button>
        </form>
      </div>
    </div>
  );
}
