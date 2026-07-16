import Link from "next/link";

export default function TopBar({ agencyName, userName }: { agencyName: string; userName?: string }) {
  return (
    <div className="topbar">
      <Link href="/dashboard" className="brand">
        <span className="dot" />
        FlowLens
        <span className="pill" style={{ marginLeft: 6 }}>{agencyName}</span>
      </Link>
      <div className="row">
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
