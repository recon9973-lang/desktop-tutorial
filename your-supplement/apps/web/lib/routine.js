// 내 루틴 — 복용 기록·리마인더 상태 (localStorage 우선, 키/계정 없이 동작)
// 데이터 모델:
//   items:     [{ id, name, slots:['morning'|'evening'], addedAt }]
//   checks:    { 'YYYY-MM-DD': { 'id|slot': true } }
//   reminders: { enabled, morning:'HH:MM', evening:'HH:MM' }

const KEY = 'ys-routine';

const DEFAULT = () => ({
  items: [],
  checks: {},
  checkins: {}, // { 'YYYY-MM-DD': 1..5 } 일일 컨디션
  reminders: { enabled: false, morning: '09:00', evening: '21:00' },
});

// 복용 유형별 재점검 권장 간격(일). continuous는 점검 없음.
const REVIEW_DAYS = { monitor: 90, cyclic: 56 };

function parseKey(k) {
  const [y, m, d] = k.split('-').map(Number);
  return new Date(y, m - 1, d);
}
export function daysSince(fromKey, toKey = dateKey()) {
  const ms = parseKey(toKey).getTime() - parseKey(fromKey).getTime();
  return Math.floor(ms / 86400000);
}

export function dateKey(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function loadRoutine() {
  if (typeof window === 'undefined') return DEFAULT();
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return DEFAULT();
    return { ...DEFAULT(), ...JSON.parse(raw) };
  } catch {
    return DEFAULT();
  }
}

export function saveRoutine(state) {
  if (typeof window === 'undefined') return;
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {}
}

// 추천/검색 결과 → 루틴에 추가(중복 id는 슬롯 합치고 갱신)
export function addItems(state, newItems) {
  const items = [...state.items];
  for (const ni of newItems) {
    const slots = (ni.slots && ni.slots.length ? ni.slots : ['morning']);
    const ex = items.find((it) => it.id === ni.id);
    if (ex) {
      ex.slots = [...new Set([...ex.slots, ...slots])];
      if (ni.name) ex.name = ni.name;
      if (ni.duration_type) ex.duration_type = ni.duration_type;
    } else {
      items.push({ id: ni.id, name: ni.name, slots, addedAt: dateKey(), duration_type: ni.duration_type || 'continuous' });
    }
  }
  return { ...state, items };
}

export function removeItem(state, id) {
  return { ...state, items: state.items.filter((it) => it.id !== id) };
}

const ckey = (id, slot) => `${id}|${slot}`;

export function isChecked(state, id, slot, dk = dateKey()) {
  return !!state.checks?.[dk]?.[ckey(id, slot)];
}

export function toggleCheck(state, id, slot, dk = dateKey()) {
  const checks = { ...(state.checks || {}) };
  const day = { ...(checks[dk] || {}) };
  const k = ckey(id, slot);
  if (day[k]) delete day[k]; else day[k] = true;
  checks[dk] = day;
  return { ...state, checks };
}

// 하루가 '완료'인가 = 모든 아이템의 모든 슬롯이 체크됨(아이템 있을 때만)
function isDayComplete(state, dk) {
  if (!state.items.length) return false;
  for (const it of state.items) {
    for (const slot of it.slots) {
      if (!state.checks?.[dk]?.[ckey(it.id, slot)]) return false;
    }
  }
  return true;
}

// 연속 복용일 — 오늘부터 거꾸로 '완료'인 날을 셈.
// 오늘이 아직 미완료면 어제까지의 연속을 보여줌(오늘은 진행 중).
export function computeStreak(state) {
  if (!state.items.length) return 0;
  let streak = 0;
  const d = new Date();
  // 오늘이 완료면 오늘 포함, 아니면 어제부터
  if (!isDayComplete(state, dateKey(d))) d.setDate(d.getDate() - 1);
  for (let i = 0; i < 400; i++) {
    if (isDayComplete(state, dateKey(d))) { streak++; d.setDate(d.getDate() - 1); }
    else break;
  }
  return streak;
}

// 오늘의 진행도 { done, total } — 슬롯 단위
export function todayProgress(state, dk = dateKey()) {
  let total = 0, done = 0;
  for (const it of state.items) {
    for (const slot of it.slots) {
      total++;
      if (state.checks?.[dk]?.[ckey(it.id, slot)]) done++;
    }
  }
  return { done, total };
}

// ── 컨디션 체크인 ──
export function setCheckin(state, score, dk = dateKey()) {
  const checkins = { ...(state.checkins || {}) };
  if (checkins[dk] === score) delete checkins[dk]; else checkins[dk] = score;
  return { ...state, checkins };
}
export function getCheckin(state, dk = dateKey()) {
  return state.checkins?.[dk] ?? null;
}
// 최근 N일 [{ date, score|null }] (과거→오늘)
export function recentCheckins(state, days = 14) {
  const out = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const k = dateKey(d);
    out.push({ date: k, score: state.checkins?.[k] ?? null });
  }
  return out;
}

// ── 재점검(점검 시기) ──
// monitor(90일)/cyclic(56일) 경과 아이템을 점검 대상으로.
export function reviewDue(state, todayKey = dateKey()) {
  return state.items
    .map((it) => {
      const need = REVIEW_DAYS[it.duration_type];
      if (!need) return null;
      const since = daysSince(it.addedAt, todayKey);
      return since >= need ? { ...it, sinceDays: since, needDays: need } : null;
    })
    .filter(Boolean);
}

// 슬롯별 오늘 할 일 [{ slot, items:[{id,name,checked}] }]
export function todayBySlot(state, dk = dateKey()) {
  const slots = ['morning', 'evening'];
  return slots
    .map((slot) => ({
      slot,
      items: state.items
        .filter((it) => it.slots.includes(slot))
        .map((it) => ({ id: it.id, name: it.name, checked: isChecked(state, it.id, slot, dk) })),
    }))
    .filter((g) => g.items.length);
}
