import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import TopBar from "@/components/TopBar";

export const dynamic = "force-dynamic";

export default async function FailPage({ searchParams }: { searchParams: Promise<{ message?: string; code?: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const sp = await searchParams;

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container" style={{ maxWidth: 520 }}>
        <div className="card card-pad" style={{ textAlign: "center", marginTop: 20 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>⚠️</div>
          <h1 style={{ fontSize: 20, marginBottom: 8 }}>결제가 취소되었거나 실패했습니다</h1>
          <p className="muted" style={{ marginTop: 0 }}>{sp.message || "결제가 완료되지 않았습니다."} {sp.code && `(${sp.code})`}</p>
          <div className="row" style={{ justifyContent: "center", marginTop: 16 }}>
            <Link className="btn primary" href="/billing">요금제로 돌아가기</Link>
          </div>
        </div>
      </div>
    </>
  );
}
