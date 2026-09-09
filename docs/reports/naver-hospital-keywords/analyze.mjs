#!/usr/bin/env node
// 네이버 데이터랩 검색어트렌드 원자료 → 공통 스케일 지수 변환 및 집계
// 원리: DataLab ratio = c_R × 실제검색량 (c_R은 요청마다 다른 상수).
//       모든 요청에 앵커 키워드(서울피부과)를 넣었으므로
//       raw / mean(앵커_of_그_요청) 로 나누면 c_R이 소거되고
//       "서울피부과 3년 평균 = 100" 스케일의 공통 지수가 된다.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const ANCHOR = '서울피부과';
const DEPTS = ['치과', '한의원', '피부과', '정형외과', '안과', '내과', '성형외과'];
const METROS = ['서울', '부산', '대구', '인천', '광주', '대전', '울산'];

const MONTHS = [];
for (let y = 2023, m = 9; MONTHS.length < 36; m++) {
  if (m > 12) { m = 1; y++; }
  MONTHS.push(`${y}-${String(m).padStart(2, '0')}`);
}

// --- 파싱 ---
const lines = readFileSync(join(DIR, 'raw-datalab.csv'), 'utf8').trim().split('\n').slice(1);
const rows = lines.map((ln) => {
  const [head, vals] = ln.split('"');
  const [req, keyword, isAnchor] = head.split(',');
  return { req, keyword, isAnchor: isAnchor === '1', v: vals.split(',').map(Number) };
});

// --- 요청별 앵커 평균으로 스케일 통일 ---
const anchorMean = {};
for (const r of rows) {
  if (r.isAnchor) anchorMean[r.req] = r.v.reduce((a, b) => a + b, 0) / r.v.length;
}
const series = {}; // keyword -> 36개월 지수 (서울피부과 3년평균 = 100)
for (const r of rows) {
  if (r.isAnchor && series[ANCHOR]) continue;
  series[r.keyword] = r.v.map((x) => (x / anchorMean[r.req]) * 100);
}

// --- 지표 계산 ---
const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
const median = (a) => { const s = [...a].sort((x, y) => x - y); const h = s.length >> 1;
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2; };

function stats(v) {
  const y1 = mean(v.slice(0, 12));   // 2023-09 ~ 2024-08
  const y2 = mean(v.slice(12, 24));  // 2024-09 ~ 2025-08
  const y3 = mean(v.slice(24, 36));  // 2025-09 ~ 2026-08
  const avg = mean(v);
  const sd = Math.sqrt(mean(v.map((x) => (x - avg) ** 2)));
  // 계절지수: 월(1~12)별 3년 평균을 전체평균 100 기준으로
  const seasonal = Array.from({ length: 12 }, (_, i) => {
    const mm = ((i + 8) % 12) + 1; // 배열 0번 = 9월
    const picks = [v[i], v[i + 12], v[i + 24]];
    return { month: mm, idx: (mean(picks) / avg) * 100 };
  }).sort((a, b) => a.month - b.month);
  return {
    avg, y1, y2, y3,
    g21: (y2 / y1 - 1) * 100,
    g32: (y3 / y2 - 1) * 100,
    g31: (y3 / y1 - 1) * 100,
    cv: (sd / avg) * 100,
    spike: Math.max(...v) / median(v),
    peakMonth: seasonal.reduce((a, b) => (b.idx > a.idx ? b : a)).month,
    lowMonth: seasonal.reduce((a, b) => (b.idx < a.idx ? b : a)).month,
    seasonal: seasonal.map((s) => s.idx),
  };
}

const out = { meta: {
  source: '네이버 데이터랩 검색어트렌드 (PlayMCP NaverSearch datalab_search)',
  period: '2023-09 ~ 2026-08 (36개월, 월간)',
  scale: `상대지수 — 앵커 '${ANCHOR}'의 36개월 평균 = 100`,
  note: '데이터랩은 상대적 검색 비율만 제공하며 절대 검색량(회)이 아님. PC+모바일 합산, 성별·연령 전체.',
  months: MONTHS,
}, keywords: {} };

for (const [k, v] of Object.entries(series)) {
  out.keywords[k] = { series: v.map((x) => +x.toFixed(2)), ...stats(v) };
}

// --- 매트릭스 (7대 도시 × 7개 진료과) ---
const cell = (region, dept) => out.keywords[region + dept];
const matrix = { avg: {}, g31: {} };
for (const d of DEPTS) {
  matrix.avg[d] = {}; matrix.g31[d] = {};
  for (const r of METROS) {
    const c = cell(r, d);
    matrix.avg[d][r] = c ? +c.avg.toFixed(1) : null;
    matrix.g31[d][r] = c ? +c.g31.toFixed(1) : null;
  }
}
out.matrix = matrix;

