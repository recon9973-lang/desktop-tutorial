'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · 통합 서버리스 엔드포인트 (거래처 멀티테넌트 관리층)
//   설계: docs/plans/geo-ops-os-design.md §3
//   GET  /api/geo-ops?module=dashboard                  → 관제 위젯 집계
//   GET  /api/geo-ops?module=clients&action=list        → 거래처 목록(옵션 필터 ?active=true)
//   GET  /api/geo-ops?module=clients&action=get&id=..   → 단건
//   POST /api/geo-ops?module=clients&action=upsert  body:{client}
//   POST /api/geo-ops?module=clients&action=delete  body:{id}
//   (channels|tasks|content|prompts|automations 동일 패턴)
//   POST /api/geo-ops?module=tasks&action=move      body:{id,to}   → 칸반 상태 이동
//
// 인증: ADMIN_SECRET(Bearer) 설정 시 모든 메서드에 필요(거래처 데이터=고객정보).
//       미설정(로컬/초기)에서는 통과. 콘솔은 admin 로그인 후 시크릿을 헤더로 전달.
// 함수 한도: 신규 함수 1개(모든 CRUD를 module 라우팅으로 흡수).
// ─────────────────────────────────────────────────────────────────────────

const geo = require('../lib/geo-store');
const tpl = require('../lib/geo-templates');

// tasks.json 상태값(칸반) — 이동 검증용
const TASK_STATUS = ['backlog', 'thisweek', 'doing', 'review', 'hold', 'done', 'failed'];

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function authOk(req) {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return true; // 시크릿 미설정 환경에서는 통과
  const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
  return auth === secret;
}

async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  return await new Promise((resolve) => {
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', () => { try { resolve(JSON.parse(raw || '{}')); } catch { resolve({}); } });
    req.on('error', () => resolve({}));
  });
}

// module → geo-store 컬렉션 + 쓰기 payload 필드명
const MODULES = {
  clients:     { coll: 'clients',     field: 'client',     idPrefix: 'cli' },
  channels:    { coll: 'channels',    field: 'channel',    idPrefix: 'chn' },
  tasks:       { coll: 'tasks',       field: 'task',       idPrefix: 'tsk' },
  content:     { coll: 'content',     field: 'item',       idPrefix: 'cnt' },
  prompts:     { coll: 'prompts',     field: 'set',        idPrefix: 'set' },
  automations: { coll: 'automations', field: 'automation', idPrefix: 'atm' },
};

// GET ?필터를 컬렉션 필드로 변환 (문자열/boolean 정규화)
function queryFilter(req) {
  const f = {};
  if (req.query.clientId) f.clientId = String(req.query.clientId);
  if (req.query.channelType) f.channelType = String(req.query.channelType);
  if (req.query.status) f.status = String(req.query.status);
  if (req.query.active != null) f.active = req.query.active === 'true' || req.query.active === true;
  return Object.keys(f).length ? f : null;
}

