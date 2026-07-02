'use strict';

/*
 * 블로그 인포그래픽 10종 — 자동발행 글의 데이터 막대그래프를 다양한 시각화로 교체.
 * 흐름: AI가 생성한 표준 막대그래프 블록에서 (라벨,퍼센트) 데이터를 추출 →
 *       10종 중 하나를 회전 선택해 같은 데이터로 재렌더 → 원본 블록 치환.
 * 모든 렌더러는 인라인 스타일(CMS/이메일 안전), 베놈 퍼플(#533afd) 계열.
 */

const BRAND = '#533afd';
const PALETTE = ['#533afd', '#7c3aed', '#6366f1', '#8b5cf6', '#4f46e5', '#a78bfa'];
const clamp = (v) => Math.max(0, Math.min(100, Math.round(v)));
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const color = (i) => PALETTE[i % PALETTE.length];

// ── 10종 렌더러 ──────────────────────────────────────────────
// 1) 가로 막대(그라데이션)
function horizontalBars(d) {
  const rows = d.map((x, i) => `<div style="display:flex;align-items:center;gap:12px;margin:9px 0">`
    + `<span style="width:140px;font-size:13px;font-weight:600;color:#334155;flex-shrink:0">${esc(x.label)}</span>`
    + `<span style="flex:1;background:#eef0f5;border-radius:6px;overflow:hidden"><span style="display:block;height:20px;width:${clamp(x.value)}%;background:linear-gradient(90deg,${BRAND},#818cf8);border-radius:6px"></span></span>`
    + `<span style="width:46px;font-size:13px;font-weight:700;text-align:right;color:${BRAND};flex-shrink:0">${clamp(x.value)}%</span></div>`).join('');
  return wrap(rows);
}
// 2) 세로 막대(컬럼)
function verticalColumns(d) {
  const cols = d.map((x, i) => `<div style="flex:1;min-width:0;text-align:center">`
    + `<div style="font-size:13px;font-weight:800;color:${color(i)};margin-bottom:6px">${clamp(x.value)}%</div>`
    + `<div style="height:140px;display:flex;align-items:flex-end;justify-content:center"><div style="width:60%;max-width:40px;height:${clamp(x.value)}%;background:linear-gradient(180deg,${color(i)},#a5b4fc);border-radius:7px 7px 0 0"></div></div>`
    + `<div style="font-size:12px;color:#475569;margin-top:8px;word-break:keep-all">${esc(x.label)}</div></div>`).join('');
  return wrap(`<div style="display:flex;gap:10px;align-items:flex-end">${cols}</div>`);
}
// 3) 진행 링(도넛) 그리드
function progressRings(d) {
  const cells = d.map((x, i) => {
    const v = clamp(x.value), c = color(i);
    return `<div style="text-align:center;min-width:96px;flex:1">`
      + `<div style="width:84px;height:84px;border-radius:50%;margin:0 auto;background:conic-gradient(${c} 0% ${v}%,#eef0f5 ${v}% 100%);display:flex;align-items:center;justify-content:center">`
      + `<div style="width:60px;height:60px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;color:${c}">${v}%</div></div>`
      + `<div style="font-size:12px;color:#475569;margin-top:9px;word-break:keep-all">${esc(x.label)}</div></div>`;
  }).join('');
  return wrap(`<div style="display:flex;flex-wrap:wrap;gap:14px;justify-content:center">${cells}</div>`);
}
// 4) 스탯 카드 그리드
function statCards(d) {
  const cells = d.map((x, i) => `<div style="flex:1;min-width:120px;background:#f8fafc;border:1px solid #eef0f5;border-left:3px solid ${color(i)};border-radius:10px;padding:16px 14px">`
    + `<div style="font-size:26px;font-weight:800;color:${color(i)};line-height:1">${clamp(x.value)}%</div>`
    + `<div style="font-size:12.5px;color:#475569;margin-top:6px;word-break:keep-all">${esc(x.label)}</div></div>`).join('');
  return wrap(`<div style="display:flex;flex-wrap:wrap;gap:12px">${cells}</div>`);
}
// 5) 랭킹 리스트(메달)
function rankingList(d) {
  const sorted = d.map((x, i) => ({ ...x, _i: i })).sort((a, b) => b.value - a.value);
  const medal = ['linear-gradient(135deg,#fbbf24,#f59e0b)', 'linear-gradient(135deg,#cbd5e1,#94a3b8)', 'linear-gradient(135deg,#d6a06a,#b45309)'];
  const rows = sorted.map((x, r) => `<div style="display:flex;align-items:center;gap:12px;padding:10px 12px;background:${r % 2 ? '#fff' : '#f8fafc'};border-radius:10px;margin:6px 0">`
    + `<span style="width:26px;height:26px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#fff;background:${medal[r] || '#c7cdda'}">${r + 1}</span>`
    + `<span style="flex:1;font-size:14px;font-weight:600;color:#1f2937">${esc(x.label)}</span>`
    + `<span style="font-size:15px;font-weight:800;color:${BRAND}">${clamp(x.value)}%</span></div>`).join('');
  return wrap(rows);
}
// 6) 반원 게이지(대표 1개) + 리스트
function gaugeList(d) {
  const top = d.reduce((a, b) => (b.value > a.value ? b : a), d[0]);
  const v = clamp(top.value), deg = Math.round(180 * v / 100);
  const gauge = `<div style="text-align:center;margin-bottom:8px">`
    + `<div style="width:180px;height:90px;margin:0 auto;border-radius:90px 90px 0 0;overflow:hidden;position:relative;background:conic-gradient(from 270deg,${BRAND} 0deg ${deg}deg,#eef0f5 ${deg}deg 180deg)">`
    + `<div style="position:absolute;left:18px;right:18px;bottom:0;top:18px;background:#fff;border-radius:90px 90px 0 0"></div>`
    + `<div style="position:absolute;left:0;right:0;bottom:6px;text-align:center;font-size:24px;font-weight:800;color:${BRAND}">${v}%</div></div>`
    + `<div style="font-size:13px;color:#475569;margin-top:6px">${esc(top.label)}</div></div>`;
  const rest = d.filter((x) => x !== top).map((x) => `<div style="display:flex;align-items:center;gap:10px;margin:6px 0;font-size:13px">`
    + `<span style="width:130px;color:#475569">${esc(x.label)}</span>`
    + `<span style="flex:1;height:8px;background:#eef0f5;border-radius:8px;overflow:hidden"><span style="display:block;height:100%;width:${clamp(x.value)}%;background:#a5b4fc"></span></span>`
    + `<span style="width:40px;text-align:right;font-weight:700;color:#64748b">${clamp(x.value)}%</span></div>`).join('');
  return wrap(gauge + rest);
}
// 7) 점(도트) 스케일 미터 — 10칸
function dotMeter(d) {
  const rows = d.map((x, i) => {
    const filled = Math.round(clamp(x.value) / 10);
    let dots = '';
    for (let k = 0; k < 10; k++) dots += `<span style="width:14px;height:14px;border-radius:50%;background:${k < filled ? color(i) : '#e6e8f0'}"></span>`;
    return `<div style="display:flex;align-items:center;gap:12px;margin:9px 0">`
      + `<span style="width:140px;font-size:13px;font-weight:600;color:#334155;flex-shrink:0">${esc(x.label)}</span>`
      + `<span style="display:flex;gap:5px;flex:1">${dots}</span>`
      + `<span style="width:42px;text-align:right;font-weight:700;color:${color(i)}">${clamp(x.value)}%</span></div>`;
  }).join('');
  return wrap(rows);
}
// 8) 분할 비교 막대(라벨 위 + 값 안)
function insetBars(d) {
  const rows = d.map((x, i) => `<div style="margin:10px 0">`
    + `<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px"><span style="font-weight:600;color:#334155">${esc(x.label)}</span><span style="font-weight:800;color:${color(i)}">${clamp(x.value)}%</span></div>`
    + `<div style="height:24px;background:#eef0f5;border-radius:7px;overflow:hidden"><div style="height:100%;width:${clamp(x.value)}%;background:linear-gradient(90deg,${color(i)},#a5b4fc);border-radius:7px"></div></div></div>`).join('');
  return wrap(rows);
}
// 9) 스텝 진행(타임라인 노드)
function stepFlow(d) {
  const nodes = d.map((x, i) => `<div style="flex:1;min-width:0;text-align:center;position:relative">`
    + `<div style="width:46px;height:46px;border-radius:50%;margin:0 auto;background:${color(i)};color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;box-shadow:0 6px 16px ${color(i)}40">${clamp(x.value)}%</div>`
    + `<div style="font-size:12px;color:#475569;margin-top:8px;word-break:keep-all">${esc(x.label)}</div></div>`).join('<div style="flex:0 0 24px;align-self:flex-start;margin-top:20px;color:#c7cdda;text-align:center">→</div>');
  return wrap(`<div style="display:flex;align-items:flex-start;gap:4px">${nodes}</div>`);
}
// 10) 버블 스케일(값 크기 = 원 크기)
function bubbleScale(d) {
  const cells = d.map((x, i) => {
    const sz = 44 + Math.round(clamp(x.value) / 100 * 52);
    return `<div style="text-align:center;flex:1;min-width:96px">`
      + `<div style="width:${sz}px;height:${sz}px;border-radius:50%;margin:0 auto;background:radial-gradient(circle at 35% 30%,#a5b4fc,${color(i)});color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800">${clamp(x.value)}%</div>`
      + `<div style="font-size:12px;color:#475569;margin-top:8px;word-break:keep-all">${esc(x.label)}</div></div>`;
  }).join('');
  return wrap(`<div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:center;min-height:120px">${cells}</div>`);
}

