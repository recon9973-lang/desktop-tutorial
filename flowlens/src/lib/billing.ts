import { getPlan } from "./plans";
import type { Prisma, PrismaClient } from "@prisma/client";

// 요금제 변경 시 사이트 보관일 동기화 — 단, 절대 즉시 줄이지 않는다.
//
// 다운그레이드(예: 에이전시 90일 → 무료 14일) 때 보관일을 바로 14일로 낮추면,
// 자동 정리 크론이 90일치 데이터를 갑자기 삭제한다. 이건 유료 고객에게 사고다.
// 그래서 "필요보다 짧은 사이트만 새 요금제 기준으로 올리고", 이미 더 긴 사이트는 건드리지 않는다.
// (보관 축소는 결제주기가 끝나는 시점에 안내 후 처리 — 토스 결제 연동과 함께. docs/08 정책 참조)
//
// tx(트랜잭션)와 일반 prisma 클라이언트 모두에서 호출 가능하도록 타입을 느슨하게 받는다.
type Db = PrismaClient | Prisma.TransactionClient;

export async function syncRetentionForPlan(db: Db, agencyId: string, planKey: string): Promise<void> {
  const plan = getPlan(planKey);
  const clients = await db.client.findMany({ where: { agencyId }, select: { id: true } });
  const clientIds = clients.map((c) => c.id);
  if (!clientIds.length) return;
  // retentionDays < 새 기준인 사이트만 올린다. 이보다 긴 사이트는 그대로 → 데이터 삭제 없음.
  await db.site.updateMany({
    where: { clientId: { in: clientIds }, retentionDays: { lt: plan.retentionDays } },
    data: { retentionDays: plan.retentionDays },
  });
}
