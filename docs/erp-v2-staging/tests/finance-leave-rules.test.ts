// 목표 경로: tests/domain/finance-leave-rules.test.ts
import { describe, it, expect } from "vitest";
import { BillingStatus, LeaveType } from "@/domain/types";
import { computeBillingStatus } from "@/domain/finance-rules";
import { leaveDays, remainingLeave } from "@/domain/leave-rules";

const today = new Date("2026-07-01");
const past = new Date("2026-06-01");
const future = new Date("2026-08-01");

describe("computeBillingStatus", () => {
  it("미입금(마감 전) → UNPAID", () => {
    expect(computeBillingStatus(1000, 0, future, today)).toBe(BillingStatus.UNPAID);
  });
  it("미입금(마감 경과) → OVERDUE", () => {
    expect(computeBillingStatus(1000, 0, past, today)).toBe(BillingStatus.OVERDUE);
  });
  it("부분입금(마감 전) → PARTIALLY_PAID", () => {
    expect(computeBillingStatus(1000, 400, future, today)).toBe(BillingStatus.PARTIALLY_PAID);
  });
  it("부분입금(마감 경과) → OVERDUE", () => {
    expect(computeBillingStatus(1000, 400, past, today)).toBe(BillingStatus.OVERDUE);
  });
  it("완납 → PAID", () => {
    expect(computeBillingStatus(1000, 1000, past, today)).toBe(BillingStatus.PAID);
    expect(computeBillingStatus(1000, 1200, null, today)).toBe(BillingStatus.PAID);
  });
});

describe("leaveDays / remainingLeave", () => {
  it("반차는 0.5일", () => {
    expect(leaveDays(LeaveType.HALF_DAY_AM, today, today)).toBe(0.5);
    expect(leaveDays(LeaveType.HALF_DAY_PM, today, today)).toBe(0.5);
  });
  it("연차 당일=1일, 3일범위=3일", () => {
    expect(leaveDays(LeaveType.ANNUAL, new Date("2026-07-01"), new Date("2026-07-01"))).toBe(1);
    expect(leaveDays(LeaveType.ANNUAL, new Date("2026-07-01"), new Date("2026-07-03"))).toBe(3);
  });
  it("잔여 연차 = 부여+이월-사용", () => {
    expect(remainingLeave(15, 3, 5)).toBe(13);
  });
});
