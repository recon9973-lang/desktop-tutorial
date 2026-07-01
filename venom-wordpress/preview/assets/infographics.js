/*!
 * VENOM Infographics — 브라우저용 인포그래픽 렌더러 16종 (블로그 + 사이트 내부 콘텐츠 공용)
 *   data-vshape로 특정 모양 고정: 숫자(회전 인덱스) 또는 이름(radar·areaLine·verticalColumns 등)
 * 사용(HTML): <div data-vinfo='[{"label":"신환 증가","value":320},{"label":"재계약률","value":98}]'></div>
 *   (value는 0~100 권장. 100 초과 값은 라벨에 원값 표기하고 막대는 상대 스케일)
 * 렌더: VInfo.scan(root)  — data-vinfo 요소를 찾아 모양을 결정적 회전 렌더.
 *       VInfo.render(data, seed) — HTML 문자열 반환.
 * 모양이 콘텐츠마다 달라지도록 요소 순서/라벨 해시로 렌더러를 회전 선택한다.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.VInfo = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var BRAND = '#533afd';
  var PALETTE = ['#533afd', '#7c3aed', '#6366f1', '#8b5cf6', '#4f46e5', '#a78bfa'];
  var clamp = function (v) { return Math.max(0, Math.min(100, Math.round(v))); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); };
  var color = function (i) { return PALETTE[i % PALETTE.length]; };
  // value가 100 초과 지표(예: 320%)여도 막대는 상대 스케일, 숫자는 원값 표기
  var pct = function (x, max) { return clamp((x.value / (max || 100)) * 100); };
  var num = function (x) { return (x.suffix != null ? x.value + x.suffix : (x.value <= 100 ? x.value + '%' : x.value + '')); };
  var maxOf = function (d) { return Math.max.apply(null, d.map(function (x) { return x.value; }).concat([100])); };

  function wrap(inner) {
    return '<div style="margin:26px 0;padding:22px 20px;background:#fdfdff;border:1px solid #eef0f5;border-radius:14px">' + inner + '</div>';
  }

  // 1) 가로 막대
  function horizontalBars(d) { var mx = maxOf(d);
    return wrap(d.map(function (x, i) { return '<div style="display:flex;align-items:center;gap:12px;margin:9px 0">'
      + '<span style="width:150px;font-size:13px;font-weight:600;color:#334155;flex-shrink:0;word-break:keep-all">' + esc(x.label) + '</span>'
      + '<span style="flex:1;background:#eef0f5;border-radius:6px;overflow:hidden"><span style="display:block;height:20px;width:' + pct(x, mx) + '%;background:linear-gradient(90deg,' + BRAND + ',#818cf8);border-radius:6px"></span></span>'
      + '<span style="width:52px;font-size:13px;font-weight:700;text-align:right;color:' + BRAND + ';flex-shrink:0">' + num(x) + '</span></div>'; }).join('')); }
  // 2) 세로 막대
  function verticalColumns(d) { var mx = maxOf(d);
    return wrap('<div style="display:flex;gap:10px;align-items:flex-end">' + d.map(function (x, i) { return '<div style="flex:1;min-width:0;text-align:center">'
      + '<div style="font-size:13px;font-weight:800;color:' + color(i) + ';margin-bottom:6px">' + num(x) + '</div>'
      + '<div style="height:140px;display:flex;align-items:flex-end;justify-content:center"><div style="width:60%;max-width:40px;height:' + pct(x, mx) + '%;background:linear-gradient(180deg,' + color(i) + ',#a5b4fc);border-radius:7px 7px 0 0"></div></div>'
      + '<div style="font-size:12px;color:#475569;margin-top:8px;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('') + '</div>'); }
  // 3) 진행 링(도넛) 그리드
  function progressRings(d) {
    return wrap('<div style="display:flex;flex-wrap:wrap;gap:14px;justify-content:center">' + d.map(function (x, i) { var v = clamp(x.value), c = color(i);
      return '<div style="text-align:center;min-width:96px;flex:1">'
      + '<div style="width:84px;height:84px;border-radius:50%;margin:0 auto;background:conic-gradient(' + c + ' 0% ' + v + '%,#eef0f5 ' + v + '% 100%);display:flex;align-items:center;justify-content:center">'
      + '<div style="width:60px;height:60px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:800;color:' + c + '">' + num(x) + '</div></div>'
      + '<div style="font-size:12px;color:#475569;margin-top:9px;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('') + '</div>'); }
  // 4) 스탯 카드
  function statCards(d) {
    return wrap('<div style="display:flex;flex-wrap:wrap;gap:12px">' + d.map(function (x, i) { return '<div style="flex:1;min-width:120px;background:#f8fafc;border:1px solid #eef0f5;border-left:3px solid ' + color(i) + ';border-radius:10px;padding:16px 14px">'
      + '<div style="font-size:26px;font-weight:800;color:' + color(i) + ';line-height:1">' + num(x) + '</div>'
      + '<div style="font-size:12.5px;color:#475569;margin-top:6px;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('') + '</div>'); }
  // 5) 랭킹(메달)
  function rankingList(d) {
    var sorted = d.map(function (x, i) { return { label: x.label, value: x.value, suffix: x.suffix }; }).sort(function (a, b) { return b.value - a.value; });
    var medal = ['linear-gradient(135deg,#fbbf24,#f59e0b)', 'linear-gradient(135deg,#cbd5e1,#94a3b8)', 'linear-gradient(135deg,#d6a06a,#b45309)'];
    return wrap(sorted.map(function (x, r) { return '<div style="display:flex;align-items:center;gap:12px;padding:10px 12px;background:' + (r % 2 ? '#fff' : '#f8fafc') + ';border-radius:10px;margin:6px 0">'
      + '<span style="width:26px;height:26px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#fff;background:' + (medal[r] || '#c7cdda') + '">' + (r + 1) + '</span>'
      + '<span style="flex:1;font-size:14px;font-weight:600;color:#1f2937;word-break:keep-all">' + esc(x.label) + '</span>'
      + '<span style="font-size:15px;font-weight:800;color:' + BRAND + '">' + num(x) + '</span></div>'; }).join('')); }
  // 6) 반원 게이지 + 리스트
  function gaugeList(d) {
    var top = d.reduce(function (a, b) { return b.value > a.value ? b : a; }, d[0]);
    var v = clamp(top.value), deg = Math.round(180 * v / 100);
    var gauge = '<div style="text-align:center;margin-bottom:8px"><div style="width:180px;height:90px;margin:0 auto;border-radius:90px 90px 0 0;overflow:hidden;position:relative;background:conic-gradient(from 270deg,' + BRAND + ' 0deg ' + deg + 'deg,#eef0f5 ' + deg + 'deg 180deg)">'
      + '<div style="position:absolute;left:18px;right:18px;bottom:0;top:18px;background:#fff;border-radius:90px 90px 0 0"></div>'
      + '<div style="position:absolute;left:0;right:0;bottom:6px;text-align:center;font-size:22px;font-weight:800;color:' + BRAND + '">' + num(top) + '</div></div>'
      + '<div style="font-size:13px;color:#475569;margin-top:6px">' + esc(top.label) + '</div></div>';
    var rest = d.filter(function (x) { return x !== top; }).map(function (x) { return '<div style="display:flex;align-items:center;gap:10px;margin:6px 0;font-size:13px">'
      + '<span style="width:140px;color:#475569;word-break:keep-all">' + esc(x.label) + '</span>'
      + '<span style="flex:1;height:8px;background:#eef0f5;border-radius:8px;overflow:hidden"><span style="display:block;height:100%;width:' + clamp(x.value) + '%;background:#a5b4fc"></span></span>'
      + '<span style="width:46px;text-align:right;font-weight:700;color:#64748b">' + num(x) + '</span></div>'; }).join('');
    return wrap(gauge + rest); }
  // 7) 도트 미터
  function dotMeter(d) {
    return wrap(d.map(function (x, i) { var filled = Math.round(clamp(x.value) / 10), dots = '';
      for (var k = 0; k < 10; k++) dots += '<span style="width:14px;height:14px;border-radius:50%;background:' + (k < filled ? color(i) : '#e6e8f0') + '"></span>';
      return '<div style="display:flex;align-items:center;gap:12px;margin:9px 0">'
        + '<span style="width:150px;font-size:13px;font-weight:600;color:#334155;flex-shrink:0;word-break:keep-all">' + esc(x.label) + '</span>'
        + '<span style="display:flex;gap:5px;flex:1">' + dots + '</span>'
        + '<span style="width:48px;text-align:right;font-weight:700;color:' + color(i) + '">' + num(x) + '</span></div>'; }).join('')); }
  // 8) 분할 비교 막대
  function insetBars(d) { var mx = maxOf(d);
    return wrap(d.map(function (x, i) { return '<div style="margin:10px 0">'
      + '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px"><span style="font-weight:600;color:#334155;word-break:keep-all">' + esc(x.label) + '</span><span style="font-weight:800;color:' + color(i) + '">' + num(x) + '</span></div>'
      + '<div style="height:24px;background:#eef0f5;border-radius:7px;overflow:hidden"><div style="height:100%;width:' + pct(x, mx) + '%;background:linear-gradient(90deg,' + color(i) + ',#a5b4fc);border-radius:7px"></div></div></div>'; }).join('')); }
  // 9) 스텝 타임라인
  function stepFlow(d) {
    return wrap('<div style="display:flex;align-items:flex-start;gap:4px;flex-wrap:wrap">' + d.map(function (x, i) { return '<div style="flex:1;min-width:80px;text-align:center">'
      + '<div style="width:46px;height:46px;border-radius:50%;margin:0 auto;background:' + color(i) + ';color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;box-shadow:0 6px 16px ' + color(i) + '40">' + num(x) + '</div>'
      + '<div style="font-size:12px;color:#475569;margin-top:8px;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('<div style="flex:0 0 20px;align-self:flex-start;margin-top:20px;color:#c7cdda;text-align:center">→</div>') + '</div>'); }
  // 10) 버블 스케일
  function bubbleScale(d) { var mx = maxOf(d);
    return wrap('<div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:center;min-height:120px">' + d.map(function (x, i) { var sz = 44 + Math.round(pct(x, mx) / 100 * 52);
      return '<div style="text-align:center;flex:1;min-width:96px"><div style="width:' + sz + 'px;height:' + sz + 'px;border-radius:50%;margin:0 auto;background:radial-gradient(circle at 35% 30%,#a5b4fc,' + color(i) + ');color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800">' + num(x) + '</div>'
      + '<div style="font-size:12px;color:#475569;margin-top:8px;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('') + '</div>'); }
  // 11) 육각 뱃지(hexagon clip-path)
  function hexBadge(d) {
    return wrap('<div style="display:flex;flex-wrap:wrap;gap:16px;justify-content:center">' + d.map(function (x, i) { return '<div style="text-align:center;min-width:92px;flex:1">'
      + '<div style="width:78px;height:86px;margin:0 auto;background:linear-gradient(135deg,' + color(i) + ',#a5b4fc);clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%);display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:800">' + num(x) + '</div>'
      + '<div style="font-size:12px;color:#475569;margin-top:9px;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('') + '</div>'); }
  // 12) 분절 필 트랙(segmented pill)
  function pillTrack(d) {
    return wrap(d.map(function (x, i) { var filled = Math.round(clamp(x.value) / 5), seg = '';
      for (var k = 0; k < 20; k++) seg += '<span style="flex:1;height:16px;background:' + (k < filled ? color(i) : '#e9ebf3') + '"></span>';
      return '<div style="margin:10px 0"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px"><span style="font-weight:600;color:#334155;word-break:keep-all">' + esc(x.label) + '</span><span style="font-weight:800;color:' + color(i) + '">' + num(x) + '</span></div>'
      + '<div style="display:flex;gap:2px;border-radius:9px;overflow:hidden">' + seg + '</div></div>'; }).join('')); }
  // 13) 롤리팝(stem + dot)
  function lollipop(d) { var mx = maxOf(d);
    return wrap(d.map(function (x, i) { return '<div style="display:flex;align-items:center;gap:12px;margin:11px 0">'
      + '<span style="width:150px;font-size:13px;font-weight:600;color:#334155;flex-shrink:0;word-break:keep-all">' + esc(x.label) + '</span>'
      + '<span style="flex:1;position:relative;height:22px;display:flex;align-items:center"><span style="position:absolute;left:0;height:3px;width:' + pct(x, mx) + '%;background:#c7cdda"></span>'
      + '<span style="position:absolute;left:calc(' + pct(x, mx) + '% - 11px);width:22px;height:22px;border-radius:50%;background:' + color(i) + ';box-shadow:0 3px 8px ' + color(i) + '55"></span></span>'
      + '<span style="width:52px;text-align:right;font-weight:800;color:' + color(i) + '">' + num(x) + '</span></div>'; }).join('')); }
  // 14) 히트 그리드(intensity cells)
  function heatGrid(d) {
    return wrap('<div style="display:flex;flex-wrap:wrap;gap:10px">' + d.map(function (x, i) { var a = 0.25 + clamp(x.value) / 100 * 0.75;
      return '<div style="flex:1;min-width:104px;border-radius:12px;padding:18px 14px;background:' + color(i) + ';opacity:' + a.toFixed(2) + ';color:#fff">'
      + '<div style="font-size:22px;font-weight:800;line-height:1">' + num(x) + '</div>'
      + '<div style="font-size:12px;margin-top:6px;opacity:.95;word-break:keep-all">' + esc(x.label) + '</div></div>'; }).join('') + '</div>'); }

  // 15) 레이더(펜타곤) 차트 — 다축 비교(참고: 사업분야 레이더)
  function radar(d) {
    var n = d.length; if (n < 3) return verticalColumns(d);
    var cx = 130, cy = 130, R = 92;
    function pt(i, frac) { var ang = -Math.PI / 2 + i * 2 * Math.PI / n; return [cx + Math.cos(ang) * R * frac, cy + Math.sin(ang) * R * frac]; }
    var rings = '', axes = '', labels = '', poly = [];
    for (var g = 1; g <= 4; g++) { var rp = []; for (var k = 0; k < n; k++) { var p = pt(k, g / 4); rp.push(p[0].toFixed(1) + ',' + p[1].toFixed(1)); } rings += '<polygon points="' + rp.join(' ') + '" fill="none" stroke="#e5e8f0" stroke-width="1"/>'; }
    for (var i = 0; i < n; i++) { var edge = pt(i, 1); axes += '<line x1="' + cx + '" y1="' + cy + '" x2="' + edge[0].toFixed(1) + '" y2="' + edge[1].toFixed(1) + '" stroke="#e5e8f0" stroke-width="1"/>';
      var frac = clamp(d[i].value) / 100, vp = pt(i, frac); poly.push(vp[0].toFixed(1) + ',' + vp[1].toFixed(1));
      var lp = pt(i, 1.17); labels += '<text x="' + lp[0].toFixed(1) + '" y="' + lp[1].toFixed(1) + '" font-size="11" fill="#475569" text-anchor="middle" dominant-baseline="middle">' + esc(d[i].label) + '</text>'; }
    var dots = d.map(function (x, i) { var vp = pt(i, clamp(x.value) / 100); return '<circle cx="' + vp[0].toFixed(1) + '" cy="' + vp[1].toFixed(1) + '" r="3.5" fill="' + BRAND + '"/>'; }).join('');
    return wrap('<svg viewBox="0 0 260 260" width="100%" style="max-width:320px;display:block;margin:0 auto">' + rings + axes
      + '<polygon points="' + poly.join(' ') + '" fill="' + BRAND + '33" stroke="' + BRAND + '" stroke-width="2"/>' + dots + labels + '</svg>'); }
  // 16) 라인/에어리어 차트 — 추이(참고: 월별 순이익 라인)
  function areaLine(d) {
    var n = d.length; if (n < 2) return statCards(d);
    var W = 300, H = 152, pad = 26, mx = maxOf(d), gid = 'vla' + hashSeed(d.map(function (x) { return x.label; }).join('|'));
    function X(i) { return pad + i * (W - 2 * pad) / (n - 1); }
    function Y(v) { return H - pad - (clamp(v / mx * 100) / 100) * (H - 2 * pad); }
    var pts = d.map(function (x, i) { return X(i).toFixed(1) + ',' + Y(x.value).toFixed(1); });
    var area = 'M' + X(0).toFixed(1) + ',' + (H - pad) + ' L' + pts.join(' L') + ' L' + X(n - 1).toFixed(1) + ',' + (H - pad) + ' Z';
    var dots = d.map(function (x, i) { return '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(x.value).toFixed(1) + '" r="3.5" fill="#fff" stroke="' + BRAND + '" stroke-width="2"/>'; }).join('');
    var labels = d.map(function (x, i) { return '<text x="' + X(i).toFixed(1) + '" y="' + (H - 7) + '" font-size="10" fill="#94a3b8" text-anchor="middle">' + esc(x.label) + '</text>'; }).join('');
    return wrap('<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="display:block">'
      + '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + BRAND + '" stop-opacity="0.28"/><stop offset="1" stop-color="' + BRAND + '" stop-opacity="0"/></linearGradient></defs>'
      + '<path d="' + area + '" fill="url(#' + gid + ')"/>'
      + '<path d="M' + pts.join(' L') + '" fill="none" stroke="' + BRAND + '" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
      + dots + labels + '</svg>'); }

  var RENDERERS = [horizontalBars, verticalColumns, progressRings, statCards, rankingList,
    gaugeList, dotMeter, insetBars, stepFlow, bubbleScale, hexBadge, pillTrack, lollipop, heatGrid, radar, areaLine];
  var NAMED = { horizontalBars: horizontalBars, verticalColumns: verticalColumns, progressRings: progressRings, statCards: statCards, rankingList: rankingList, gaugeList: gaugeList, dotMeter: dotMeter, insetBars: insetBars, stepFlow: stepFlow, bubbleScale: bubbleScale, hexBadge: hexBadge, pillTrack: pillTrack, lollipop: lollipop, heatGrid: heatGrid, radar: radar, areaLine: areaLine };

  function hashSeed(s) { var h = 0, str = String(s || ''); for (var i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0; return Math.abs(h); }

  function render(data, seed) {
    if (!data || data.length < 1) return '';
    if (typeof seed === 'string' && NAMED[seed]) { try { return NAMED[seed](data); } catch (e) { return ''; } }
    var idx = (typeof seed === 'number' ? seed : hashSeed(data.map(function (x) { return x.label; }).join('|'))) % RENDERERS.length;
    try { return RENDERERS[idx](data); } catch (e) { return ''; }
  }

  // data-vinfo 요소들을 찾아 렌더(중복 방지 플래그). data-vshape로 특정 모양 고정 가능.
  function scan(rootEl) {
    var root = rootEl || document;
    var nodes = root.querySelectorAll ? root.querySelectorAll('[data-vinfo]:not([data-vdone])') : [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i], data;
      try { data = JSON.parse(el.getAttribute('data-vinfo')); } catch (e) { continue; }
      var shape = el.getAttribute('data-vshape');
      var seed = shape == null ? undefined : (/^\d+$/.test(shape) ? parseInt(shape, 10) : shape);
      el.innerHTML = render(data, seed);
      el.setAttribute('data-vdone', '1');
    }
  }

  return { render: render, scan: scan, hashSeed: hashSeed, RENDERERS: RENDERERS, count: RENDERERS.length };
});
