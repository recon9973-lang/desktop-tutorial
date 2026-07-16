import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { prisma } from "@/lib/db";
import { getSitePaths } from "@/lib/metrics";
import PurgeForm from "@/components/PurgeForm";

export const dynamic = "force-dynamic";

const ACTION_LABEL: Record<string, string> = {
  LOGIN: "로그인", SIGNUP: "가입", DELETE_DATA: "데이터 삭제", CREATE_SHARE: "공유링크 생성", CHANGE_PLAN: "요금제 변경",
};

function fmt(d: Date) {
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(d);
}

export default async function DataPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ deleted?: string; err?: string }>;
}) {
  const { id } = await params;
  const { user, site } = await loadSiteForUser(id);
  if (!user || !site) redirect("/dashboard");
  const { deleted, err } = await searchParams;

  const [paths, logs] = await Promise.all([
    getSitePaths(site.id),
    prisma.auditLog.findMany({ where: { agencyId: user.agencyId }, orderBy: { ts: "desc" }, take: 20 }),
  ]);

  return (
    <div className="grid grid-2" style={{ alignItems: "start" }}>
      <div className="card card-pad">
        <h4 style={{ marginBottom: 6 }}>방문자 데이터 삭제</h4>
        <p className="muted small" style={{ marginTop: 0 }}>
          정보주체(방문자)의 삭제 요청이나 보관정책에 따라 이 사이트의 행동 데이터를 삭제합니다. <b>되돌릴 수 없습니다.</b>
        </p>

        {deleted && Number(deleted) >= 0 && !err && (
          <div className="notice" style={{ marginBottom: 14, background: "#e7f6ee", borderColor: "#bfe6cf", color: "#12a150" }}>
            {Number(deleted).toLocaleString()}건의 이벤트를 삭제했습니다.
          </div>
        )}
        {err && (
          <div className="notice" style={{ marginBottom: 14, background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c" }}>
            삭제 조건을 확인하세요. (입력값 누락 또는 대상 없음)
          </div>
        )}

        <PurgeForm siteId={site.id} paths={paths.map((p) => p.path)} />

        <div className="notice small" style={{ marginTop: 16 }}>
          보관기간 초과분은 서버의 자동 삭제(`npm run cleanup`, cron 등록)로도 정리됩니다. 이 도구는 즉시 삭제·개별 요청 처리용입니다.
        </div>
      </div>

      <div className="card card-pad">
        <h4 style={{ marginBottom: 6 }}>감사 로그</h4>
        <p className="muted small" style={{ marginTop: 0 }}>로그인·삭제·공유링크·요금제 변경 등 민감 행위 기록(최근 20건).</p>
        {logs.length === 0 ? (
          <div className="muted small">아직 기록이 없습니다.</div>
        ) : (
          <div className="stack" style={{ gap: 0 }}>
            {logs.map((l) => (
              <div key={l.id} className="between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <span className="badge gray">{ACTION_LABEL[l.action] ?? l.action}</span>
                  <span className="small" style={{ marginLeft: 8 }}>{l.detail || l.userEmail}</span>
                </div>
                <span className="muted small" style={{ flexShrink: 0 }}>{fmt(l.ts)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
