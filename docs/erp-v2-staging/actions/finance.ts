// 목표 경로: src/server/actions/finance.ts
//
// 거래처 청구/입금 + 은행내역 반자동 대사.
// 권한: 마케터 열람 불가(재무 격리). ADMIN=범위 내, SUPER_ADMIN=전체.
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role } from "@/domain/types";
import { assertCanAccessClient } from "@/domain/access-control";
import { db } from "@/server/db";
import {
  getAdminScopes,
  recordAudit,
  requestMeta,
  requireUser,
  runAction,
  type ActionResult
} from "@/server/actions/_helpers";
import type { CurrentUser } from "@/server/session";

/** 재무 접근: 마케터 전면 차단. 관리자는 거래처 범위 검증. */
async function assertFinanceAccess(user: CurrentUser, clientId: string, assignedMarketerId: string | null) {
  if (user.role === Role.MARKETER) throw new Error("FORBIDDEN"); // 재무 열람 불가
  const scopes = await getAdminScopes(user);
  assertCanAccessClient(user, clientId, scopes, assignedMarketerId);
}

/** 청구 상태 계산 (issued 대비 paid). 연체는 dueDate 경과 + 미완납 시. */
function computeBillingStatus(issued: number, paid: number, dueDate: Date | null, today: Date): string {
  if (paid <= 0) {
    return dueDate && dueDate < today ? "OVERDUE" : "UNPAID";
  }
  if (paid < issued) {
    return dueDate && dueDate < today ? "OVERDUE" : "PARTIALLY_PAID";
  }
  return "PAID";
}

// ── 청구 생성 ─────────────────────────────────
const billingSchema = z.object({
  clientId: z.string().min(1),
  billingMonth: z.string().regex(/^\d{4}-\d{2}$/), // YYYY-MM
  contractAmount: z.coerce.number().nonnegative(),
  issuedAmount: z.coerce.number().nonnegative().optional(),
  dueDate: z.coerce.date().optional().nullable(),
  invoiceNumber: z.string().trim().optional().nullable()
});

export async function createBilling(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const p = billingSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    const client = await db.client.findUnique({ where: { id: d.clientId } });
    if (!client) throw new Error("NOT_FOUND");
    await assertFinanceAccess(user, d.clientId, client.assignedMarketerId);

    const issued = d.issuedAmount ?? d.contractAmount;
    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const rec = await tx.billingRecord.create({
        data: {
          clientId: d.clientId,
          billingMonth: d.billingMonth,
          contractAmount: d.contractAmount,
          issuedAmount: issued,
          paidAmount: 0,
          status: "ISSUED",
          invoiceNumber: d.invoiceNumber || null,
          dueDate: d.dueDate ?? null
        }
      });
      await recordAudit(tx, {
        actorId: user.id, action: "billing.create",
        targetType: "BillingRecord", targetId: rec.id, afterState: rec, ...meta
      });
      return rec;
    });
    revalidatePath("/finance");
    revalidatePath(`/clients/${d.clientId}`);
    return { id: saved.id };
  });
}

// ── 입금 기록 (수기) ──────────────────────────
const paymentSchema = z.object({
  billingRecordId: z.string().min(1),
  amount: z.coerce.number().positive(),
  method: z.enum(["BANK_TRANSFER", "CARD", "CASH", "VIRTUAL_ACCOUNT", "OTHER"]).optional(),
  receivedAt: z.coerce.date().optional().nullable()
});

export async function recordPayment(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const p = paymentSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    const billing = await db.billingRecord.findUnique({
      where: { id: d.billingRecordId },
      include: { client: { select: { id: true, assignedMarketerId: true } } }
    });
    if (!billing) throw new Error("NOT_FOUND");
    await assertFinanceAccess(user, billing.client.id, billing.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.paymentRecord.create({
        data: {
          billingRecordId: d.billingRecordId,
          amount: d.amount,
          method: d.method ?? "BANK_TRANSFER",
          provider: "MANUAL",
          receivedAt: d.receivedAt ?? new Date()
        }
      });
      const newPaid = Number(billing.paidAmount) + d.amount;
      const status = computeBillingStatus(Number(billing.issuedAmount), newPaid, billing.dueDate, new Date());
      const after = await tx.billingRecord.update({
        where: { id: d.billingRecordId },
        data: { paidAmount: newPaid, status: status as never }
      });
      await recordAudit(tx, {
        actorId: user.id, action: "payment.record",
        targetType: "BillingRecord", targetId: d.billingRecordId,
        beforeState: { paidAmount: billing.paidAmount, status: billing.status },
        afterState: { paidAmount: after.paidAmount, status: after.status, addedAmount: d.amount }, ...meta
      });
    });
    revalidatePath("/finance");
  });
}

