import Link from "next/link";
import crypto from "crypto";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { getPlan, PLANS } from "@/lib/plans";
import { tossConfigured } from "@/lib/toss";
import TopBar from "@/components/TopBar";
import TossCheckout from "@/components/TossCheckout";

export const dynamic = "force-dynamic";

export default async function CheckoutPage({ searchParams }: { searchParams: Promise<{ plan?: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { plan: planKey } = await searchParams;

  const plan = PLANS.find((p) => p.key === planKey);
  if (!plan || plan.key === "FREE") redirect("/billing");

  const configured = tossConfigured();
  const clientKey = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY || "";
  const orderId = `flowlens_${plan.key}_${crypto.randomBytes(8).toString("hex")}`;
  const orderName = `FlowLens ${plan.name} 요금제 (월)`;

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container" style={{ maxWidth: 560 }}>
        <Link href="/billing" className="muted small">← 요금제</Link>
        <h1 style={{ fontSize: 22, margin: "10px 0 18px" }}>결제</h1>

        <div className="card card-pad" style={{ marginBottom: 18 }}>
          <div className="between">
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{plan.name} 요금제</div>
              <div className="muted small">{plan.target} · 월 구독</div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 800 }}>{plan.price.toLocaleString()}원</div>
          </div>
        </div>

        {configured ? (
          <div className="card card-pad">
            <TossCheckout
              clientKey={clientKey}
              customerKey={`agency_${user.agencyId}`}
              amount={plan.price}
              orderId={orderId}
              orderName={orderName}
              planKey={plan.key}
            />
            <p className="muted small" style={{ marginTop: 14 }}>
              테스트 모드에서는 실제 결제가 일어나지 않습니다. 토스 테스트 카드로 결제 흐름을 확인할 수 있습니다.
            </p>
          </div>
        ) : (
          <div className="card card-pad">
            <div className="notice" style={{ marginBottom: 14 }}>
              토스페이먼츠 키가 아직 설정되지 않았습니다. 실제 결제 위젯을 보려면 <code>.env</code>에
              <code> NEXT_PUBLIC_TOSS_CLIENT_KEY</code>와 <code>TOSS_SECRET_KEY</code>(개발자센터의 테스트 키)를 넣고 서버를 재시작하세요.
            </div>
            <form action="/api/billing/change-plan" method="post">
              <input type="hidden" name="plan" value={plan.key} />
              <button className="btn primary" type="submit" style={{ width: "100%", justifyContent: "center" }}>
                (개발용) 결제 없이 이 요금제 적용
              </button>
            </form>
          </div>
        )}
      </div>
    </>
  );
}
