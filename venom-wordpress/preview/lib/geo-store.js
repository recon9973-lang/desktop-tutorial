'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · 엔티티 저장 래퍼 (GitHub JSON, 거래처 멀티테넌트)
//   설계: docs/plans/geo-ops-os-design.md §1.1
//   컬렉션마다 content/geo/<파일>.json 에 { <arrayKey>: [ {id, ...}, ... ] } 로 저장.
//   upsert(id 기준)·동시쓰기 충돌(409) 재시도는 github-store 프리미티브 재사용.
//   순수 헬퍼(upsertItem/removeItem/matchFilter/genId)는 백엔드 없이 단위 테스트 가능.
//   백엔드는 주입 가능(_setBackend) — 오프라인 테스트용 인메모리 목 사용.
// ─────────────────────────────────────────────────────────────────────────

const BASE = 'venom-wordpress/preview/content/geo/';

// 컬렉션 → { file, key(배열 필드명) }
const COLLECTIONS = {
  clients:     { file: 'clients.json',        key: 'clients' },
  channels:    { file: 'channels.json',       key: 'channels' },
  tasks:       { file: 'tasks.json',          key: 'tasks' },
  content:     { file: 'content-items.json',  key: 'items' },
  prompts:     { file: 'prompt-sets.json',    key: 'sets' },
  automations: { file: 'automations.json',    key: 'automations' },
};

let backend = require('./github-store'); // 기본: 실제 GitHub 저장
function _setBackend(b) { backend = b; }  // 테스트 주입용

function collMeta(coll) {
  const m = COLLECTIONS[coll];
  if (!m) throw new Error('unknown collection: ' + coll);
  return { path: BASE + m.file, key: m.key };
}

// ── 순수 헬퍼 (백엔드 불필요, 단위 테스트 대상) ──
function genId(prefix) {
  return (prefix || 'geo') + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}
function upsertItem(arr, item) {
  const i = arr.findIndex((x) => x.id === item.id);
  if (i >= 0) { arr[i] = Object.assign({}, arr[i], item); return arr[i]; }
  arr.unshift(item);
  return item;
}
function removeItem(arr, id) {
  const i = arr.findIndex((x) => x.id === id);
  if (i < 0) return false;
  arr.splice(i, 1);
  return true;
}
function matchFilter(item, filter) {
  if (!filter) return true;
  return Object.keys(filter).every((k) => item[k] === filter[k]);
}

// ── 비동기 CRUD ──
async function _readArr(coll) {
  const { path, key } = collMeta(coll);
  const f = await backend.getJsonFile(path, { [key]: [] });
  const content = f && f.content && typeof f.content === 'object' ? f.content : {};
  if (!Array.isArray(content[key])) content[key] = [];
  return { content, key, path };
}

async function list(coll, filter) {
  const { content, key } = await _readArr(coll);
  return content[key].filter((x) => matchFilter(x, filter));
}

async function get(coll, id) {
  const { content, key } = await _readArr(coll);
  return content[key].find((x) => x.id === id) || null;
}

// read-modify-write 를 withConflictRetry 안에서 매 시도마다 재읽기(getFile→putFile) → 동시쓰기 안전
async function _mutate(coll, fn, message) {
  const { path, key } = collMeta(coll);
  return backend.withConflictRetry(async () => {
    const f = await backend.getFile(path); // {sha, content} | null
    const content = f && f.content && typeof f.content === 'object' ? f.content : {};
    if (!Array.isArray(content[key])) content[key] = [];
    const result = fn(content[key], content);
    await backend.putFile(path, content, f ? f.sha : null, message || `chore(geo): update ${coll}`);
    return result;
  });
}

async function upsert(coll, item, idPrefix) {
  if (!item || typeof item !== 'object') throw new Error('item 필요');
  const withId = Object.assign({}, item);
  if (!withId.id) withId.id = genId(idPrefix || coll.slice(0, 4));
  withId.updatedAt = new Date().toISOString();
  return _mutate(coll, (arr) => upsertItem(arr, withId), `chore(geo): upsert ${coll} ${withId.id}`);
}

async function remove(coll, id) {
  return _mutate(coll, (arr) => removeItem(arr, id), `chore(geo): delete ${coll} ${id}`);
}

// 여러 항목을 1커밋으로 upsert (템플릿 인스턴스화 등 — N개 개별 커밋 방지)
async function upsertMany(coll, items, idPrefix) {
  const prepared = (items || []).map((it) => {
    const w = Object.assign({}, it);
    if (!w.id) w.id = genId(idPrefix || coll.slice(0, 4));
    w.updatedAt = new Date().toISOString();
    return w;
  });
  if (!prepared.length) return [];
  await _mutate(coll, (arr) => { prepared.forEach((w) => upsertItem(arr, w)); return prepared.length; },
    `chore(geo): upsertMany ${coll} ${prepared.length}`);
  return prepared;
}

module.exports = {
  COLLECTIONS, collMeta,
  genId, upsertItem, removeItem, matchFilter,
  list, get, upsert, upsertMany, remove,
  _setBackend,
};
