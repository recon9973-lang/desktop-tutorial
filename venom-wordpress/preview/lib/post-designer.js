'use strict';

// "GPT=글 / 클로드=디자인" 분리 구현.
// GPT가 만든 의미만 있는 평문 HTML(<h2>,<p>,<table>...)을 받아,
// 수기 작성 글과 동일한 베놈 브랜드 디자인(인라인 스타일)으로 변환한다.
// LLM 호출 없이 결정적으로 동작 → 추가 비용 0, 일관된 결과.

// ── 디자인 토큰(인라인 값; CSS 변수도 페이지 컨텍스트에서 동작) ──
const S = {
  lead:  'font-size:16.5px;color:var(--ink2);line-height:1.85;border-left:3px solid var(--p);padding:4px 0 4px 18px;margin:0 0 32px',
  p:     'color:var(--ink2);line-height:1.9;margin:0 0 20px',
  h2:    'font-size:23px;font-weight:700;color:var(--ink);margin:64px 0 20px;padding-bottom:10px;border-bottom:2px solid var(--soft);line-height:1.4',
  h3:    'font-size:19px;font-weight:600;color:var(--ink);margin:48px 0 14px;line-height:1.45',
  h4:    'font-size:17px;font-weight:600;color:var(--ink);margin:38px 0 12px',
  ul:    'color:var(--ink2);line-height:1.9;margin:18px 0 32px;padding-left:22px',
  ol:    'color:var(--ink2);line-height:1.9;margin:18px 0 32px;padding-left:22px',
  li:    'margin:0 0 14px',
  table: 'width:100%;border-collapse:collapse;font-size:14.5px;margin:8px 0',
  th:    'background:var(--soft);font-weight:600;padding:11px 14px;border:1px solid var(--border);text-align:left',
  td:    'padding:11px 14px;border:1px solid var(--border);text-align:left',
  blockquote: 'margin:32px 0;padding:16px 20px;border-left:4px solid var(--p);background:rgba(83,58,253,.05);border-radius:0 8px 8px 0;color:var(--ink2)',
  strong: 'color:var(--ink)',
};

// 여는 태그에 style이 없을 때만 스타일 주입(인라인 스타일이 이미 있으면 보존)
function addStyle(html, tag, style) {
  const re = new RegExp('<' + tag + '(?![a-z0-9])([^>]*)>', 'gi');
  return html.replace(re, (m, attrs) => {
    if (/\bstyle\s*=/i.test(attrs || '')) return m;
    return '<' + tag + (attrs || '') + ' style="' + style + '">';
  });
}

// 첫 번째 <p>만 리드(요약) 스타일로
function styleLead(html) {
  let done = false;
  return html.replace(/<p(?![a-z0-9])([^>]*)>/i, (m, attrs) => {
    if (done || /\bstyle\s*=/i.test(attrs || '')) return m;
    done = true;
    return '<p' + attrs + ' style="' + S.lead + '">';
  });
}

// 표를 가로 스크롤 컨테이너로 감싸 모바일 대응
function wrapTables(html) {
  return html
    .replace(/<table(?![a-z0-9])/gi, '<div style="overflow-x:auto;margin:24px 0"><table')
    .replace(/<\/table>/gi, '</table></div>');
}

// 실사 배경 배너형 CTA — 사진 위 반투명 오버레이 + 텍스트/버튼 (광고 배너 스타일)
const CTA_BLOCK =
  '<div style="position:relative;border-radius:16px;overflow:hidden;margin:56px 0 8px;min-height:200px">'
  + '<img src="/images/office.webp" alt="" loading="lazy" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">'
  + '<div style="position:absolute;inset:0;background:linear-gradient(100deg,rgba(13,27,46,.85) 0%,rgba(13,27,46,.62) 55%,rgba(28,30,84,.45) 100%)"></div>'
  + '<div style="position:relative;padding:38px 28px;text-align:center">'
  + '<h3 style="color:#fff;font-size:21px;font-weight:800;margin:0 0 10px;letter-spacing:-.02em">병원마케팅, 베놈과 상담하세요</h3>'
  + '<p style="color:rgba(255,255,255,.88);font-size:14px;line-height:1.7;margin:0 0 20px">베놈이 직접 집행한 데이터 기준으로 병원·의원 맞춤 GEO/SEO 전략을 제안드립니다.</p>'
  + '<a href="https://pf.kakao.com/_jxjxdcxj/chat" target="_blank" rel="noopener" style="display:inline-block;background:#fff;color:var(--p);font-weight:800;padding:13px 32px;border-radius:9999px;text-decoration:none;box-shadow:0 10px 26px rgba(0,0,0,.3)">💬 카카오 상담신청</a>'
  + '</div></div>';

/**
 * GPT 평문 HTML → 베놈 브랜드 디자인 HTML.
 * @param {string} html  GPT가 생성한 본문 HTML (JSON-LD/스크립트 미포함 권장)
 * @returns {string}
 */
function designPost(html) {
  if (!html || typeof html !== 'string') return '';
  let out = html;

  out = wrapTables(out);
  out = addStyle(out, 'h2', S.h2);
  out = addStyle(out, 'h3', S.h3);
  out = addStyle(out, 'h4', S.h4);
  out = addStyle(out, 'ul', S.ul);
  out = addStyle(out, 'ol', S.ol);
  out = addStyle(out, 'li', S.li);
  out = addStyle(out, 'th', S.th);
  out = addStyle(out, 'td', S.td);
  out = addStyle(out, 'table', S.table);
  out = addStyle(out, 'blockquote', S.blockquote);
  out = addStyle(out, 'strong', S.strong);

  // 리드 문단은 일반 <p> 스타일보다 먼저 지정한 뒤, 나머지 <p> 일괄 스타일
  out = styleLead(out);
  out = addStyle(out, 'p', S.p);

  // GPT가 카카오 CTA를 넣지 않았으면 표준 브랜드 CTA 박스 추가
  if (!/pf\.kakao\.com/i.test(out)) {
    out = out + CTA_BLOCK;
  }

  return out;
}

module.exports = { designPost };
