'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GrowthOps · 통합 서버리스 엔드포인트 (Vercel 12-함수 한도 절감)
//   GET  /api/growthops?module=linkhealth          → 내부링크 헬스(M2/M3): 고아글·평균링크
//   GET  /api/growthops?module=outreach&action=list → 아웃리치 연락처 목록(M4)
//   GET  /api/growthops?module=outreach&action=remind → 오늘 할 일(리마인더)
//   POST /api/growthops?module=outreach&action=upsert  body:{contact}
//   POST /api/growthops?module=outreach&action=transition body:{id,to,note}
//   POST /api/growthops?module=outreach&action=delete  body:{id}
//   POST /api/growthops?module=snapshot               → 일별 SEO 스냅샷 저장(cron용)
// 쓰기(POST)는 ADMIN_SECRET(Bearer) 필요. 읽기(GET)는 공개.
// 기존 자산 재사용: github-store(영속화), internal-linker(M2), outreach(M4 로직).
// ─────────────────────────────────────────────────────────────────────────

const store = require('../lib/github-store');
const linker = require('../lib/internal-linker');
const O = require('../lib/outreach');
const TC = require('../lib/topic-cluster');
const { fetchPsi } = require('../lib/psi');
const GSC = require('../lib/search-console');

const OUTREACH_PATH = 'venom-wordpress/preview/content/outreach.json';
const CLUSTERS_PATH = 'venom-wordpress/preview/content/clusters.json';

