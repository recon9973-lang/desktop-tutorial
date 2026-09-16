/* ═══════════════════════════════════════════════════════════════════
   AEO 언급현황 워드클라우드 — 2026-09-16
   라이브러리 없음. 화면에 먼저 그린 뒤 실제 크기를 재서 앉힌다
   (캔버스로 재면 CSS 와 어긋나 낱말이 겹친다 — 그 함정을 피한 구현).
   ═══════════════════════════════════════════════════════════════ */
"use strict";

export var KIND = {
  us:    { color:"#00ed64", weight:700, label:"우리 브랜드" },
  rival: { color:"#c98500", weight:600, label:"경쟁사" },
  term:  { color:"#8a9aa0", weight:400, label:"일반어" }
};

var esc = function(s){ return String(s).replace(/[&<>"]/g, function(c){
  return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); };
var fmt = function(n){ return Number(n).toLocaleString("ko-KR"); };

/* box  : .mk-cloud 요소
   words: [{t:"말", n:언급수, k:"us"|"rival"|"term"}]
   한 번 더 부르면 다시 앉힌다(창 크기 바뀔 때). */
export function drawCloud(box, words){
  if(!box) return 0;
  var W = box.clientWidth, H = box.clientHeight;
  if(!W || !H) return 0;                     /* 부모가 높이를 안 주면 0 이 된다 */

  var ns = words.map(function(w){ return w.n; });
  var lo = Math.min.apply(null, ns), hi = Math.max.apply(null, ns);
  var k = Math.min(1, W / 900), MIN = 12 * k + 2, MAX = 44 * k;
  var size = function(n){
    var r = (Math.sqrt(n) - Math.sqrt(lo)) / (Math.sqrt(hi) - Math.sqrt(lo) || 1);
    return Math.round(MIN + r * (MAX - MIN));
  };

  var sorted = words.slice().sort(function(a,b){ return b.n - a.n; });
  box.innerHTML = sorted.map(function(w){
    return '<span class="w ' + w.k + '" data-k="' + w.k + '" data-n="' + w.n + '"' +
      ' style="visibility:hidden;left:0;top:0;font-size:' + size(w.n) + 'px"' +
      ' title="' + esc(w.t) + ' · ' + fmt(w.n) + '회">' + esc(w.t) + '</span>';
  }).join("");

  var els = box.querySelectorAll(".w"), placed = [], put = 0;
  var cx = W / 2, cy = H / 2, wide = (W / H) > 1.7;

  for(var i = 0; i < els.length; i++){
    var el = els[i];
    var tw = el.offsetWidth + 10, th = el.offsetHeight + 8;
    var spot = null;
    for(var t = 0; t < 3200; t++){                 /* 아르키메데스 나선 */
      var ang = t * 0.2, rad = 3.0 * ang * (wide ? 1.35 : 1);
      var x = cx + Math.cos(ang) * rad, y = cy + Math.sin(ang) * rad * 0.62;
      if(x - tw/2 < 4 || y - th/2 < 2 || x + tw/2 > W - 4 || y + th/2 > H - 2) continue;
      var hit = false;
      for(var j = 0; j < placed.length; j++){
        var q = placed[j];
        if(x - tw/2 < q.x2 && x + tw/2 > q.x1 && y - th/2 < q.y2 && y + th/2 > q.y1){ hit = true; break; }
      }
      if(!hit){
        placed.push({x1:x-tw/2, y1:y-th/2, x2:x+tw/2, y2:y+th/2});
        spot = {x:x, y:y};
        break;
      }
    }
    if(spot){
      el.style.left = spot.x.toFixed(1) + "px";
      el.style.top  = spot.y.toFixed(1) + "px";
      el.style.visibility = "visible";
      put++;
    } else {
      el.remove();          /* 자리가 없으면 안 넣는다 — 겹쳐 두지 않는다 */
    }
  }
  return put;               /* 앉힌 개수. words.length 보다 적으면 칸이 좁은 것 */
}

/* 범례 — 색 + 이름 + 합계. 누르면 그 갈래만 남는다. */
export function legendHTML(words, withTableToggle){
  var tot = {us:0, rival:0, term:0};
  words.forEach(function(w){ tot[w.k] += w.n; });
  var out = Object.keys(KIND).map(function(k){
    return '<button type="button" class="lg" data-k="' + k + '" aria-pressed="false">' +
      '<i style="background:' + KIND[k].color + '"></i>' + KIND[k].label +
      ' <b>' + fmt(tot[k]) + '</b></button>';
  }).join("");
  if(withTableToggle !== false) out += '<button type="button" class="sw" data-role="swap">표 보기</button>';
  return out;
}

/* 정확한 수는 표로 — 구름은 눈대중, 표는 값이다 */
export function tableHTML(words){
  var rows = words.slice().sort(function(a,b){ return b.n - a.n; }).map(function(w,i){
    return '<tr><td class="n">' + (i+1) + '</td>' +
      '<td title="' + esc(w.t) + '"><span class="mk-dot" style="background:' +
        KIND[w.k].color + '"></span>' + esc(w.t) + '</td>' +
      '<td>' + KIND[w.k].label + '</td>' +
      '<td class="n">' + fmt(w.n) + '</td></tr>';
  }).join("");
  return '<table class="mk-table">' +
    '<colgroup><col style="width:44px"><col><col style="width:96px"><col style="width:64px"></colgroup>' +
    '<thead><tr><th class="n">#</th><th>말</th><th>갈래</th><th class="n">언급</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>';
}
