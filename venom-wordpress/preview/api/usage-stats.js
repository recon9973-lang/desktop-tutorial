'use strict';

const https = require('https');

const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
const REPO  = process.env.GITHUB_REPO  || 'desktop-tutorial';
const TOKEN = process.env.GITHUB_TOKEN;
const LOG_PATH = 'venom-wordpress/preview/content/posting-log.json';

// gpt-4o-mini pricing (per 1M tokens)
const PRICE_INPUT  = 0.15;
const PRICE_OUTPUT = 0.60;
// dall-e-3 1024x1024 standard
const PRICE_IMAGE  = 0.040;

// 카테고리 코드 → 한글 라벨(상세 분석 표기용)
const CAT_LABEL = {
  geo_local: '지역마케팅', geo: 'GEO/AI', aeo: 'AEO', seo: 'SEO', strategy: '전략',
  dental: '치과', skin: '피부과', ortho: '정형외과', oriental: '한의원',
  plastic: '성형외과', naegwa: '내과', angwa: '안과', shimui: '의료광고심의',
  hosp_mkt: '병원마케팅', marketing: '마케팅',
};
const catLabel = (c) => CAT_LABEL[c] || c || '기타';
const round4 = (n) => Math.round(n * 1e4) / 1e4;

function ghGet(filePath) {
  return new Promise((resolve) => {
    if (!TOKEN) return resolve(null);
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}`,
      method: 'GET',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
      },
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const body = JSON.parse(data);
          if (res.statusCode === 200) resolve(body);
          else resolve(null);
        } catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'GET only' });

  try {
    const file = await ghGet(LOG_PATH);
    const logs = file && file.content
      ? JSON.parse(Buffer.from(file.content, 'base64').toString('utf8'))
      : [];

    // 기간 선택(7/30/90일 등). 기본 30일, 7~90일 범위로 클램프.
    let nDays = parseInt((req.query && req.query.days) || '30', 10);
    if (!Number.isFinite(nDays)) nDays = 30;
    nDays = Math.max(7, Math.min(90, nDays));

    const today = new Date();
    const days = [];
    for (let i = nDays - 1; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      days.push(d.toISOString().slice(0, 10));
    }

    const byDay = {};
    days.forEach(d => {
      byDay[d] = { date: d, posts: 0, promptTokens: 0, completionTokens: 0, totalTokens: 0, images: 0, costUsd: 0 };
    });

    // 상세 분석 누적기 (카테고리·모델·액션별 / 입력·출력 / 비용 구성)
    const byCat = {}, byModel = {}, byAction = {};
    const io = { promptTokens: 0, completionTokens: 0 };
    const cost = { inputUsd: 0, outputUsd: 0, imageUsd: 0 };
    const bump = (map, key, ent) => {
      const m = (map[key] = map[key] || { key, posts: 0, promptTokens: 0, completionTokens: 0, totalTokens: 0, images: 0, costUsd: 0 });
      m.posts += 1;
      m.promptTokens += ent.p; m.completionTokens += ent.c; m.totalTokens += ent.t;
      m.images += ent.img; m.costUsd += ent.cost;
    };

    logs.forEach(entry => {
      const date = (entry.ts || '').slice(0, 10);
      if (!byDay[date]) return;
      const d = byDay[date];
      if (entry.action === 'cron-publish' || entry.action === 'cron-publish-fixed' || entry.action === 'generate') {
        d.posts += 1;
        const tu = entry.tokenUsage || {};
        const p = tu.promptTokens || 0, c = tu.completionTokens || 0, t = tu.totalTokens || (p + c);
        const inUsd = (p / 1e6) * PRICE_INPUT, outUsd = (c / 1e6) * PRICE_OUTPUT;
        const imgUsd = entry.imageGenerated ? PRICE_IMAGE : 0;
        const entCost = inUsd + outUsd + imgUsd;
        d.promptTokens += p; d.completionTokens += c; d.totalTokens += t;
        d.costUsd += inUsd + outUsd;
        if (entry.imageGenerated) { d.images += 1; d.costUsd += PRICE_IMAGE; }
        // 상세 누적
        io.promptTokens += p; io.completionTokens += c;
        cost.inputUsd += inUsd; cost.outputUsd += outUsd; cost.imageUsd += imgUsd;
        const acc = { p, c, t, img: entry.imageGenerated ? 1 : 0, cost: entCost };
        bump(byCat, entry.category || '기타', acc);
        bump(byModel, (tu.model || 'unknown'), acc);
        bump(byAction, (entry.action === 'generate' ? '수동/즉시' : '크론 자동'), acc);
      }
    });

    // totals
    const all = Object.values(byDay);
    const totals = all.reduce((acc, d) => {
      acc.posts             += d.posts;
      acc.promptTokens      += d.promptTokens;
      acc.completionTokens  += d.completionTokens;
      acc.totalTokens       += d.totalTokens;
      acc.images            += d.images;
      acc.costUsd           += d.costUsd;
      return acc;
    }, { posts: 0, promptTokens: 0, completionTokens: 0, totalTokens: 0, images: 0, costUsd: 0 });

    // 상세 분석 정리 (내림차순 정렬 + 비율)
    const tt = totals.totalTokens || 1;
    const sortByTokens = (map, addLabel) => Object.values(map)
      .map(m => Object.assign(m, {
        label: addLabel ? catLabel(m.key) : m.key,
        costUsd: round4(m.costUsd),
        pct: Math.round((m.totalTokens / tt) * 100),
      }))
      .sort((a, b) => b.totalTokens - a.totalTokens);

    const detail = {
      byCategory: sortByTokens(byCat, true),
      byModel:    sortByTokens(byModel, false),
      byAction:   sortByTokens(byAction, false),
      io: {
        promptTokens: io.promptTokens,
        completionTokens: io.completionTokens,
        promptPct: Math.round((io.promptTokens / tt) * 100),
        completionPct: Math.round((io.completionTokens / tt) * 100),
      },
      cost: {
        inputUsd:  round4(cost.inputUsd),
        outputUsd: round4(cost.outputUsd),
        imageUsd:  round4(cost.imageUsd),
        totalUsd:  round4(cost.inputUsd + cost.outputUsd + cost.imageUsd),
      },
      avg: {
        tokensPerPost: totals.posts ? Math.round(totals.totalTokens / totals.posts) : 0,
        costPerPost:   totals.posts ? round4(totals.costUsd / totals.posts) : 0,
      },
    };

    return res.status(200).json({ ok: true, days: all, totals, period: nDays, detail });
  } catch (e) {
    console.error('[usage-stats]', e);
    return res.status(500).json({ error: e.message });
  }
};