// 11) 레이더(펜타곤) 차트 — 다축 비교
function radar(d) {
  const n = d.length; if (n < 3) return verticalColumns(d);
  const cx = 130, cy = 130, R = 92;
  const pt = (i, frac) => { const ang = -Math.PI / 2 + i * 2 * Math.PI / n; return [cx + Math.cos(ang) * R * frac, cy + Math.sin(ang) * R * frac]; };
  let rings = '', axes = '', labels = ''; const poly = [];
  for (let g = 1; g <= 4; g++) { const rp = []; for (let k = 0; k < n; k++) { const p = pt(k, g / 4); rp.push(`${p[0].toFixed(1)},${p[1].toFixed(1)}`); } rings += `<polygon points="${rp.join(' ')}" fill="none" stroke="#e5e8f0" stroke-width="1"/>`; }
  for (let i = 0; i < n; i++) { const edge = pt(i, 1); axes += `<line x1="${cx}" y1="${cy}" x2="${edge[0].toFixed(1)}" y2="${edge[1].toFixed(1)}" stroke="#e5e8f0" stroke-width="1"/>`;
    const vp = pt(i, clamp(d[i].value) / 100); poly.push(`${vp[0].toFixed(1)},${vp[1].toFixed(1)}`);
    const lp = pt(i, 1.17); labels += `<text x="${lp[0].toFixed(1)}" y="${lp[1].toFixed(1)}" font-size="11" fill="#475569" text-anchor="middle" dominant-baseline="middle">${esc(d[i].label)}</text>`; }
  const dots = d.map((x, i) => { const vp = pt(i, clamp(x.value) / 100); return `<circle cx="${vp[0].toFixed(1)}" cy="${vp[1].toFixed(1)}" r="3.5" fill="${BRAND}"/>`; }).join('');
  return wrap(`<svg viewBox="0 0 260 260" width="100%" style="max-width:320px;display:block;margin:0 auto">${rings}${axes}<polygon points="${poly.join(' ')}" fill="${BRAND}33" stroke="${BRAND}" stroke-width="2"/>${dots}${labels}</svg>`);
}
// 12) 라인/에어리어 차트 — 추이
function areaLine(d) {
  const n = d.length; if (n < 2) return statCards(d);
  const W = 300, H = 152, pad = 26, mx = Math.max(...d.map((x) => x.value), 100), gid = 'vla' + hashSeed(d.map((x) => x.label).join('|'));
  const X = (i) => pad + i * (W - 2 * pad) / (n - 1);
  const Y = (v) => H - pad - (clamp(v / mx * 100) / 100) * (H - 2 * pad);
  const pts = d.map((x, i) => `${X(i).toFixed(1)},${Y(x.value).toFixed(1)}`);
  const area = `M${X(0).toFixed(1)},${H - pad} L${pts.join(' L')} L${X(n - 1).toFixed(1)},${H - pad} Z`;
  const dots = d.map((x, i) => `<circle cx="${X(i).toFixed(1)}" cy="${Y(x.value).toFixed(1)}" r="3.5" fill="#fff" stroke="${BRAND}" stroke-width="2"/>`).join('');
  const labels = d.map((x, i) => `<text x="${X(i).toFixed(1)}" y="${H - 7}" font-size="10" fill="#94a3b8" text-anchor="middle">${esc(x.label)}</text>`).join('');
  return wrap(`<svg viewBox="0 0 ${W} ${H}" width="100%" style="display:block"><defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${BRAND}" stop-opacity="0.28"/><stop offset="1" stop-color="${BRAND}" stop-opacity="0"/></linearGradient></defs><path d="${area}" fill="url(#${gid})"/><path d="M${pts.join(' L')}" fill="none" stroke="${BRAND}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>${dots}${labels}</svg>`);
}