// 모니터링 대상 핵심 URL(쉼표구분 env). 미설정이면 사이트 루트만.
function monitorUrls() {
  const raw = process.env.GROWTHOPS_MONITOR_URLS || process.env.SITE_URL || '';
  return raw.split(',').map((s) => s.trim()).filter((s) => /^https?:\/\//.test(s)).slice(0, 5);
}

// KST 기준 YYYY-MM-DD (offsetDays 전)
function ymdKST(offsetDays) {
  const ms = Date.now() + 9 * 3600 * 1000 - (offsetDays || 0) * 86400000;
  return new Date(ms).toISOString().slice(0, 10);
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function authOk(req) {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return true; // 시크릿 미설정 환경(로컬/초기)에서는 통과
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

async function loadOutreach() {
  const f = await store.getJsonFile(OUTREACH_PATH, { contacts: [] });
  const content = f.content && Array.isArray(f.content.contacts) ? f.content : { contacts: [] };
  return content;
}

async function saveOutreach(content, message) {
  await store.saveJsonFile(OUTREACH_PATH, content, message || 'chore(growthops): update outreach');
}

// ── M2/M3: 내부링크 헬스 ──
async function handleLinkHealth(res) {
  const { posts } = await store.getPosts();
  let clusters = null;
  try { clusters = (await store.getJsonFile('venom-wordpress/preview/content/clusters.json', null)).content; } catch {}
  const r = linker.suggestLinks(posts, { perPost: 4, clusters });
  return res.status(200).json({ ok: true, ...r.stats, orphans: r.orphans });
}

// ── M4: 아웃리치 ──
async function handleOutreach(req, res, action) {
  if (req.method === 'GET') {
    const data = await loadOutreach();
    if (action === 'remind') {
      return res.status(200).json({ ok: true, today: ymdKST(), due: O.dueReminders(data.contacts, ymdKST()) });
    }
    // 기본: list (+요약)
    return res.status(200).json({ ok: true, summary: O.summary(data.contacts), contacts: data.contacts });
  }

  if (req.method === 'POST') {
    if (!authOk(req)) return res.status(401).json({ ok: false, error: 'ADMIN_SECRET 필요' });
    const body = await readBody(req);
    const data = await loadOutreach();

    if (action === 'upsert') {
      const v = O.validateContact(body.contact || body);
      if (!v.ok) return res.status(400).json({ ok: false, errors: v.errors });
      data.contacts = O.upsert(data.contacts, v.contact);
      await saveOutreach(data, `chore(growthops): upsert outreach "${v.contact.name}"`);
      return res.status(200).json({ ok: true, contact: v.contact });
    }

    if (action === 'transition') {
      const { id, to, note } = body;
      const c = data.contacts.find((x) => x.id === id);
      if (!c) return res.status(404).json({ ok: false, error: '연락처 없음' });
      const next = O.transition(c, to, note);
      data.contacts = O.upsert(data.contacts, next);
      await saveOutreach(data, `chore(growthops): ${id} → ${to}`);
      return res.status(200).json({ ok: true, contact: next });
    }

    if (action === 'delete') {
      const { id } = body;
      const r = O.remove(data.contacts, id);
      if (!r.removed) return res.status(404).json({ ok: false, error: '연락처 없음' });
      data.contacts = r.contacts;
      await saveOutreach(data, `chore(growthops): delete ${id}`);
      return res.status(200).json({ ok: true });
    }

    if (action === 'draft') {
      // 적법 제안 메일 초안 생성(OpenAI). 저장하지 않음.
      const c = (body.id && data.contacts.find((x) => x.id === body.id)) || body.contact;
      if (!c || !c.name) return res.status(400).json({ ok: false, error: '연락처(name) 필요' });
      try {
        const { chatComplete } = require('../lib/openai-client');
        const out = await chatComplete(
          '당신은 적법한 화이트햇 디지털 PR·아웃리치 전문가입니다. 링크 구매·교환·스팸을 절대 제안하지 않고, 가치 중심의 정중한 제안만 작성합니다.',
          O.buildOutreachPrompt(c),
          { max_tokens: 800, temperature: 0.6 }
        );
        return res.status(200).json({ ok: true, draft: out.text, usage: out.usage });
      } catch (e) {
        return res.status(500).json({ ok: false, error: String((e && e.message) || e) });
      }
    }

    return res.status(400).json({ ok: false, error: '알 수 없는 action' });
  }

  return res.status(405).json({ ok: false, error: 'GET/POST only' });
}

// ── M1: 토픽 클러스터 ──
async function loadClusters() {
  const f = await store.getJsonFile(CLUSTERS_PATH, { clusters: [] });
  return (f.content && Array.isArray(f.content.clusters)) ? f.content : { clusters: [] };
}

async function handleCluster(req, res, action) {
  if (req.method === 'GET') {
    // list: 라이브 글을 빈칸에 매칭한 최신 상태 + 요약 반환
    const obj = await loadClusters();
    const { posts } = await store.getPosts();
    const merged = TC.mergePostsIntoClusters(obj, posts);
    return res.status(200).json({ ok: true, summary: TC.summary(merged), clusters: merged.clusters });
  }

  if (req.method === 'POST') {
    if (!authOk(req)) return res.status(401).json({ ok: false, error: 'ADMIN_SECRET 필요' });
    const body = await readBody(req);
    const obj = await loadClusters();

    if (action === 'build') {
      const { category, region = '', pillar, size } = body;
      if (!category || !pillar) return res.status(400).json({ ok: false, error: 'category, pillar 필수' });
      let related = Array.isArray(body.related) ? body.related : [];
      let questions = Array.isArray(body.questions) ? body.questions : [];
      // 리서치 키워드 미제공 시 실데이터로 자동 수집(네트워크 실패해도 빌드는 진행)
      if (!related.length && !questions.length) {
        try {
          const { researchKeywords } = require('../lib/keyword-research');
          const r = await researchKeywords(pillar, { region });
          related = r.related || []; questions = r.questions || [];
        } catch (e) { /* 무시: 빈 클러스터로 생성 */ }
      }
      const cluster = TC.buildCluster({ category, region, pillar, related, questions, size: size || 6 });
      const next = TC.upsertCluster(obj, cluster);
      await store.saveJsonFile(CLUSTERS_PATH, next, `chore(growthops): build cluster ${cluster.id}`);
      return res.status(200).json({ ok: true, cluster, summary: TC.summary(next) });
    }

    if (action === 'sync') {
      const { posts } = await store.getPosts();
      const merged = TC.mergePostsIntoClusters(obj, posts);
      await store.saveJsonFile(CLUSTERS_PATH, merged, 'chore(growthops): sync clusters with posts');
      return res.status(200).json({ ok: true, summary: TC.summary(merged), clusters: merged.clusters });
    }

    return res.status(400).json({ ok: false, error: '알 수 없는 action' });
  }

  return res.status(405).json({ ok: false, error: 'GET/POST only' });
}

// ── M3+: Search Console 실측 ──
async function handleGsc(req, res) {
  if (!GSC.isConfigured()) {
    return res.status(200).json({ ok: true, configured: false, note: 'GSC 미설정: GSC_CLIENT_EMAIL/GSC_PRIVATE_KEY(또는 GSC_SERVICE_ACCOUNT_JSON) + GSC_SITE_URL 필요' });
  }
  const q = req.query || {};
  const type = q.type || 'summary';
  // GSC 데이터는 2~3일 지연 → endDate=오늘-3, startDate=오늘-30
  const endDate = ymdKST(3);
  const startDate = ymdKST(30);
  const limit = Math.min(parseInt(q.limit, 10) || 10, 100);

  if (type === 'query' || type === 'page') {
    const r = await GSC.querySearchAnalytics({ startDate, endDate, dimensions: [type], rowLimit: limit });
    if (!r.ok) return res.status(200).json({ ok: true, configured: true, error: r.reason });
    return res.status(200).json({ ok: true, configured: true, range: { startDate, endDate }, rows: r.rows, totals: r.totals });
  }

  // summary: 총계 + 상위 쿼리 + 상위 페이지
  const [tot, queries, pages] = await Promise.all([
    GSC.querySearchAnalytics({ startDate, endDate, dimensions: [], rowLimit: 1 }),
    GSC.querySearchAnalytics({ startDate, endDate, dimensions: ['query'], rowLimit: limit }),
    GSC.querySearchAnalytics({ startDate, endDate, dimensions: ['page'], rowLimit: limit }),
  ]);
  if (!tot.ok) return res.status(200).json({ ok: true, configured: true, error: tot.reason });
  return res.status(200).json({
    ok: true, configured: true, range: { startDate, endDate },
    totals: tot.totals,
    topQueries: queries.ok ? queries.rows : [],
    topPages: pages.ok ? pages.rows : [],
  });
}

// ── M3: 인덱싱 준비도(발행물 기반 추정) ──
async function handleIndexing(res) {
  const { posts } = await store.getPosts();
  const pub = (posts || []).filter((p) => p && p.publishable !== false &&
    (!p.status || !/draft|임시|hidden|trash|삭제|review|검수/i.test(p.status)));
  const missingSlug = pub.filter((p) => !p.slug).length;
  const noImage = pub.filter((p) => !(p.images && p.images.length) && !/<img/i.test(p.html || '')).length;
  const noMeta = pub.filter((p) => !p.metaDesc).length;
  const ready = pub.filter((p) => p.slug && p.metaDesc).length;
  return res.status(200).json({
    ok: true,
    published: pub.length,
    ready,
    readiness: { missingSlug, noImage, noMeta },
    note: '발행물 기반 인덱싱 준비도 추정입니다. 실측 색인/노출/클릭은 Search Console API 연동 시 제공됩니다.',
  });
}

// ── M3: Core Web Vitals(PSI) ──
async function handleCwv(req, res) {
  const q = req.query || {};
  const urls = q.url ? [q.url] : monitorUrls();
  if (!urls.length) return res.status(200).json({ ok: true, results: [], note: 'GROWTHOPS_MONITOR_URLS/SITE_URL 미설정 또는 url 파라미터 없음' });
  const strategy = q.strategy === 'desktop' ? 'desktop' : 'mobile';
  const results = [];
  for (const u of urls.slice(0, 5)) results.push(await fetchPsi(u, { strategy })); // 순차(타임아웃 여유)
  return res.status(200).json({ ok: true, strategy, results });
}

// ── M3: 일별 스냅샷(cron) — KV 있으면 저장, 없으면 계산만 반환 ──
async function handleSnapshot(req, res) {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'ADMIN_SECRET 필요' });
  const { posts } = await store.getPosts();
  const link = linker.suggestLinks(posts, { perPost: 4 });
  const snap = {
    date: ymdKST(),
    posts: link.stats.posts,
    orphanCount: link.stats.orphanCount,
    orphanRate: link.stats.orphanRate,
    avgLinksPerPost: link.stats.avgLinksPerPost,
  };
  // CWV(PSI) — PSI_KEY 있을 때만, 핵심 URL 최대 3개 순차 측정(타임아웃 여유)
  if (process.env.PSI_KEY) {
    try {
      const cwv = [];
      for (const u of monitorUrls().slice(0, 3)) {
        const r = await fetchPsi(u, { strategy: 'mobile' });
        if (r.ok) cwv.push({ url: r.url, performance: r.scores.performance, seo: r.scores.seo, lcpMs: r.lab.lcpMs, cls: r.lab.cls });
      }
      if (cwv.length) snap.cwv = cwv;
    } catch (e) { /* 무시 */ }
  }
  // 일별 스냅샷을 GitHub에 누적 저장(간단·견고, KV 불필요). 추세 그래프의 데이터 소스.
  let stored = false;
  try {
    const path = 'venom-wordpress/preview/content/seo-snapshots.json';
    const f = await store.getJsonFile(path, { snapshots: [] });
    const arr = (f.content && f.content.snapshots) || [];
    const i = arr.findIndex((s) => s.date === snap.date);
    if (i >= 0) arr[i] = snap; else arr.unshift(snap);
    if (arr.length > 400) arr.length = 400; // 약 13개월 보관
    await store.saveJsonFile(path, { snapshots: arr }, `chore(growthops): snapshot ${snap.date}`);
    stored = true;
  } catch (e) { stored = false; }
  return res.status(200).json({ ok: true, stored, snapshot: snap });
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const q = req.query || {};
  const moduleName = q.module || 'linkhealth';
  const action = q.action || 'list';

  try {
    if (moduleName === 'linkhealth') return await handleLinkHealth(res);
    if (moduleName === 'outreach') return await handleOutreach(req, res, action);
    if (moduleName === 'cluster') return await handleCluster(req, res, action);
    if (moduleName === 'indexing') return await handleIndexing(res);
    if (moduleName === 'gsc') return await handleGsc(req, res);
    if (moduleName === 'cwv') return await handleCwv(req, res);
    if (moduleName === 'snapshot') return await handleSnapshot(req, res);
    return res.status(400).json({ ok: false, error: '알 수 없는 module' });
  } catch (e) {
    return res.status(500).json({ ok: false, error: String((e && e.message) || e) });
  }
};
