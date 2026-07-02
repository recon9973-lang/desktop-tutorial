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

    // last 30 days
    const today = new Date();
    const days = [];
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      days.push(d.toISOString().slice(0, 10));
    }

    const byDay = {};
    days.forEach(d => {
      byDay[d] = { date: d, posts: 0, promptTokens: 0, completionTokens: 0, totalTokens: 0, images: 0, costUsd: 0 };
    });

    logs.forEach(entry => {
      const date = (entry.ts || '').slice(0, 10);
      if (!byDay[date]) return;
      const d = byDay[date];
      if (entry.action === 'cron-publish' || entry.action === 'cron-publish-fixed' || entry.action === 'generate') {
        d.posts += 1;
        if (entry.tokenUsage) {
          d.promptTokens     += entry.tokenUsage.promptTokens     || 0;
          d.completionTokens += entry.tokenUsage.completionTokens || 0;
          d.totalTokens      += entry.tokenUsage.totalTokens      || 0;
          d.costUsd += (entry.tokenUsage.promptTokens     / 1e6) * PRICE_INPUT;
          d.costUsd += (entry.tokenUsage.completionTokens / 1e6) * PRICE_OUTPUT;
        }
        if (entry.imageGenerated) {
          d.images  += 1;
          d.costUsd += PRICE_IMAGE;
        }
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

    return res.status(200).json({ ok: true, days: all, totals });
  } catch (e) {
    console.error('[usage-stats]', e);
    return res.status(500).json({ error: e.message });
  }
};
