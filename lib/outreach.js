'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GrowthOps · M4 적법 아웃리치 CRM (순수 로직)
// ─────────────────────────────────────────────────────────────────────────
// 게스트포스팅·디지털 PR·제휴·인터뷰 등 "실제 관계 기반"으로 외부 인용/백링크를
// 확보하는 활동을 추적한다. PBN/링크구매/링크교환 자동화는 다루지 않는다.
//   - 1:1 관계 관리(파이프라인)일 뿐, 대량 메일 발송 기능 없음
//   - 상태 전이 이력을 남겨 추적 가능
// 영속화는 api/growthops.js에서 github-store(content/outreach.json)로 처리.
// 이 파일은 네트워크/IO 없는 순수 함수만 — 단위 테스트 용이.
// ─────────────────────────────────────────────────────────────────────────

const STATUSES = ['lead', 'contacted', 'replied', 'published', 'maintained', 'declined', 'archived'];
const TERMINAL = new Set(['declined', 'archived']);
const TYPES = ['guestpost', 'pr', 'partnership', 'interview', 'resource', 'directory'];

function nowIso(at) { return at || new Date().toISOString(); }
function ymd(d) { return String(d).slice(0, 10); }

// 간단 슬러그 id (Math.random 미사용 — 시간+이름 기반)
function makeId(name, at) {
  const base = (name || 'contact').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 24);
  const stamp = nowIso(at).replace(/[^0-9]/g, '').slice(0, 14);
  return `oc_${base || 'c'}_${stamp}`;
}

function isHttpUrl(u) {
  if (!u) return true; // site는 선택
  try { const x = new URL(u); return x.protocol === 'http:' || x.protocol === 'https:'; }
  catch { return false; }
}

/** 연락처 입력 검증 + 정규화. { ok, errors, contact } */
function validateContact(input, at) {
  const errors = [];
  const c = Object.assign({}, input);
  if (!c.name || !String(c.name).trim()) errors.push('name(매체/담당자명) 필수');
  if (c.type && !TYPES.includes(c.type)) errors.push(`type는 ${TYPES.join('/')} 중 하나`);
  if (c.status && !STATUSES.includes(c.status)) errors.push(`status는 ${STATUSES.join('/')} 중 하나`);
  if (c.site && !isHttpUrl(c.site)) errors.push('site는 http(s) URL이어야 함');
  if (c.nextAt && !/^\d{4}-\d{2}-\d{2}/.test(String(c.nextAt))) errors.push('nextAt은 YYYY-MM-DD');
  if (errors.length) return { ok: false, errors, contact: null };

  c.name = String(c.name).trim();
  c.type = c.type || 'guestpost';
  c.status = c.status || 'lead';
  c.site = c.site || '';
  c.owner = c.owner || '';
  c.email = c.email || '';
  c.notes = c.notes || '';
  c.nextAt = c.nextAt ? ymd(c.nextAt) : '';
  if (!c.id) c.id = makeId(c.name, at);
  if (!Array.isArray(c.history)) c.history = [];
  if (!c.createdAt) c.createdAt = nowIso(at);
  c.updatedAt = nowIso(at);
  return { ok: true, errors: [], contact: c };
}

/** 상태 전이(이력 기록). 모든 전이를 허용하되 기록한다(현실 운영 유연성). */
function transition(contact, toStatus, note, at) {
  if (!STATUSES.includes(toStatus)) throw new Error('알 수 없는 status: ' + toStatus);
  const from = contact.status;
  const next = Object.assign({}, contact, {
    status: toStatus,
    updatedAt: nowIso(at),
    history: (contact.history || []).concat([{ at: nowIso(at), from, to: toStatus, note: note || '' }]),
  });
  return next;
}

/** contacts 배열에 upsert(동일 id 교체, 없으면 추가). 새 배열 반환. */
function upsert(contacts, contact) {
  const list = Array.isArray(contacts) ? contacts.slice() : [];
  const i = list.findIndex((x) => x.id === contact.id);
  if (i >= 0) list[i] = contact; else list.unshift(contact);
  return list;
}

function remove(contacts, id) {
  const list = Array.isArray(contacts) ? contacts : [];
  const out = list.filter((x) => x.id !== id);
  return { contacts: out, removed: out.length !== list.length };
}

/** 오늘(todayYmd) 이전/당일 nextAt이 잡힌, 종료되지 않은 연락처(=할 일). */
function dueReminders(contacts, todayYmd) {
  const today = ymd(todayYmd);
  return (contacts || [])
    .filter((c) => c.nextAt && !TERMINAL.has(c.status) && ymd(c.nextAt) <= today)
    .sort((a, b) => (a.nextAt < b.nextAt ? -1 : 1));
}

/** 상태별/유형별 집계 + 활성 파이프라인 수. */
function summary(contacts) {
  const byStatus = {}; const byType = {};
  for (const s of STATUSES) byStatus[s] = 0;
  for (const t of TYPES) byType[t] = 0;
  let acquired = 0; // published+maintained = 실제 게재 확보
  for (const c of contacts || []) {
    if (byStatus[c.status] != null) byStatus[c.status]++;
    if (byType[c.type] != null) byType[c.type]++;
    if (c.status === 'published' || c.status === 'maintained') acquired++;
  }
  const total = (contacts || []).length;
  const active = total - byStatus.declined - byStatus.archived;
  return { total, active, acquired, byStatus, byType };
}

const TYPE_LABEL = {
  guestpost: '게스트 포스팅(기고) 제안',
  pr: '보도자료·디지털 PR 제안',
  partnership: '콘텐츠 제휴 제안',
  interview: '전문가 인터뷰 요청',
  resource: '리소스 페이지 등재 요청',
  directory: '정식 디렉터리 등재 요청',
};

/** 적법 아웃리치 제안 메일 초안용 프롬프트(순수). 링크구매/교환/스팸은 절대 제안하지 않는다. */
function buildOutreachPrompt(contact, sender) {
  const c = contact || {};
  const label = TYPE_LABEL[c.type] || '협업 제안';
  const from = sender || '병원마케팅 베놈';
  return [
    `아래 매체/담당자에게 보낼 "${label}" 이메일 초안을 한국어로 작성하세요.`,
    '요건:',
    '- 정중하고 간결하게(과장·스팸 금지), 상대 매체의 독자에게 주는 가치를 먼저 제시',
    '- 링크 구매/교환/맞교환을 절대 제안하지 말 것. 양질의 콘텐츠·전문성 제공이 핵심',
    '- 제목 1줄 + 본문 3~5문단 + 간단한 서명',
    `- 발신: ${from}`,
    '',
    `매체/담당자: ${c.name || '-'}`,
    `사이트: ${c.site || '-'}`,
    `제안 유형: ${label}`,
    `참고 메모: ${c.notes || '-'}`,
  ].join('\n');
}

module.exports = {
  STATUSES, TYPES, TERMINAL, TYPE_LABEL,
  validateContact, transition, upsert, remove, dueReminders, summary, makeId, isHttpUrl,
  buildOutreachPrompt,
};
