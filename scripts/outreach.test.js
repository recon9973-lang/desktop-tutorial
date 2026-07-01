'use strict';

// node scripts/outreach.test.js
const assert = require('assert');
const O = require('../lib/outreach');

let pass = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('  ✓ ' + name); }
  catch (e) { console.error('  ✗ ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const AT = '2026-06-30T00:00:00.000Z';

test('validateContact: name 필수', () => {
  const v = O.validateContact({}, AT);
  assert.strictEqual(v.ok, false);
  assert.ok(v.errors.join().includes('name'));
});

test('validateContact: 정규화 + 기본값 + id 생성', () => {
  const v = O.validateContact({ name: '대구의료신문', site: 'https://x.kr' }, AT);
  assert.ok(v.ok);
  assert.strictEqual(v.contact.type, 'guestpost');
  assert.strictEqual(v.contact.status, 'lead');
  assert.ok(v.contact.id.startsWith('oc_'));
  assert.deepStrictEqual(v.contact.history, []);
});

test('validateContact: 잘못된 site/type/nextAt 거절', () => {
  assert.strictEqual(O.validateContact({ name: 'a', site: 'ftp://x' }, AT).ok, false);
  assert.strictEqual(O.validateContact({ name: 'a', type: 'spam' }, AT).ok, false);
  assert.strictEqual(O.validateContact({ name: 'a', nextAt: '06/30' }, AT).ok, false);
});

test('transition: 이력 기록', () => {
  const { contact } = O.validateContact({ name: 'a' }, AT);
  const t = O.transition(contact, 'contacted', '메일 발송', AT);
  assert.strictEqual(t.status, 'contacted');
  assert.strictEqual(t.history.length, 1);
  assert.strictEqual(t.history[0].from, 'lead');
  assert.strictEqual(t.history[0].to, 'contacted');
});

test('transition: 알 수 없는 status 거절', () => {
  const { contact } = O.validateContact({ name: 'a' }, AT);
  assert.throws(() => O.transition(contact, 'nope', '', AT));
});

test('upsert: 동일 id 교체, 새 id 추가', () => {
  const { contact } = O.validateContact({ name: 'a' }, AT);
  let list = O.upsert([], contact);
  assert.strictEqual(list.length, 1);
  list = O.upsert(list, Object.assign({}, contact, { notes: '수정' }));
  assert.strictEqual(list.length, 1);
  assert.strictEqual(list[0].notes, '수정');
});

test('remove: 존재/부재', () => {
  const { contact } = O.validateContact({ name: 'a' }, AT);
  const list = O.upsert([], contact);
  assert.strictEqual(O.remove(list, contact.id).removed, true);
  assert.strictEqual(O.remove(list, 'zzz').removed, false);
});

test('dueReminders: 오늘 이전/당일 + 종료상태 제외', () => {
  const mk = (over) => Object.assign(O.validateContact({ name: 'a' + Math.floor(over * 1000) }, AT).contact, over);
  const contacts = [
    mk({ nextAt: '2026-06-29', status: 'contacted' }), // due (과거)
    mk({ nextAt: '2026-06-30', status: 'lead' }),       // due (당일)
    mk({ nextAt: '2026-07-05', status: 'lead' }),       // not yet
    mk({ nextAt: '2026-06-01', status: 'archived' }),   // 종료 제외
  ];
  const due = O.dueReminders(contacts, '2026-06-30');
  assert.strictEqual(due.length, 2);
  assert.ok(due[0].nextAt <= due[1].nextAt); // 정렬
});

test('summary: 집계', () => {
  const base = O.validateContact({ name: 'a' }, AT).contact;
  const contacts = [
    Object.assign({}, base, { id: '1', status: 'published', type: 'pr' }),
    Object.assign({}, base, { id: '2', status: 'maintained', type: 'guestpost' }),
    Object.assign({}, base, { id: '3', status: 'archived', type: 'pr' }),
  ];
  const s = O.summary(contacts);
  assert.strictEqual(s.total, 3);
  assert.strictEqual(s.acquired, 2);
  assert.strictEqual(s.active, 2); // archived 1 제외
  assert.strictEqual(s.byType.pr, 2);
});

test('buildOutreachPrompt: 유형 라벨 + 스팸/링크교환 금지 명시', () => {
  const { contact } = O.validateContact({ name: '대구일보', type: 'pr', site: 'https://x.kr', notes: '의료 섹션' }, AT);
  const p = O.buildOutreachPrompt(contact);
  assert.ok(p.includes('대구일보'));
  assert.ok(p.includes('보도자료')); // pr 라벨
  assert.ok(p.includes('링크 구매/교환'));
  assert.ok(p.includes('병원마케팅 베놈'));
});

test('buildOutreachPrompt: 알 수 없는 유형은 협업 제안으로 폴백', () => {
  const p = O.buildOutreachPrompt({ name: 'A', type: 'zzz' });
  assert.ok(p.includes('협업 제안'));
});

console.log(`\n${pass} passed`);
