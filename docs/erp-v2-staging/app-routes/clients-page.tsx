// 목표 경로: src/app/(erp)/clients/page.tsx (조립 예시)
//
// 거래처 목록 페이지 — 서버 컴포넌트에서 데이터 조회 후 클라이언트 컴포넌트에 주입.
// 다른 페이지(work/finance/settings 등)도 동일 패턴으로 조립.
import { getCurrentUser } from "@/server/session";
import { listClientsForUser } from "@/server/repositories/clients";
import { getIndustryTree } from "@/server/repositories/masters";
import { ClientList } from "@/components/clients/ClientList";
import { ClientForm } from "@/components/clients/ClientForm";
import { db } from "@/server/db";
import { Role } from "@/domain/types";

export default async function ClientsPage() {
  const user = await getCurrentUser();
  if (!user) return null; // 미들웨어에서 /login 리다이렉트 전제

  const [rows, industries] = await Promise.all([listClientsForUser(user), getIndustryTree()]);
  const canCreate = user.role === Role.SUPER_ADMIN || user.role === Role.ADMIN;
  const marketers = canCreate
    ? await db.user.findMany({ where: { role: Role.MARKETER, status: "ACTIVE" }, select: { id: true, name: true } })
    : [];

  return (
    <div className="space-y-8 p-6">
      <section>
        <h1 className="mb-4 text-xl font-semibold">거래처</h1>
        <ClientList rows={rows} />
      </section>

      {canCreate && (
        <section className="rounded-lg border p-6">
          <h2 className="mb-4 font-medium">신규 거래처 등록</h2>
          <ClientForm industries={industries} marketers={marketers} />
        </section>
      )}
    </div>
  );
}