// ── 은행내역 임포트 (반자동 대사 1단계) ────────
const importSchema = z.object({
  rows: z.array(z.object({
    txDate: z.coerce.date(),
    amount: z.coerce.number(),
    counterpartyName: z.string().trim().optional().nullable(),
    memo: z.string().trim().optional().nullable()
  })).min(1)
});

export async function importBankTransactions(input: unknown): Promise<ActionResult<{ count: number }>> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role === Role.MARKETER) throw new Error("FORBIDDEN");
    const p = importSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");

    const meta = await requestMeta();
    const created = await db.$transaction(async (tx) => {
      const res = await tx.bankTransaction.createMany({
        data: p.data.rows.map((r) => ({
          txDate: r.txDate,
          amount: r.amount,
          counterpartyName: r.counterpartyName || null,
          memo: r.memo || null,
          matchStatus: "UNMATCHED"
        }))
      });
      await recordAudit(tx, {
        actorId: user.id, action: "bank.import",
        targetType: "BankTransaction", targetId: "bulk",
        afterState: { count: res.count }, ...meta
      });
      return res.count;
    });
    revalidatePath("/finance");
    return { count: created };
  });
}

/** 후보 매칭 제안: 미매칭 은행내역 × 미납 청구건을 금액/입금자명으로 매칭 후보 산출(조회). */
export async function suggestBankMatches(): Promise<ActionResult<Array<{ bankTxId: string; billingId: string; score: number }>>> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role === Role.MARKETER) throw new Error("FORBIDDEN");

    const [txs, bills] = await Promise.all([
      db.bankTransaction.findMany({ where: { matchStatus: "UNMATCHED" } }),
      db.billingRecord.findMany({
        where: { status: { in: ["ISSUED", "UNPAID", "PARTIALLY_PAID", "OVERDUE"] } },
        include: { client: { select: { name: true } } }
      })
    ]);

    const suggestions: Array<{ bankTxId: string; billingId: string; score: number }> = [];
    for (const tx of txs) {
      for (const b of bills) {
        const remaining = Number(b.issuedAmount) - Number(b.paidAmount);
        let score = 0;
        if (Number(tx.amount) === remaining) score += 2; // 금액 정확 일치
        else if (Math.abs(Number(tx.amount) - remaining) < 1) score += 1;
        if (tx.counterpartyName && b.client?.name && tx.counterpartyName.includes(b.client.name)) score += 2;
        if (score >= 2) suggestions.push({ bankTxId: tx.id, billingId: b.id, score });
      }
    }
    suggestions.sort((a, b) => b.score - a.score);
    return suggestions;
  });
}

/** 대사 확정: 은행내역 → 청구건 매칭 + 입금기록 생성 + 상태 갱신. */
export async function confirmBankMatch(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role === Role.MARKETER) throw new Error("FORBIDDEN");
    const p = z.object({ bankTxId: z.string().min(1), billingId: z.string().min(1) }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const { bankTxId, billingId } = p.data;

    const [tx, billing] = await Promise.all([
      db.bankTransaction.findUnique({ where: { id: bankTxId } }),
      db.billingRecord.findUnique({
        where: { id: billingId },
        include: { client: { select: { id: true, assignedMarketerId: true } } }
      })
    ]);
    if (!tx || !billing) throw new Error("NOT_FOUND");
    await assertFinanceAccess(user, billing.client.id, billing.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (trx) => {
      await trx.paymentRecord.create({
        data: {
          billingRecordId: billingId,
          amount: Number(tx.amount),
          method: "BANK_TRANSFER",
          provider: "MANUAL",
          transactionId: tx.id,
          receivedAt: tx.txDate
        }
      });
      const newPaid = Number(billing.paidAmount) + Number(tx.amount);
      const status = computeBillingStatus(Number(billing.issuedAmount), newPaid, billing.dueDate, new Date());
      await trx.billingRecord.update({ where: { id: billingId }, data: { paidAmount: newPaid, status: status as never } });
      await trx.bankTransaction.update({ where: { id: bankTxId }, data: { matchStatus: "CONFIRMED", matchedBillingId: billingId } });
      await recordAudit(trx, {
        actorId: user.id, action: "bank.match.confirm",
        targetType: "BillingRecord", targetId: billingId,
        afterState: { bankTxId, amount: Number(tx.amount), status }, ...meta
      });
    });
    revalidatePath("/finance");
  });
}