async function handleEntity(req, res, mod) {
  const action = String(req.query.action || (req.method === 'GET' ? 'list' : 'upsert')).toLowerCase();

  if (req.method === 'GET') {
    if (action === 'get') {
      const item = await geo.get(mod.coll, String(req.query.id || ''));
      return res.status(item ? 200 : 404).json({ ok: !!item, data: item || null });
    }
    const items = await geo.list(mod.coll, queryFilter(req));
    return res.status(200).json({ ok: true, count: items.length, data: items });
  }

  // 쓰기(POST) — 인증 필요
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });
  const body = await readBody(req);

  if (action === 'delete') {
    const id = body.id || req.query.id;
    if (!id) return res.status(400).json({ ok: false, error: 'id 필요' });
    const removed = await geo.remove(mod.coll, String(id));
    return res.status(200).json({ ok: true, removed });
  }

  if (action === 'move' && mod.coll === 'tasks') {
    const { id, to } = body;
    if (!id || !TASK_STATUS.includes(to)) return res.status(400).json({ ok: false, error: 'id, to(유효 상태) 필요' });
    const task = await geo.get('tasks', String(id));
    if (!task) return res.status(404).json({ ok: false, error: 'task 없음' });
    const saved = await geo.upsert('tasks', Object.assign({}, task, { status: to }));
    return res.status(200).json({ ok: true, data: saved });
  }

  if (action === 'approve' && mod.coll === 'tasks') {
    const { id, decision } = body; // 'approved' | 'rejected'
    if (!id) return res.status(400).json({ ok: false, error: 'id 필요' });
    const task = await geo.get('tasks', String(id));
    if (!task) return res.status(404).json({ ok: false, error: 'task 없음' });
    const approvalStatus = decision === 'rejected' ? 'rejected' : 'approved';
    const status = approvalStatus === 'approved' ? 'thisweek' : 'hold';
    const saved = await geo.upsert('tasks', Object.assign({}, task, { approvalStatus, status }));
    return res.status(200).json({ ok: true, data: saved });
  }

  if (action === 'generate' && mod.coll === 'tasks') {
    const { clientId, templateId } = body;
    if (!clientId || !templateId) return res.status(400).json({ ok: false, error: 'clientId, templateId 필요' });
    const templates = await tpl.loadTemplates();
    const t = templates.find((x) => x.id === templateId);
    if (!t) return res.status(404).json({ ok: false, error: '템플릿 없음: ' + templateId });
    const tasks = tpl.buildTasksFromTemplate(t, String(clientId));
    const created = await geo.upsertMany('tasks', tasks, 'tsk');
    return res.status(200).json({ ok: true, count: created.length, data: created });
  }

  if (action === 'upsert') {
    const item = body[mod.field] || body.item || body;
    if (!item || typeof item !== 'object') return res.status(400).json({ ok: false, error: mod.field + ' 필요' });
    const saved = await geo.upsert(mod.coll, item, mod.idPrefix);
    return res.status(200).json({ ok: true, data: saved });
  }

  return res.status(400).json({ ok: false, error: 'unknown action: ' + action });
}

// ── 관제 대시보드 집계 (설계 §2.1) ──
async function handleDashboard(res) {
  const [clients, channels, tasks, autos] = await Promise.all([
    geo.list('clients'), geo.list('channels'), geo.list('tasks'), geo.list('automations'),
  ]);
  const byStage = {};
  clients.forEach((c) => { byStage[c.lifecycleStage || '미지정'] = (byStage[c.lifecycleStage || '미지정'] || 0) + 1; });
  const risks = channels.filter((ch) => ['오류', '미연결', 'high', '높음'].includes(ch.healthStatus) || ch.riskLevel === 'high');
  const summary = {
    clientsTotal: clients.length,
    clientsActive: clients.filter((c) => c.active).length,
    lifecycleBreakdown: byStage,
    channelsTotal: channels.length,
    tasksApprovalWaiting: tasks.filter((t) => t.approvalStatus === 'pending' || t.status === 'review').length,
    tasksDueThisWeek: tasks.filter((t) => t.status === 'thisweek').length,
    tasksFailed: tasks.filter((t) => t.status === 'failed').length,
    automationsFailed: autos.filter((a) => a.status === 'error' || a.lastResult === 'error').length,
    riskCount: risks.length,
    risks: risks.slice(0, 20).map((r) => ({ clientId: r.clientId, channelType: r.channelType, healthStatus: r.healthStatus })),
  };
  return res.status(200).json({ ok: true, data: summary });
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  const module = String(req.query.module || '').toLowerCase();
  try {
    if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });
    if (module === 'dashboard') return await handleDashboard(res);
    if (module === 'templates') {
      const templates = await tpl.loadTemplates();
      return res.status(200).json({ ok: true, count: templates.length, data: templates.map((t) => ({ id: t.id, channelType: t.channelType, cap: t.cap, steps: (t.steps || t.variants || []).length })) });
    }
    const mod = MODULES[module];
    if (!mod) return res.status(400).json({ ok: false, error: 'unknown module (dashboard|clients|channels|tasks|content|prompts|automations)' });
    return await handleEntity(req, res, mod);
  } catch (e) {
    return res.status(500).json({ ok: false, error: e.message });
  }
};