// 13) 육각 배지
function hexBadge(d) {
  return wrap(`<div style="display:flex;flex-wrap:wrap;gap:16px;justify-content:center">${d.map((x, i) => `<div style="text-align:center;min-width:92px;flex:1"><div style="width:78px;height:86px;margin:0 auto;background:linear-gradient(135deg,${color(i)},#a5b4fc);clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%);display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:800">${clamp(x.value)}%</div><div style="font-size:12px;color:#475569;margin-top:9px;word-break:keep-all">${esc(x.label)}</div></div>`).join('')}</div>`);
}
// 14) 분절 필 트랙
function pillTrack(d) {
  return wrap(d.map((x, i) => { const filled = Math.round(clamp(x.value) / 5); let seg = ''; for (let k = 0; k < 20; k++) seg += `<span style="flex:1;height:16px;background:${k < filled ? color(i) : '#e9ebf3'}"></span>`; return `<div style="margin:10px 0"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px"><span style="font-weight:600;color:#334155;word-break:keep-all">${esc(x.label)}</span><span style="font-weight:800;color:${color(i)}">${clamp(x.value)}%</span></div><div style="display:flex;gap:2px;border-radius:9px;overflow:hidden">${seg}</div></div>`; }).join(''));
}
// 15) 롤리팝
function lollipop(d) {
  return wrap(d.map((x, i) => `<div style="display:flex;align-items:center;gap:12px;margin:11px 0"><span style="width:150px;font-size:13px;font-weight:600;color:#334155;flex-shrink:0;word-break:keep-all">${esc(x.label)}</span><span style="flex:1;position:relative;height:22px;display:flex;align-items:center"><span style="position:absolute;left:0;height:3px;width:${clamp(x.value)}%;background:#c7cdda"></span><span style="position:absolute;left:calc(${clamp(x.value)}% - 11px);width:22px;height:22px;border-radius:50%;background:${color(i)};box-shadow:0 3px 8px ${color(i)}55"></span></span><span style="width:52px;text-align:right;font-weight:800;color:${color(i)}">${clamp(x.value)}%</span></div>`).join(''));
}
// 16) 히트 그리드
function heatGrid(d) {
  return wrap(`<div style="display:flex;flex-wrap:wrap;gap:10px">${d.map((x, i) => { const a = 0.25 + clamp(x.value) / 100 * 0.75; return `<div style="flex:1;min-width:104px;border-radius:12px;padding:18px 14px;background:${color(i)};opacity:${a.toFixed(2)};color:#fff"><div style="font-size:22px;font-weight:800;line-height:1">${clamp(x.value)}%</div><div style="font-size:12px;margin-top:6px;opacity:.95;word-break:keep-all">${esc(x.label)}</div></div>`; }).join('')}</div>`);
}

