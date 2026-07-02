// 목표 경로: src/domain/finance-rules.ts
//
// 청구 상태 계산 (순수 함수). actions/finance.ts 가 이 함수를 import 하도록 정리 권장.
import { BillingStatus } from "@/domain/types";

/**
 * issued 대비 paid + 마감일로 청구 상태 계산.
 * - paid<=0: 마감 경과면 OVERDUE, 아니면 UNPAID
 * - 0<paid<issued: 마감 경과면 OVERDUE, 아니면 PARTIALLY_PAID
 * - paid>=issued: PAID
 */
export function computeBillingStatus(
  issued: number,
  paid: number,
  dueDate: Date | null,
  today: Date
): BillingStatus {
  const overdue = dueDate != null && dueDate < today;
  if (paid <= 0) return overdue ? BillingStatus.OVERDUE : BillingStatus.UNPAID;
  if (paid < issued) return overdue ? BillingStatus.OVERDUE : BillingStatus.PARTIALLY_PAID;
  return BillingStatus.PAID;
}
