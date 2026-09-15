/* ═══════════════════════════════════════════════════════════════════
   가 · 지도에서 같은 과를 가른다 — 마커·범례
   2026-09-15 · 지도 라이브러리를 가리지 않는다.
   핀 그림을 data: URI 로 돌려주므로 카카오맵 MarkerImage 에 그대로 넣거나,
   직접 그리는 SVG 레이어에 붙여도 된다.
   ═══════════════════════════════════════════════════════════════ */
"use strict";

/* 뜻이 있는 색 — 지도·막대·표 배지가 전부 이 셋만 쓴다.
   [검증] dataviz 검증기 · 다크 면 #182226
          같은 과 ↔ 그 외 : 적록색약 ΔE 27.4 · 정상시력 ΔE 30.7 · 전 항목 통과 */
export const MARK = {
  same:  { color:"#c98500", label:"같은 과",    z:30 },  /* 채운 점 + 링 */
  other: { color:"#3987e5", label:"그 외 병의원", z:20 },  /* 속빈 점     */
  us:    { color:"#00ed64", label:"우리 병원",   z:40 }   /* 삼각 핀     */
};

/* 색만으로 가르지 않는다 — 모양이 함께 갈린다.
   kind: "same" | "other" | "us"
   반환: { url, size:[w,h], anchor:[x,y] } — 카카오맵 MarkerImage 인자 그대로 */
export function markerImage(kind, scale){
  const k = MARK[kind] || MARK.other;
  const s = scale || 1;
  let w, h, body;

  if(kind === "us"){
    w = 44; h = 44;
    body =
      '<circle cx="22" cy="22" r="19" fill="rgba(0,237,100,.10)" stroke="'+k.color+'" stroke-width="1.2" opacity=".6"/>' +
      '<path d="M22 36 L9 15 L35 15 Z" fill="'+k.color+'" stroke="#0d1417" stroke-width="2.4"/>';
  } else if(kind === "same"){
    w = 22; h = 22;
    body =
      '<circle cx="11" cy="11" r="5.6" fill="'+k.color+'" stroke="#111a1e" stroke-width="1.6"/>' +
      '<circle cx="11" cy="11" r="8.6" fill="none" stroke="'+k.color+'" stroke-width="1.2" opacity=".55"/>';
  } else {
    w = 14; h = 14;
    body = '<circle cx="7" cy="7" r="3.6" fill="none" stroke="'+k.color+'" stroke-width="1.6" opacity=".92"/>';
  }

  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="'+(w*s)+'" height="'+(h*s)+'" viewBox="0 0 '+w+' '+h+'">' +
    body + '</svg>';
  return {
    url: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    size: [w*s, h*s],
    anchor: [w*s/2, h*s/2],
    zIndex: k.z
  };
}

/* 범례 — 지도 위에 항상 떠 있다. 개수를 같이 적어 색을 못 가려도 읽힌다.
   counts: { same:Number, other:Number } */
export function legendHTML(counts){
  const n = v => Number(v).toLocaleString("ko-KR");
  return (
    '<span class="lg"><svg class="sw" viewBox="0 0 12 12" aria-hidden="true">' +
      '<circle cx="6" cy="6" r="3.4" fill="'+MARK.same.color+'"/>' +
      '<circle cx="6" cy="6" r="5.2" fill="none" stroke="'+MARK.same.color+'" stroke-width="1"/>' +
    '</svg>같은 과 <b>'+n(counts.same)+'</b></span>' +
    '<span class="lg"><svg class="sw" viewBox="0 0 12 12" aria-hidden="true">' +
      '<circle cx="6" cy="6" r="3.6" fill="none" stroke="'+MARK.other.color+'" stroke-width="1.6"/>' +
    '</svg>그 외 <b>'+n(counts.other)+'</b></span>' +
    '<span class="lg"><svg class="sw" viewBox="0 0 12 12" aria-hidden="true">' +
      '<path d="M6 10.5 L1.6 3.4 L10.4 3.4 Z" fill="'+MARK.us.color+'"/>' +
    '</svg>우리 병원</span>'
  );
}

/* 점 상한 — 3km 이상이면 반경 안 병의원이 1,000곳을 넘는다(실측: 3km 1,025 · 10km 3,736).
   군집 표기가 붙기 전까지는 상한을 넘을 때 띠를 띄워 「전부가 아니다」를 밝힌다. */
export const DOT_CAP = 240;
export function needsCluster(totalInRadius){ return totalInRadius > DOT_CAP; }

/* 같은 과 여부 판정 — 표 배지와 지도 마커가 같은 답을 쓰게 한 자리.
   두 곳에서 따로 판정하면 지도와 목록이 어긋난다.
   ours·theirs 는 심평원 표방 진료과목 배열. */
export function isSameDept(ours, theirs){
  if(!Array.isArray(ours) || !Array.isArray(theirs)) return false;
  const set = new Set(ours.map(s => String(s).trim()));
  return theirs.some(s => set.has(String(s).trim()));
}
