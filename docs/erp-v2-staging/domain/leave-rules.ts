// 목표 경로: src/domain/leave-rules.ts
//
// 휴가 소요일수 계산 (순수 함수). actions/leave.ts 가 import 하도록 정리 권장.
import { LeaveType } from "@/domain/types";

/** 반차=0.5, 그 외=시작~종료 포함 일수. */
export function leaveDays(type: LeaveType, start: Date, end: Date): number {
  if (type === LeaveType.HALF_DAY_AM || type === LeaveType.HALF_DAY_PM) return 0.5;
  const ms = +new Date(end.toDateString()) - +new Date(start.toDateString());
  return Math.floor(ms / 86400000) + 1;
}

/** 잔여 연차 = 부여 + 이월 - 사용. */
export function remainingLeave(annualDays: number, carryOverDays: number, usedDays: number): number {
  return annualDays + carryOverDays - usedDays;
}