function wrap(inner) {
  return `<div style="margin:28px 0;padding:22px 20px;background:#fdfdff;border:1px solid #eef0f5;border-radius:14px">${inner}</div>`;
}

const RENDERERS = [horizontalBars, verticalColumns, progressRings, statCards, rankingList,
  gaugeList, dotMeter, insetBars, stepFlow, bubbleScale, radar, areaLine, hexBadge, pillTrack, lollipop, heatGrid];

// ── 데이터 추출: AI가 만든 표준 막대그래프 블록 → [{label,value}] ──
function extractChart(html) {
  // 막대 행 패턴: width:140px 라벨 span ... 안쪽 막대 width:NN%
  const rowRe = /width:140px[^>]*>([^<]*)<\/span>[\s\S]*?height:18px;width:(\d{1,3})%/g;
  const data = []; let m;
  while ((m = rowRe.exec(html))) {
    const label = m[1].replace(/&amp;/g, '&').trim();
    const value = parseInt(m[2], 10);
    if (label && !isNaN(value)) data.push({ label, value });
  }
  return data;
}

// 원본 차트 컨테이너(<div style="margin:24px 0"> ... </div>) 범위 찾기
function findChartBlock(html) {
  const start = html.indexOf('<div style="margin:24px 0">');
  if (start === -1) return null;
  // 균형 맞춰 닫는 </div> 탐색
  let i = start, depth = 0;
  const openRe = /<div\b/g, closeRe = /<\/div>/g;
  let cursor = start;
  while (cursor < html.length) {
    const nextOpen = html.indexOf('<div', cursor);
    const nextClose = html.indexOf('</div>', cursor);
    if (nextClose === -1) return null;
    if (nextOpen !== -1 && nextOpen < nextClose) { depth++; cursor = nextOpen + 4; }
    else { depth--; cursor = nextClose + 6; if (depth === 0) return { start, end: cursor }; }
  }
  return null;
}

/**
 * 글 HTML의 표준 막대그래프를 10종 중 하나로 회전 교체.
 * @param {string} html  생성된 글 본문
 * @param {number} [seed]  회전 인덱스(없으면 랜덤). 같은 글에 일관 적용하려면 id 해시 전달.
 */
function diversifyInfographic(html, seed) {
  try {
    const data = extractChart(html);
    if (data.length < 2) return html;            // 차트 없음/파싱 실패 → 원본 유지
    const block = findChartBlock(html);
    if (!block) return html;
    const idx = (typeof seed === 'number' ? seed : Math.floor(Math.random() * RENDERERS.length)) % RENDERERS.length;
    const rendered = RENDERERS[idx](data);
    return html.slice(0, block.start) + rendered + html.slice(block.end);
  } catch (e) { return html; }
}

// 문자열 → 안정적 정수 해시(글 id로 결정적 회전용)
function hashSeed(s) {
  let h = 0; const str = String(s || '');
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
  return Math.abs(h);
}

module.exports = { diversifyInfographic, hashSeed, RENDERERS, extractChart };
