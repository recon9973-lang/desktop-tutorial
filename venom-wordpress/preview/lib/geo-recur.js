'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · 반복 업무 자동 생성
//   설계: docs/plans/geo-ops-os-design.md §7(주간 운영: 월요일 이번주 업무 자동 생성)
//   recurrenceRule 이 있는 Task(=반복 시드)를 매 주기(period)마다 1건씩 새로 인스턴스화.
//   중복 방지: 같은 (templateId|title, clientId, period) 인스턴스가 이미 있으면 생성 안 함.
//   순수 함수 → 오프라인 단위 테스트.
// ─────────────────────────────────────────────────────────────────────────

function seedKey(t) { return (t.clientId || '') + '|' + (t.templateId || t.title || '') + '|' + (t.channelType || ''); }

// tasks 중 recurrenceRule 있는 시드에 대해, 이번 period 인스턴스가 없으면 새 Task 생성
// 반환: 새로 만들 Task[] (status='thisweek', period 태그)
function dueRecurrences(tasks, period) {
  if (!period) return [];
  const all = tasks || [];
  // 이번 period 에 이미 존재하는 인스턴스의 키 집합
  const existing = new Set(all.filter((t) => t.period === period).map(seedKey));
  const seeds = all.filter((t) => t.recurrenceRule && t.recurrenceRule !== 'none');
  // 시드 자체는 period 태그가 없어야(원본). period 태그가 있으면 그건 인스턴스로 간주.
  const out = [];
  const seen = new Set();
  seeds.forEach((s) => {
    const k = seedKey(s);
    if (seen.has(k) || existing.has(k)) return; // 중복 시드/이미 생성됨
    seen.add(k);
    out.push({
      clientId: s.clientId,
      channelType: s.channelType || null,
      templateId: s.templateId || null,
      taskType: s.taskType || s.templateId || null,
      title: s.title,
      automationLevel: s.automationLevel || 'D',
      status: 'thisweek',
      approvalStatus: s.automationLevel === 'B' ? 'pending' : 'none',
      recurrenceRule: s.recurrenceRule,
      period,
      guard: s.guard || null,
    });
  });
  return out;
}

module.exports = { seedKey, dueRecurrences };
