import { notFound } from "next/navigation";
import { getAdminUser } from "@/lib/admin";
import { prisma } from "@/lib/db";
import { PLANS } from "@/lib/plans";
import { adminSetPlan, adminExtendTrial, adminClearTrial } from "./actions";
import ConfirmButton from "./ConfirmButton";
import { getAllPosts } from "@/lib/blog";

export const dynamic = "force-dynamic";

function ym(): string {
  return new Date().toISOString().slice(0, 7);
}

const ACTION_LABEL: Record<string, string> = {
  LOGIN: "로그인",
  SIGNUP: "가입",
  CHANGE_PLAN: "요금제 변경",
  DELETE_DATA: "데이터 삭제",
  CREATE_SHARE: "공유링크 생성",
  CREATE_SITE: "사이트 등록",
  CHANGE_PASSWORD: "비밀번호 변경",
  TRIAL_REMINDER: "체험 만료 알림",
};

function fmtTs(d: Date): string {
  return d.toISOString().slice(0, 16).replace("T", " ");
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

  // 최근 활동(감사 로그): 누가 언제 무엇을 했는지 — 운영 추적용
  const agencyName = new Map(agencies.map((a) => [a.id, a.name]));
  const auditLogs = await prisma.auditLog.findMany({ orderBy: { ts: "desc" }, take: 40 });

  // 발행된 블로그 글 목록 (파일 기반 — 읽기 전용 현황)
  const posts = getAllPosts();

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

  // 운영자 요약: 실계정 기준 총계 + 현재 요금제 배정 기준 예상 월 매출(MRR).
  const totalSites = real.reduce((n, r) => n + r.siteCount, 0);
  const totalSessions = real.reduce((n, r) => n + r.used, 0);
  const paidCount = real.filter((r) => r.plan !== "FREE").length;
  const mrr = real.reduce((n, r) => n + (PLANS.find((p) => p.key === r.plan)?.price ?? 0), 0);
  const summary = [
    { label: "실계정", value: real.length.toLocaleString() },
    { label: "활성 사이트", value: totalSites.toLocaleString() },
    { label: "이번 달 총 세션", value: totalSessions.toLocaleString() },
    { label: "예상 월 매출(MRR)", value: `${mrr.toLocaleString()}원`, sub: `유료 ${paidCount}곳` },
  ];

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
      <div className="notice small" style={{ marginBottom: 18 }}>
        결제 연동 전까지 <b>유료 전환은 여기서 수동으로</b> 처리합니다. 요금제를 바꾸면 사이트 보관일도 자동으로 맞춰지고, 모든 변경은 감사 로그에 남습니다. (네온 SQL 직접 입력을 대체)
      </div>

      <div className="grid grid-4" style={{ marginBottom: 22 }}>
        {summary.map((s) => (
          <div key={s.label} className="card metric">
            <div className="label">{s.label}</div>
            <div className="value" style={{ fontVariantNumeric: "tabular-nums" }}>{s.value}</div>
            {s.sub && <div className="sub">{s.sub}</div>}
          </div>
        ))}
      </div>

      <AgencyTable title="실계정" rows={real} />
      {test.length > 0 && <AgencyTable title="테스트 계정 (@example.com)" rows={test} muted />}

      {/* 최근 활동 (감사 로그) — 누가 언제 무엇을 했는지 */}
      <div style={{ marginTop: 34 }}>
        <h2 style={{ fontSize: 15, margin: "0 0 12px", color: "var(--text-2)" }}>최근 활동 (감사 로그 · 최근 {auditLogs.length}건)</h2>
        {auditLogs.length === 0 ? (
          <div className="card card-pad muted small">아직 기록된 활동이 없습니다.</div>
        ) : (
          <div className="card" style={{ padding: 0, overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 640 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--text-3)", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 14px", fontWeight: 700 }}>시각(UTC)</th>
                  <th style={{ padding: "10px 14px", fontWeight: 700 }}>행위</th>
                  <th style={{ padding: "10px 14px", fontWeight: 700 }}>대행사</th>
                  <th style={{ padding: "10px 14px", fontWeight: 700 }}>사용자</th>
                  <th style={{ padding: "10px 14px", fontWeight: 700 }}>상세</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((l) => (
                  <tr key={l.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "9px 14px", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums", color: "var(--text-3)" }}>{fmtTs(l.ts)}</td>
                    <td style={{ padding: "9px 14px", whiteSpace: "nowrap", fontWeight: 700 }}>{ACTION_LABEL[l.action] ?? l.action}</td>
                    <td style={{ padding: "9px 14px" }}>{agencyName.get(l.agencyId) ?? "—"}</td>
                    <td style={{ padding: "9px 14px", color: "var(--text-3)" }}>{l.userEmail || "—"}</td>
                    <td style={{ padding: "9px 14px", color: "var(--text-3)" }}>{l.detail || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 블로그 글 현황 (읽기 전용 — 발행/수정은 코드·배포로 관리) */}
      <div style={{ marginTop: 34 }}>
        <h2 style={{ fontSize: 15, margin: "0 0 4px", color: "var(--text-2)" }}>블로그 글 ({posts.length}편)</h2>
        <p className="muted small" style={{ margin: "0 0 12px" }}>
          현재 블로그는 코드(파일) 기반으로 관리됩니다. 이 목록은 발행 현황이며, 새 글 작성·수정은 배포로 반영됩니다.
        </p>
        <div className="card" style={{ padding: 0, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 560 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--text-3)", borderBottom: "1px solid var(--border)" }}>
                <th style={{ padding: "10px 14px", fontWeight: 700 }}>발행일</th>
                <th style={{ padding: "10px 14px", fontWeight: 700 }}>카테고리</th>
                <th style={{ padding: "10px 14px", fontWeight: 700 }}>제목</th>
              </tr>
            </thead>
            <tbody>
              {posts.map((p) => (
                <tr key={p.slug} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "9px 14px", whiteSpace: "nowrap", color: "var(--text-3)", fontVariantNumeric: "tabular-nums" }}>{p.date}</td>
                  <td style={{ padding: "9px 14px", whiteSpace: "nowrap", color: "var(--text-3)" }}>{p.category ?? "—"}</td>
                  <td style={{ padding: "9px 14px" }}>
                    <a href={`/blog/${p.slug}`} target="_blank" style={{ color: "var(--accent)" }}>{p.title}</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
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
                {(() => {
                  const over = r.planLimit > 0 && r.used >= r.planLimit;
                  const near = r.planLimit > 0 && !over && r.used >= r.planLimit * 0.8;
                  const color = over ? "var(--red)" : near ? "var(--amber)" : "var(--text-3)";
                  return (
                    <div className="small" style={{ marginTop: 2, fontVariantNumeric: "tabular-nums", color, fontWeight: over || near ? 700 : 400 }}>
                      이번 달 {r.used.toLocaleString()} / {r.planLimit.toLocaleString()} 세션
                      {over ? " · 한도 초과" : near ? " · 한도 임박" : ""}
                    </div>
                  );
                })()}
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
