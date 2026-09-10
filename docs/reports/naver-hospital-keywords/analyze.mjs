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

// 키워드 분류 — 지역명+진료과 / 상권명+진료과 / 진료과 단독 / 시술·질환 / 의료 무관 대조군
const GENERIC = ['피부과','치과','한의원','내과','정형외과','안과','성형외과','병원'];
const PROC    = ['임플란트','라식','도수치료','여드름치료'];
const CTRL    = ['날씨','지하철','환율','로또'];
const DISTRICT= ['강남피부과','강남치과','서면피부과','부평치과'];
// 'metro'는 7대 도시 × 보고서가 다루는 7개 진료과 조합만. 초기에 수집했다가 범위에서 빠진
// 산부인과·이비인후과·비뇨기과는 'extra'로 따로 둔다 — 합산에 섞이면 지역 총량이 부풀려진다.
const group = k => GENERIC.includes(k) ? 'generic' : PROC.includes(k) ? 'proc'
  : CTRL.includes(k) ? 'control' : DISTRICT.includes(k) ? 'district'
  : METROS.some(m => k.startsWith(m)) ? (DEPTS.includes(k.slice(2)) ? 'metro' : 'extra')
  : DEPTS.some(d => k.endsWith(d)) ? 'city' : 'extra';
for (const k of Object.keys(out.keywords)) out.keywords[k].group = group(k);

// 진료과별 대표 키워드 TOP3 (7대 도시 안에서 — 도시 수가 같아 진료과끼리 공정 비교)
out.top3 = DEPTS.map(d => ({ dept: d,
  rows: METROS.map(r => ({ keyword: r + d, region: r, ...out.keywords[r + d] }))
    .sort((a, b) => b.avg - a.avg).slice(0, 3)
    .map((x, i) => ({ rank: i + 1, keyword: x.keyword, region: x.region,
      avg: +x.avg.toFixed(1), y1: +x.y1.toFixed(1), y2: +x.y2.toFixed(1), y3: +x.y3.toFixed(1),
      g31: +x.g31.toFixed(1), cv: +x.cv.toFixed(0), peakMonth: x.peakMonth })),
  // 7대 도시 밖(중소도시·상권)에서 그 진료과 3위 컷을 넘는 키워드
  outside: Object.entries(out.keywords)
    .filter(([k, v]) => k.endsWith(d) && (v.group === 'city' || v.group === 'district'))
    .map(([k, v]) => ({ keyword: k, avg: +v.avg.toFixed(1), g31: +v.g31.toFixed(1) }))
    .filter(x => x.avg > METROS.map(r => out.keywords[r + d].avg).sort((a, b) => b - a)[2])
    .sort((a, b) => b.avg - a.avg),
}));

// 「수요 자체가 줄었나」 — 그룹별 합산 Y1 → Y3
const bucket = (keys) => { const cs = keys.map(k => out.keywords[k]).filter(Boolean);
  const sum = f => cs.reduce((a, c) => a + f(c), 0);
  return { n: cs.length, y1: +sum(c => c.y1).toFixed(1), y2: +sum(c => c.y2).toFixed(1),
    y3: +sum(c => c.y3).toFixed(1), g31: +((sum(c => c.y3) / sum(c => c.y1) - 1) * 100).toFixed(1) }; };
out.buckets = {
  '지역명+진료과 49개 합산': bucket(DEPTS.flatMap(d => METROS.map(r => r + d))),
  '진료과 단독 7개 합산':    bucket(['피부과','치과','한의원','내과','정형외과','안과','성형외과']),
  '「병원」 단독':            bucket(['병원']),
  '시술·질환 4개 합산':      bucket(PROC),
  '대조군(의료 무관) 4개':   bucket(CTRL),
};
out.controlEach = CTRL.map(k => ({ keyword: k, avg: +out.keywords[k].avg.toFixed(1),
  y1: +out.keywords[k].y1.toFixed(2), y2: +out.keywords[k].y2.toFixed(2),
  y3: +out.keywords[k].y3.toFixed(2), g31: +out.keywords[k].g31.toFixed(1) }));
out.genericEach = GENERIC.map(k => ({ keyword: k, avg: +out.keywords[k].avg.toFixed(1),
  y1: +out.keywords[k].y1.toFixed(1), y2: +out.keywords[k].y2.toFixed(1),
  y3: +out.keywords[k].y3.toFixed(1), g31: +out.keywords[k].g31.toFixed(1) }));
