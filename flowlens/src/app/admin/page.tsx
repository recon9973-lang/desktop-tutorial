import { notFound } from "next/navigation";
import { getAdminUser } from "@/lib/admin";
import { prisma } from "@/lib/db";
import { PLANS } from "@/lib/plans";
import { adminSetPlan, adminExtendTrial, adminClearTrial } from "./actions";
import ConfirmButton from "./ConfirmButton";

export const dynamic = "force-dynamic";

function ym(): string {
  return new Date().toISOString().slice(0, 7);
}

export default async function AdminPage() {
  const admin = await getAdminUser();
  // 운영자가 아니면 페이지 존재 자체를 숨긴다(로그인 리다이렉트 대신 404).
  if (!admin) notFound();

  const thisYm = ym();
  const agencies = await prisma.agency.findMany({
    orderBy: { createdAt: "asc" },
    include: {
      users: { select: { email: true, name: true, role: true }, orderBy: { createdAt: "asc" } },
      clients: { select: { id: true, sites: { select: { id: true, name: true, domain: true } } } },
    },
  });

  // 이번 달 사용량을 한 번에 조회
  const usages = await prisma.usageMonth.findMany({ where: { ym: thisYm } });
  const usageBy = new Map(usages.map((u) => [u.agencyId, u.sessions]));

  const now = Date.now();
  const rows = agencies.map((a) => {
    const siteCount = a.clients.reduce((n, c) => n + c.sites.length, 0);
    const trial =
      a.trialEndsAt == null
        ? { label: "제한 없음", danger: false }
        : a.trialEndsAt.getTime() < now
          ? { label: "체험 만료 · 수집 멈춤", danger: true }
          : { label: `체험 ~${a.trialEndsAt.toISOString().slice(5, 10)}`, danger: false };
    const plan = PLANS.find((p) => p.key === a.plan) ?? PLANS[0];
    return {
      id: a.id,
      name: a.name,
      plan: a.plan,
      planLimit: plan.sessionsPerMonth,
      used: usageBy.get(a.id) ?? 0,
      trial,
      users: a.users,
      isTest: a.users.some((u) => u.email.endsWith("@example.com")),
      siteCount,
      sites: a.clients.flatMap((c) => c.sites),
    };
  });

  const real = rows.filter((r) => !r.isTest);
  const test = rows.filter((r) => r.isTest);

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", padding: "28px 22px 80px" }}>
      <div className="between" style={{ marginBottom: 6 }}>
        <div>
          <div className="small" style={{ color: "var(--red)", fontWeight: 800, letterSpacing: "0.06em" }}>운영자 전용 · ADMIN</div>
          <h1 style={{ margin: "4px 0 0", fontSize: 26 }}>대행사 관리</h1>
        </div>
        <div className="small muted" style={{ textAlign: "right" }}>
          {admin.email}
          <br />
          {thisYm} 기준 · 실계정 {real.length} · 테스트 {test.length}
        </div>
      </div>
      <div className="notice small" style={{ marginBottom: 20 }}>
        결제 연동 전까지 <b>유료 전환은 여기서 수동으로</b> 처리합니다. 요금제를 바꾸면 사이트 보관일도 자동으로 맞춰지고, 모든 변경은 감사 로그에 남습니다. (네온 SQL 직접 입력을 대체)
      </div>

      <AgencyTable title="실계정" rows={real} />
      {test.length > 0 && <AgencyTable title="테스트 계정 (@example.com)" rows={test} muted />}
    </div>
  );
}

type Row = {
  id: string;
  name: string;
  plan: string;
  planLimit: number;
  used: number;
  trial: { label: string; danger: boolean };
  users: { email: string; name: string; role: string }[];
  siteCount: number;
  sites: { id: string; name: string; domain: string }[];
};

function AgencyTable({ title, rows, muted = false }: { title: string; rows: Row[]; muted?: boolean }) {
  if (rows.length === 0) return null;
  return (
    <div style={{ marginTop: 26, opacity: muted ? 0.72 : 1 }}>
      <h2 style={{ fontSize: 15, margin: "0 0 12px", color: "var(--text-2)" }}>{title}</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {rows.map((r) => (
          <div key={r.id} className="card" style={{ padding: 18 }}>
            <div className="between" style={{ flexWrap: "wrap", gap: 12, alignItems: "flex-start" }}>
              <div style={{ minWidth: 220 }}>
                <div style={{ fontWeight: 750, fontSize: 16 }}>{r.name}</div>
                <div className="small muted" style={{ marginTop: 2 }}>
                  {r.users.map((u) => `${u.name} <${u.email}>`).join(", ") || "(사용자 없음)"}
                </div>
                <div className="small muted" style={{ marginTop: 4 }}>
                  사이트 {r.siteCount}개{r.sites.length ? ` · ${r.sites.map((s) => s.domain).join(", ")}` : ""}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontWeight: 800, fontSize: 15 }}>{r.plan}</div>
                <div className="small" style={{ color: r.trial.danger ? "var(--red)" : "var(--text-3)", marginTop: 2, fontWeight: r.trial.danger ? 700 : 400 }}>
                  {r.trial.label}
                </div>
                <div className="small muted" style={{ marginTop: 2, fontVariantNumeric: "tabular-nums" }}>
                  이번 달 {r.used.toLocaleString()} / {r.planLimit.toLocaleString()} 세션
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14, alignItems: "center" }}>
              {/* 요금제 변경 */}
              <form action={adminSetPlan} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input type="hidden" name="agencyId" value={r.id} />
                <select name="plan" defaultValue={r.plan} className="btn sm" style={{ padding: "6px 10px" }} aria-label="요금제 선택">
                  {PLANS.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.key} · {p.priceLabel}
                    </option>
                  ))}
                </select>
                <ConfirmButton
                  className="btn sm primary"
                  message={`[${r.name}]의 요금제를 바꿉니다.\n\n무료(FREE)로 내리면 보관일이 14일로 줄어, 자동 정리가 켜진 뒤 오래된 데이터가 삭제될 수 있습니다.\n\n계속할까요?`}
                >
                  요금제 적용
                </ConfirmButton>
              </form>
              <span style={{ width: 1, height: 20, background: "var(--border)" }} />
              {/* 체험 제어 */}
              <form action={adminExtendTrial}>
                <input type="hidden" name="agencyId" value={r.id} />
                <button type="submit" className="btn sm">체험 +14일</button>
              </form>
              <form action={adminClearTrial}>
                <input type="hidden" name="agencyId" value={r.id} />
                <ConfirmButton className="btn sm" message={`[${r.name}]의 체험 제한을 해제해 수집을 다시 켭니다. 계속할까요?`}>
                  체험 제한 해제
                </ConfirmButton>
              </form>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
