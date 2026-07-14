'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · 성과 수집(메트릭) — CSV 파싱·정규화·시계열/요약
//   설계: docs/plans/geo-ops-os-design.md §1.2/§3 (metrics), P1 #6
//   CSV 우선(즉시 사용). GSC "Dates" 내보내기(Date,Clicks,Impressions,CTR,Position)와
//   일반형(metricName,metricDate,value) 모두 지원. GSC API 자동수집은 러너 워크플로가 같은 레코드로 적재.
//   모두 순수 함수 → 오프라인 단위 테스트 대상.
//   레코드: { id, clientId, channelId?, metricName, metricDate(YYYY-MM-DD), value:number, source }
//   id = m_<clientId>_<metricName>_<date> → 재적재 시 중복 없이 덮어씀.
// ─────────────────────────────────────────────────────────────────────────

// 헤더명 → 표준 메트릭명
const CANON = {
  clicks: 'clicks', click: 'clicks', 클릭: 'clicks', 클릭수: 'clicks',
  impressions: 'impressions', impr: 'impressions', 노출: 'impressions', 노출수: 'impressions',
  ctr: 'ctr',
  position: 'position', pos: 'position', 순위: 'position', 평균순위: 'position',
  sessions: 'sessions', 세션: 'sessions',
  conversions: 'conversions', conversion: 'conversions', 전환: 'conversions', 전환수: 'conversions',
};

// 따옴표(숫자 내 콤마 "1,234") 지원 최소 CSV 라인 파서
function splitCsvLine(line) {
  const out = []; let cur = '', q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) { if (c === '"') { if (line[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
    else { if (c === '"') q = true; else if (c === ',') { out.push(cur); cur = ''; } else cur += c; }
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

function parseCsv(text) {
  const lines = String(text || '').split(/\r?\n/).filter((l) => l.trim() !== '');
  if (!lines.length) return { headers: [], rows: [] };
  const headers = splitCsvLine(lines[0]).map((h) => h.replace(/^﻿/, ''));
  const rows = lines.slice(1).map((l) => {
    const cells = splitCsvLine(l); const o = {};
    headers.forEach((h, i) => { o[h] = cells[i] != null ? cells[i] : ''; });
    return o;
  });
  return { headers, rows };
}

function toNum(v) {
  if (v == null) return null;
  const n = Number(String(v).replace(/[",%\s]/g, ''));
  return Number.isFinite(n) ? n : null;
}
function normDate(v) {
  const s = String(v || '').trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const m = s.match(/^(\d{4})[./-](\d{1,2})[./-](\d{1,2})/);
  if (m) return m[1] + '-' + String(m[2]).padStart(2, '0') + '-' + String(m[3]).padStart(2, '0');
  return null;
}

// CSV 텍스트 → 메트릭 레코드[]
function csvToMetrics(text, opts) {
  opts = opts || {};
  const clientId = opts.clientId; const source = opts.source || 'csv'; const channelId = opts.channelId || null;
  if (!clientId) throw new Error('clientId 필요');
  const { headers, rows } = parseCsv(text);
  const lower = headers.map((h) => h.toLowerCase());

  const dateIdx = lower.findIndex((h) => /date|날짜/.test(h));
  const metricCols = headers.map((h, i) => ({ i, name: CANON[h.toLowerCase()] })).filter((c) => c.name && c.i !== dateIdx);
  const out = [];

  // GSC/GA4 Dates 형식: 날짜 컬럼 + 표준 메트릭 컬럼이 실제로 존재할 때만
  // (일반형은 표준 메트릭 컬럼이 없으므로 이 분기를 건너뛰고 아래 일반 파서로)
  if (dateIdx >= 0 && metricCols.length > 0) {
    rows.forEach((r) => {
      const d = normDate(r[headers[dateIdx]]);
      if (!d) return;
      metricCols.forEach((c) => {
        const val = toNum(r[headers[c.i]]);
        if (val == null) return;
        out.push(rec(clientId, channelId, c.name, d, val, source));
      });
    });
    return out;
  }

  // 일반형: metricName, metricDate(or date), value
  const nameKey = headers.find((h) => /metric.?name|지표/i.test(h));
  const dateKey = headers.find((h) => /metric.?date|date|날짜/i.test(h));
  const valKey = headers.find((h) => /value|값|수치/i.test(h));
  if (nameKey && dateKey && valKey) {
    rows.forEach((r) => {
      const d = normDate(r[dateKey]); const val = toNum(r[valKey]);
      const name = CANON[String(r[nameKey]).toLowerCase()] || String(r[nameKey]).trim();
      if (d && val != null && name) out.push(rec(clientId, channelId, name, d, val, source));
    });
  }
  return out;
}

function rec(clientId, channelId, metricName, metricDate, value, source) {
  return { id: 'm_' + clientId + '_' + metricName + '_' + metricDate, clientId, channelId, metricName, metricDate, value, source };
}

// 시계열: 특정 clientId(+metricName) 오름차순 [{date,value}]
function seriesFrom(metrics, opts) {
  opts = opts || {};
  return (metrics || [])
    .filter((m) => (!opts.clientId || m.clientId === opts.clientId) && (!opts.metricName || m.metricName === opts.metricName))
    .slice().sort((a, b) => String(a.metricDate).localeCompare(String(b.metricDate)))
    .map((m) => ({ date: m.metricDate, value: m.value }));
}

// 요약: 메트릭별 최신값 + 직전 대비 delta
function summarize(metrics, opts) {
  opts = opts || {};
  const rows = (metrics || []).filter((m) => !opts.clientId || m.clientId === opts.clientId);
  const byName = {};
  rows.forEach((m) => { (byName[m.metricName] = byName[m.metricName] || []).push(m); });
  return Object.keys(byName).sort().map((name) => {
    const arr = byName[name].slice().sort((a, b) => String(a.metricDate).localeCompare(String(b.metricDate)));
    const latest = arr[arr.length - 1]; const prev = arr.length > 1 ? arr[arr.length - 2] : null;
    return {
      metricName: name, date: latest.metricDate, latest: latest.value,
      prev: prev ? prev.value : null,
      delta: prev ? Math.round((latest.value - prev.value) * 100) / 100 : null,
      points: arr.length,
    };
  });
}

module.exports = { parseCsv, splitCsvLine, csvToMetrics, seriesFrom, summarize, normDate, toNum, CANON };