// 진료과 합계(7대 도시 합산 지수)와 성장률
out.deptTotals = DEPTS.map((d) => {
  const cells = METROS.map((r) => cell(r, d)).filter(Boolean);
  const sum = (f) => cells.reduce((a, c) => a + f(c), 0);
  return { dept: d, n: cells.length, avg: +sum((c) => c.avg).toFixed(1),
    y1: +sum((c) => c.y1).toFixed(1), y2: +sum((c) => c.y2).toFixed(1), y3: +sum((c) => c.y3).toFixed(1),
    g31: +((sum((c) => c.y3) / sum((c) => c.y1) - 1) * 100).toFixed(1) };
}).sort((a, b) => b.avg - a.avg);

// 지역 합계(7개 진료과 합산 지수)
out.regionTotals = METROS.map((r) => {
  const cells = DEPTS.map((d) => cell(r, d)).filter(Boolean);
  const sum = (f) => cells.reduce((a, c) => a + f(c), 0);
  return { region: r, n: cells.length, avg: +sum((c) => c.avg).toFixed(1),
    y1: +sum((c) => c.y1).toFixed(1), y3: +sum((c) => c.y3).toFixed(1),
    g31: +((sum((c) => c.y3) / sum((c) => c.y1) - 1) * 100).toFixed(1) };
}).sort((a, b) => b.avg - a.avg);

writeFileSync(join(DIR, 'index-series.json'), JSON.stringify(out, null, 1));

// --- 콘솔 요약 ---
const fmt = (n, w = 7) => String(n).padStart(w);
console.log(`\n■ 진료과별 (7대 도시 합산 지수, 서울피부과 3년평균=100 기준)`);
console.log('  진료과      3년평균   Y1     Y2     Y3    Y3/Y1');
for (const t of out.deptTotals)
  console.log(`  ${t.dept.padEnd(8)}${fmt(t.avg)}${fmt(t.y1)}${fmt(t.y2)}${fmt(t.y3)}${fmt(t.g31 + '%')}`);

console.log(`\n■ 지역별 (7개 진료과 합산 지수)`);
console.log('  지역        3년평균    Y1     Y3    Y3/Y1');
for (const t of out.regionTotals)
  console.log(`  ${t.region.padEnd(8)}${fmt(t.avg)}${fmt(t.y1)}${fmt(t.y3)}${fmt(t.g31 + '%')}`);

console.log(`\n■ 키워드 상위 20 (3년 평균 지수)`);
const ranked = Object.entries(out.keywords).map(([k, v]) => ({ k, ...v })).sort((a, b) => b.avg - a.avg);
console.log('  키워드            평균   Y3/Y1     CV   피크월  스파이크');
for (const r of ranked.slice(0, 20))
  console.log(`  ${r.k.padEnd(16)}${fmt(r.avg.toFixed(1), 6)}${fmt(r.g31.toFixed(1) + '%')}${fmt(r.cv.toFixed(0) + '%')}${fmt(r.peakMonth + '월', 7)}${fmt(r.spike.toFixed(1) + 'x')}`);

console.log(`\n■ 3년 성장 상위/하위 10 (7대도시×7과 49개 중, 지수 5 이상)`);
const core = DEPTS.flatMap((d) => METROS.map((r) => ({ k: r + d, ...out.keywords[r + d] }))).filter((x) => x.avg >= 5);
const byG = [...core].sort((a, b) => b.g31 - a.g31);
for (const r of byG.slice(0, 10)) console.log(`  ▲ ${r.k.padEnd(16)}${fmt(r.g31.toFixed(1) + '%')}  (평균 ${r.avg.toFixed(1)})`);
for (const r of byG.slice(-10).reverse()) console.log(`  ▼ ${r.k.padEnd(16)}${fmt(r.g31.toFixed(1) + '%')}  (평균 ${r.avg.toFixed(1)})`);

console.log(`\n■ 진료과별 계절지수 (7대도시 평균, 연평균=100)`);
console.log('  진료과    ' + Array.from({ length: 12 }, (_, i) => fmt(i + 1 + '월', 6)).join(''));
for (const d of DEPTS) {
  const cs = METROS.map((r) => cell(r, d)).filter(Boolean);
  const s = Array.from({ length: 12 }, (_, i) => mean(cs.map((c) => c.seasonal[i])));
  console.log(`  ${d.padEnd(10)}` + s.map((x) => fmt(x.toFixed(0), 6)).join(''));
}
console.log('');