out.procEach = PROC.map(k => ({ keyword: k, avg: +out.keywords[k].avg.toFixed(1),
  y1: +out.keywords[k].y1.toFixed(1), y2: +out.keywords[k].y2.toFixed(1),
  y3: +out.keywords[k].y3.toFixed(1), g31: +out.keywords[k].g31.toFixed(1),
  cv: +out.keywords[k].cv.toFixed(0), spike: +out.keywords[k].spike.toFixed(1) }));

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
    y1: +sum((c) => c.y1).toFixed(1), y2: +sum((c) => c.y2).toFixed(1), y3: +sum((c) => c.y3).toFixed(1),
    g31: +((sum((c) => c.y3) / sum((c) => c.y1) - 1) * 100).toFixed(1) };
}).sort((a, b) => b.avg - a.avg);

// 진료과별 계절지수 (7대 도시 각각의 계절지수를 단순평균) — 엑셀 캐시값과 보고서가 같은 값을 쓰도록
out.deptSeasonal = DEPTS.map((d) => {
  const cs = METROS.map((r) => out.keywords[r + d]).filter(Boolean);
  return { dept: d, seasonal: Array.from({ length: 12 }, (_, i) =>
    +(cs.reduce((a, c) => a + c.seasonal[i], 0) / cs.length).toFixed(2)) };
});

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

console.log(`\n■ 「수요가 줄었나」 그룹별 합산 (Y1 → Y3)`);
console.log('  그룹                            Y1      Y2      Y3    Y3/Y1');
for (const [k, v] of Object.entries(out.buckets))
  console.log(`  ${k.padEnd(26)}${fmt(v.y1, 8)}${fmt(v.y2, 8)}${fmt(v.y3, 8)}${fmt(v.g31 + '%', 9)}`);
console.log(`\n■ 대조군 개별 (의료와 무관)`);
for (const c of out.controlEach)
  console.log(`  ${c.keyword.padEnd(8)}Y1 ${fmt(c.y1, 8)} → Y3 ${fmt(c.y3, 8)}  ${fmt(c.g31 + '%', 9)}`);
console.log(`\n■ 진료과 단독(전국) 키워드`);
for (const c of out.genericEach)
  console.log(`  ${c.keyword.padEnd(8)}평균 ${fmt(c.avg, 7)}  Y1 ${fmt(c.y1, 7)} → Y3 ${fmt(c.y3, 7)}  ${fmt(c.g31 + '%', 9)}`);
console.log(`\n■ 시술·질환 키워드`);
for (const c of out.procEach)
  console.log(`  ${c.keyword.padEnd(10)}평균 ${fmt(c.avg, 7)}  Y1 ${fmt(c.y1, 7)} → Y3 ${fmt(c.y3, 7)}  ${fmt(c.g31 + '%', 9)}  스파이크 ${c.spike}x`);
console.log(`\n■ 진료과별 TOP3 (7대 도시)`);
for (const t of out.top3) {
  console.log(`  ${t.dept}`);
  for (const r of t.rows)
    console.log(`    ${r.rank}. ${r.keyword.padEnd(12)}평균 ${fmt(r.avg, 7)}  Y1 ${fmt(r.y1, 7)} Y2 ${fmt(r.y2, 7)} Y3 ${fmt(r.y3, 7)}  ${fmt(r.g31 + '%', 8)}`);
  if (t.outside.length) console.log(`       (7대 도시 밖 상위: ${t.outside.map(o => `${o.keyword} ${o.avg}`).join(', ')})`);
}

console.log(`\n■ 진료과별 계절지수 (7대도시 평균, 연평균=100)`);
console.log('  진료과    ' + Array.from({ length: 12 }, (_, i) => fmt(i + 1 + '월', 6)).join(''));
for (const d of DEPTS) {
  const cs = METROS.map((r) => cell(r, d)).filter(Boolean);
  const s = Array.from({ length: 12 }, (_, i) => mean(cs.map((c) => c.seasonal[i])));
  console.log(`  ${d.padEnd(10)}` + s.map((x) => fmt(x.toFixed(0), 6)).join(''));
}
console.log('');
