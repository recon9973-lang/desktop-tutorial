'use strict';

/**
 * 품질 채점 엔드포인트 (LLM-as-Judge, Vercel에서 실행) — "다양한 변수 Q&A에 실제로
 * 맞는 답을 하는가"를 Claude로 표본 채점하고 약점 지도를 만든다.
 *
 *  GET /api/eval-judge?n=12            → 층화 표본 n문항 채점 후 약점 지도 반환
 *  GET /api/eval-judge?n=12&offset=12  → 다음 배치(페이지네이션)
 *  GET /api/eval-judge?...&save=1&token=<ADMIN_SECRET>
 *                                      → data/eval/judge-report.json 로 GitHub 커밋
 *
 * 필요 env: ANTHROPIC_API_KEY(답변·채점). 채점 모델은 ANTHROPIC_JUDGE_MODEL(기본 haiku).
 * 개발/차단망에서는 키가 없어 동작하지 않음 → Vercel에서 실행.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const rag = require('../chatbot/lib/rag');
const { judgeAnswer } = require('../chatbot/lib/judge');

const EVAL = path.resolve(__dirname, '..', 'chatbot', 'data', 'eval');
const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
const REPO = process.env.GITHUB_REPO || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';
const FILEPATH = 'venom-wordpress/preview/chatbot/data/eval/judge-report.json';

const joNum = s => (String(s).match(/제\s*(\d+)\s*조/) || [])[1];
const GOLD_LABELS = {
  exempt: '사전심의 예외(정보성)', media: '심의대상 매체', review: '심의필·유효기간',
  testi: '경험담·전후사진', exag: '과장·최상급', compare: '비교·비방',
  event: '할인·유인', broadcast: '방송광고 금지', agent: '광고주체', title: '자격·명칭', adlaw: '표시광고법',
};

function loadJson(p, fb) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return fb; } }

// 층화 표본: 골드(실오답·까다로운 유형) + 법조문기반 질문(조 단위 버킷)을 그룹별 라운드로빈.
function buildPool() {
  const pool = [];
  const gold = loadJson(path.join(EVAL, 'gold.json'), { cases: [] });
  for (const c of gold.cases) {
    pool.push({ q: c.q, group: GOLD_LABELS[c.id.split('-')[0]] || '골드', src: 'gold' });
  }
  const sample = loadJson(path.join(EVAL, 'questions-sample.json'), { sample: [] });
  for (const it of (sample.sample || [])) {
    const jo = joNum((it.refs || [])[0]) || '기타';
    pool.push({ q: it.q, group: `의료법 제${jo}조`, src: 'law' });
  }
  // 그룹별 버킷 → 라운드로빈으로 다양성 확보(결정론적: 원본 순서 유지)
  const buckets = new Map();
  for (const item of pool) {
    if (!buckets.has(item.group)) buckets.set(item.group, []);
    buckets.get(item.group).push(item);
  }
  const groups = [...buckets.keys()];
  const ordered = [];
  for (let i = 0; ; i++) {
    let any = false;
    for (const g of groups) { const b = buckets.get(g); if (i < b.length) { ordered.push(b[i]); any = true; } }
    if (!any) break;
  }
  return ordered;
}

async function pmap(items, limit, fn) {
  const out = new Array(items.length);
  let idx = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (idx < items.length) { const i = idx++; try { out[i] = await fn(items[i], i); } catch (e) { out[i] = { error: e.message }; } }
  });
  await Promise.all(workers);
  return out;
}

function gh(method, body) {
  const payload = body ? JSON.stringify(body) : undefined;
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${FILEPATH}` + (method === 'GET' ? `?ref=${BRANCH}` : ''),
      method,
      headers: {
        'Authorization': `token ${process.env.GITHUB_TOKEN}`,
        'User-Agent': 'venom-eval-judge/1.0',
        'Accept': 'application/vnd.github.v3+json',
        ...(payload ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (res) => {
      const chunks = []; res.on('data', c => chunks.push(c));
      res.on('end', () => { let j = null; try { j = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {} resolve({ status: res.statusCode, json: j }); });
    });
    req.on('error', () => resolve({ status: 0 }));
    req.setTimeout(20000, () => { req.destroy(); resolve({ status: 0 }); });
    if (payload) req.write(payload); req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'GET only' });

  const q0 = req.query || {};
  // 진단 모드: Claude 호출 없이 즉시 응답. 배포/키/데이터 번들 상태 확인용.
  if (q0.ping === '1' || q0.ping === 'true') {
    let pool = [];
    try { pool = buildPool(); } catch (e) {}
    const gold = loadJson(path.join(EVAL, 'gold.json'), { cases: [] });
    const sample = loadJson(path.join(EVAL, 'questions-sample.json'), { sample: [] });
    return res.status(200).json({
      ok: true, deployed: true,
      hasAnthropicKey: !!process.env.ANTHROPIC_API_KEY,
      answerModel: process.env.ANTHROPIC_MODEL || 'claude-opus-4-8',
      judgeModel: process.env.ANTHROPIC_JUDGE_MODEL || 'claude-haiku-4-5',
      dataBundled: { gold: (gold.cases || []).length, sample: (sample.sample || []).length, poolSize: pool.length },
      usage: 'GET /api/eval-judge?n=6 (채점 실행). 느리면 n을 줄이세요.',
    });
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    return res.status(503).json({ error: 'ANTHROPIC_API_KEY 미설정 — Vercel 환경변수 설정 후 실행하세요.' });
  }

  try {
    const q = q0;
    const n = Math.max(1, Math.min(24, parseInt(q.n, 10) || 6));
    const offset = Math.max(0, parseInt(q.offset, 10) || 0);
    const conc = Math.max(1, Math.min(6, parseInt(q.c, 10) || 4));

    const pool = buildPool();
    const batch = pool.slice(offset, offset + n);
    if (!batch.length) return res.status(200).json({ note: 'offset이 표본 범위를 벗어남', poolSize: pool.length });

    const graded = await pmap(batch, conc, async (item) => {
      let stage = 'answer';
      try {
        const r = await rag.answerQuestion(item.q);
        if (!r.llm) return { ...item, skipped: '답변 LLM 미동작(키/응답 없음)' };
        stage = 'judge';
        const v = await judgeAnswer({ question: item.q, answer: r.answer, context: r.context });
        return { ...item, answer: r.answer, refs: (r.sources || []).flatMap(s => s.legalRefs).slice(0, 4), ...v };
      } catch (e) {
        return { ...item, error: `${stage}: ${e.message}` };
      }
    });

    // 진단: 채점 실패 원인을 드러낸다(전멸 시 원인 파악용)
    const errored = graded.filter(g => g && g.error);
    const skipped = graded.filter(g => g && g.skipped);
    const sampleErrors = [...new Set(errored.map(g => g.error))].slice(0, 3);

    // 집계: 전체 + 그룹별 약점 지도
    const scored = graded.filter(g => g && g.verdict);
    const avg = (arr, k) => arr.length ? +(arr.reduce((s, x) => s + (x[k] || 0), 0) / arr.length).toFixed(2) : 0;
    const pass = scored.filter(g => g.verdict === 'pass').length;
    const byGroup = {};
    for (const g of scored) {
      const b = byGroup[g.group] || (byGroup[g.group] = { n: 0, pass: 0, correctness: 0 });
      b.n++; if (g.verdict === 'pass') b.pass++; b.correctness += g.correctness;
    }
    const groupRep = Object.entries(byGroup).map(([k, v]) => ({
      group: k, n: v.n, passRate: +(v.pass / v.n * 100).toFixed(0), avgCorrectness: +(v.correctness / v.n).toFixed(2),
    })).sort((a, b) => a.passRate - b.passRate || a.avgCorrectness - b.avgCorrectness);

    const report = {
      updated: new Date().toISOString(),
      model: { answer: process.env.ANTHROPIC_MODEL || 'claude-opus-4-8', judge: process.env.ANTHROPIC_JUDGE_MODEL || 'claude-haiku-4-5' },
      batch: { n: batch.length, offset, poolSize: pool.length },
      diagnostics: { scored: scored.length, errored: errored.length, skipped: skipped.length, sampleErrors },
      overall: {
        passRate: scored.length ? +(pass / scored.length * 100).toFixed(0) : 0,
        avgGrounding: avg(scored, 'grounding'), avgCorrectness: avg(scored, 'correctness'), avgCitation: avg(scored, 'citation'),
        hallucinationRate: scored.length ? +(scored.filter(g => g.hallucination).length / scored.length * 100).toFixed(0) : 0,
      },
      weakestGroups: groupRep.slice(0, 6),
      failures: scored.filter(g => g.verdict === 'fail').map(g => ({ group: g.group, q: g.q, reason: g.reason, correctness: g.correctness, hallucination: g.hallucination })),
      allByGroup: groupRep,
    };

    // 저장(선택)
    let saved = false, saveNote;
    if (q.save === '1' || q.save === 'true') {
      const secret = process.env.ADMIN_SECRET || process.env.CRON_SECRET;
      const provided = (req.headers['authorization'] || '').replace('Bearer ', '').trim() || q.token || '';
      const ok = !secret || provided === process.env.ADMIN_SECRET || (process.env.CRON_SECRET && provided === process.env.CRON_SECRET);
      if (!ok) return res.status(401).json({ error: 'save 인증 필요: ?save=1&token=<ADMIN_SECRET>' });
      if (!process.env.GITHUB_TOKEN) saveNote = 'GITHUB_TOKEN 미설정 — 저장 생략';
      else {
        const cur = await gh('GET');
        const sha = cur.status === 200 && cur.json ? cur.json.sha : undefined;
        const content = Buffer.from(JSON.stringify(report, null, 2) + '\n').toString('base64');
        const put = await gh('PUT', { message: 'chore(chatbot): LLM-as-Judge 품질 채점 리포트', content, branch: BRANCH, ...(sha ? { sha } : {}) });
        saved = put.status === 200 || put.status === 201;
        if (!saved) saveNote = `GitHub 저장 실패 ${put.status}`;
      }
    }

    return res.status(200).json({ ...report, saved, saveNote,
      hint: (offset + n < pool.length) ? `다음 배치: ?n=${n}&offset=${offset + n}` : '표본 끝. 약점 그룹은 KB·골드셋 보강 대상.' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
