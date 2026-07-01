'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GrowthOps · M3 Core Web Vitals (PageSpeed Insights) 수집·파싱
// ─────────────────────────────────────────────────────────────────────────
// Google PSI(pagespeedonline v5)로 핵심 페이지의 성능/CWV를 측정한다.
//   - parsePsi(json): 순수 파서(네트워크 없음) — 카테고리 점수 + 랩(LCP/CLS/TBT…) +
//                     필드데이터(CrUX) 추출. 단위 테스트 대상.
//   - fetchPsi(url, opts): 실제 PSI 호출(process.env.PSI_KEY 필요).
// PSI_KEY 미설정/네트워크 실패는 throw하지 않고 { ok:false, reason } 로 안전 반환.
// ─────────────────────────────────────────────────────────────────────────

const https = require('https');

function pct(score) { return score == null ? null : Math.round(score * 100); }

/** PSI 응답 JSON → 요약 지표(순수). */
function parsePsi(json) {
  if (!json || typeof json !== 'object') return { ok: false, reason: 'empty' };
  if (json.error) return { ok: false, reason: (json.error.message || 'psi error') };
  const lr = json.lighthouseResult;
  if (!lr) return { ok: false, reason: 'no lighthouseResult' };

  const cat = lr.categories || {};
  const scores = {
    performance: pct(cat.performance && cat.performance.score),
    seo: pct(cat.seo && cat.seo.score),
    accessibility: pct(cat.accessibility && cat.accessibility.score),
    bestPractices: pct(cat['best-practices'] && cat['best-practices'].score),
  };

  const a = lr.audits || {};
  const num = (k) => (a[k] && typeof a[k].numericValue === 'number' ? a[k].numericValue : null);
  const lab = {
    lcpMs: num('largest-contentful-paint'),
    cls: num('cumulative-layout-shift'),
    tbtMs: num('total-blocking-time'),
    fcpMs: num('first-contentful-paint'),
    siMs: num('speed-index'),
    inpMs: num('interaction-to-next-paint'),
  };

  // 필드데이터(CrUX) — 있으면 실제 사용자 경험치
  let field = null;
  const le = json.loadingExperience && json.loadingExperience.metrics;
  if (le) {
    const g = (k) => (le[k] ? { p75: le[k].percentile, category: le[k].category } : null);
    field = {
      lcp: g('LARGEST_CONTENTFUL_PAINT_MS'),
      cls: g('CUMULATIVE_LAYOUT_SHIFT_SCORE'),
      inp: g('INTERACTION_TO_NEXT_PAINT'),
      fcp: g('FIRST_CONTENTFUL_PAINT_MS'),
    };
  }

  return {
    ok: true,
    url: (lr.finalUrl || json.id || ''),
    strategy: (lr.configSettings && lr.configSettings.formFactor) || 'mobile',
    scores,
    lab,
    field,
  };
}

function httpGetJson(fullUrl, timeout) {
  return new Promise((resolve) => {
    const req = https.get(fullUrl, (r) => {
      const chunks = [];
      r.on('data', (c) => chunks.push(c));
      r.on('end', () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
        catch (e) { resolve({ error: { message: 'parse error' } }); }
      });
    });
    req.on('error', (e) => resolve({ error: { message: e.message } }));
    req.setTimeout(timeout || 25000, () => { req.destroy(); resolve({ error: { message: 'timeout' } }); });
  });
}

/** 실제 PSI 호출. PSI_KEY 없으면 { ok:false, reason }. */
async function fetchPsi(url, opts = {}) {
  const key = process.env.PSI_KEY;
  if (!key) return { ok: false, reason: 'PSI_KEY not configured', url };
  if (!url || !/^https?:\/\//.test(url)) return { ok: false, reason: 'invalid url', url };
  const strategy = opts.strategy === 'desktop' ? 'desktop' : 'mobile';
  const api = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url='
    + encodeURIComponent(url) + '&key=' + encodeURIComponent(key)
    + '&strategy=' + strategy
    + '&category=performance&category=seo&category=best-practices&category=accessibility';
  const json = await httpGetJson(api, opts.timeout);
  const parsed = parsePsi(json);
  if (!parsed.url) parsed.url = url;
  return parsed;
}

module.exports = { parsePsi, fetchPsi };
