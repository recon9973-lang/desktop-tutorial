import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { prisma } from "@/lib/db";
import { getPlan } from "@/lib/plans";
import { confirmPayment } from "@/lib/toss";
import TopBar from "@/components/TopBar";

export const dynamic = "force-dynamic";

// 토스 결제 성공 리다이렉트 처리: confirm API로 최종 승인 후 요금제 반영.
export default async function SuccessPage({
  searchParams,
}: {
  searchParams: Promise<{ paymentKey?: string; orderId?: string; amount?: string; plan?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const sp = await searchParams;

  const plan = getPlan(sp.plan || "");
  const amount = Number(sp.amount || 0);
  let ok = false;
  let message = "";

  if (sp.paymentKey && sp.orderId && amount > 0) {
    // 금액 위변조 방지: 요청 금액이 요금제 가격과 일치해야 함
    if (amount !== plan.price) {
      message = "결제 금액이 요금제 가격과 일치하지 않습니다.";
    } else {
      const result = await confirmPayment(sp.paymentKey, sp.orderId, amount);
      if (result.ok) {
        await prisma.agency.update({ where: { id: user.agencyId }, data: { plan: plan.key } });
        ok = true;
      } else {
        message = `${result.message} (${result.code})`;
      }
    }
  } else {
    message = "결제 정보가 부족합니다.";
  }

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container" style={{ maxWidth: 520 }}>
        <div className="card card-pad" style={{ textAlign: "center", marginTop: 20 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>{ok ? "✅" : "⚠️"}</div>
          <h1 style={{ fontSize: 20, marginBottom: 8 }}>{ok ? "결제가 완료되었습니다" : "결제를 확인하지 못했습니다"}</h1>
          {ok ? (
            <p className="muted" style={{ marginTop: 0 }}>{plan.name} 요금제({plan.price.toLocaleString()}원/월)가 적용되었습니다.</p>
          ) : (
            <p className="muted" style={{ marginTop: 0 }}>{message}</p>
          )}
          <div className="row" style={{ justifyContent: "center", marginTop: 16 }}>
            <Link className="btn primary" href="/billing">요금제로 돌아가기</Link>
            <Link className="btn" href="/dashboard">대시보드</Link>
          </div>
        </div>
      </div>
    </>
  );
}
