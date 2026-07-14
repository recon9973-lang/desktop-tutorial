'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · GSC Search Analytics(date 차원) → 성과 메트릭 레코드
//   설계: docs/plans/geo-ops-os-design.md §3 metrics, P1 #6 후속(GSC API 자동수집)
//   lib/search-console.js querySearchAnalytics 결과 rows[{keys:[date],clicks,impressions,ctr,position}]
//   → geo-metrics 와 동일한 레코드 형태({id,clientId,metricName,metricDate,value,source}).
//   ctr 은 GSC 가 소수(0.035) → CSV 경로와 통일하려 %(3.5)로 저장. 순수 함수 = 오프라인 테스트.
// ─────────────────────────────────────────────────────────────────────────

function round(n, d) { const f = Math.pow(10, d || 0); return Math.round((Number(n) || 0) * f) / f; }

// GSC rows(date 차원) → 메트릭 레코드[]
function rowsToMetrics(rows, opts) {
  opts = opts || {};
  const clientId = opts.clientId; const source = opts.source || 'gsc'; const channelId = opts.channelId || null;
  if (!clientId) throw new Error('clientId 필요');
  const out = [];
  (rows || []).forEach((r) => {
    const date = Array.isArray(r.keys) ? r.keys[0] : r.date;
    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(String(date))) return;
    const vals = {
      clicks: round(r.clicks, 0),
      impressions: round(r.impressions, 0),
      ctr: round((r.ctr || 0) * 100, 2), // 소수→%
      position: round(r.position, 2),
    };
    Object.keys(vals).forEach((name) => {
      out.push({ id: 'm_' + clientId + '_' + name + '_' + date, clientId, channelId, metricName: name, metricDate: date, value: vals[name], source });
    });
  });
  return out;
}

module.exports = { rowsToMetrics, round };
