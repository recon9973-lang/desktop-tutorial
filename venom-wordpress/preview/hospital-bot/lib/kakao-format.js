'use strict';

// ============================================================
// kakao-format — 진단서 JSON → 카카오 i 오픈빌더 스킬 응답(SkillResponse v2.0)
// ------------------------------------------------------------
// · 발화 파싱: 병원명 + 뷰 명령(seo/geo/광고/플레이스/심의/상담).
// · 렌더: 종합 요약 + 뷰별 상세 카드 + quickReplies 버튼.
// · 응답형: { version:'2.0', template:{ outputs:[...], quickReplies:[...] } }
// 참고: 오픈빌더 simpleText ≤ 1000자, quickReplies ≤ 10개.
// ============================================================

const CHANNEL_URL = 'https://pf.kakao.com/_jxjxdcxj';
const TEL = '1661-4142';

// 웹 풀리포트 URL (VENOMI_SITE_BASE 설정 시에만 카드에 링크 노출)
function reportUrl(name) {
  const base = (process.env.VENOMI_SITE_BASE || '').replace(/\/+$/, '');
  if (!base) return null;
  return `${base}/hospital-bot/report.html?hospital=${encodeURIComponent(name)}`;
}
function reportLinkCard(name) {
  const url = reportUrl(name);
  if (!url) return null;
  return { textCard: { title: '📄 상세 웹 리포트', description: '점수·경쟁·처방을 웹에서 자세히 보고 PDF로 저장할 수 있어요.',
    buttons: [{ action: 'webLink', label: '웹 리포트 열기', webLinkUrl: url }] } };
}

// ── 발화 파싱 ─────────────────────────────────────────
const VIEW_KEYWORDS = [
  ['law', /(심의|광고법|의료법)$/],
  ['ads', /(광고|광고비|키워드|cpc)$/i],
  ['geo', /(geo|지오|ai검색|ai 검색)$/i],
  ['seo', /(seo|에스이오|검색최적화)$/i],
  ['local', /(플레이스|로컬|place|지도)$/i],
  ['contact', /^(상담|견적|문의|컨설팅)$/],
];

function parseCommand(utterance) {
  const s = String(utterance || '').trim().replace(/\s+/g, ' ');
  for (const [view, re] of VIEW_KEYWORDS) {
    if (re.test(s)) {
      if (view === 'contact') return { view: 'contact', hospital: '' };
      const hospital = s.replace(re, '').trim();
      if (hospital) return { view, hospital };
    }
  }
  return { view: 'summary', hospital: s };
}

// ── 응답 빌더 ─────────────────────────────────────────
function skill(outputs, quickReplies) {
  const template = { outputs };
  if (quickReplies && quickReplies.length) template.quickReplies = quickReplies.slice(0, 10);
  return { version: '2.0', template };
}
function simpleText(text) { return { simpleText: { text: clip(text, 1000) } }; }
function clip(s, n) { s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n - 1) + '…' : s; }

function qr(label, messageText) { return { label: clip(label, 14), action: 'message', messageText }; }
function qrLink(label, url) { return { label: clip(label, 14), action: 'webLink', webLinkUrl: url }; }

// 병원명 기준 뷰 전환 quickReplies
function viewQuickReplies(name) {
  return [
    qr('SEO 자세히', `${name} seo`),
    qr('GEO 자세히', `${name} geo`),
    qr('광고 제안', `${name} 광고`),
    qr('플레이스', `${name} 플레이스`),
    qr('무료 상담', '상담'),
  ];
}

// ── 아이콘/등급 ────────────────────────────────────────
function gradeIcon(g) {
  if (!g || g === 'N/A') return '·';
  if (g === 'A') return '🟢'; if (g === 'B') return '🔵';
  if (g === 'C') return '🟡'; if (g === 'D') return '🟠';
  return '🔴';
}
function scoreIcon(n) { return n == null ? '·' : n >= 80 ? '🟢' : n >= 60 ? '🟡' : '🔴'; }

// ── 뷰: 종합 요약 ──────────────────────────────────────
function renderSummary(report) {
  const name = displayName(report);
  const region = report.resolved && report.resolved.region;
  const s = report.summary || {};
  const L = [];
  L.push(`🩺 ${name}${region ? `(${region})` : ''} 마케팅 건강검진`);
  L.push('');
  L.push(`▪ 종합등급  ${gradeIcon(s.grade)} ${s.grade || 'N/A'}${s.score != null ? ` (${s.score}점)` : ''}`);
  L.push(`▪ SEO 홈페이지  ${line_seo(report.seo)}`);
  L.push(`▪ GEO·AI검색  ${line_geo(report.geo)}`);
  L.push(`▪ 네이버 로컬  ${line_local(report.local)}`);
  L.push(`▪ 광고 기회  ${line_ads_top(report.ads)}`);
  L.push(`▪ 의료광고법  ${line_law(report.adLaw)}`);
  if (s.urgent && s.urgent.length) {
    L.push('');
    L.push(`가장 시급: ${s.urgent.join(' / ')}`);
  }
  L.push('');
  L.push('※ 공개 데이터 기반 참고용 진단입니다.');
  const outputs = [simpleText(L.join('\n'))];
  const linkCard = reportLinkCard(name);
  if (linkCard) outputs.push(linkCard);
  return skill(outputs, viewQuickReplies(name));
}

function line_seo(seo) {
  if (!seo) return '·';
  if (seo.status === 'ok') return `${seo.score100}/100 ${scoreIcon(seo.score100)}`;
  if (seo.status === 'no-homepage') return '공식 홈페이지 미발견';
  if (seo.status === 'unavailable') return '측정 불가(PSI 키 확인)';
  return '측정 실패';
}
function line_geo(geo) {
  if (!geo) return '·';
  if (geo.status === 'done') return `${geo.grade || '·'} (인용률 ${pctText(geo.citationRate)})`;
  if (geo.status === 'ready') return "'geo' 명령으로 실측 ⏳";
  if (geo.status === 'unconfigured') return 'AI엔진 미설정';
  return '·';
}
function line_local(local) {
  if (!local) return '·';
  const parts = [];
  if (local.place && local.place.registered != null) parts.push(local.place.registered ? '플레이스 등록' : '플레이스 미등록');
  if (local.blog && local.blog.total != null) parts.push(`블로그 ${local.blog.total}건`);
  if (local.news && local.news.total != null) parts.push(`뉴스 ${local.news.total}건`);
  return parts.length ? parts.join(' · ') : '·';
}
function line_ads_top(ads) {
  if (!ads || ads.status !== 'ok' || !ads.keywords || !ads.keywords.length) {
    if (ads && ads.status === 'unconfigured') return '검색광고 API 미설정';
    return '·';
  }
  const k = ads.keywords[0];
  const cpc = k.cpc != null ? `·CPC ₩${fmtNum(k.cpc)}` : '';
  return `'${k.keyword}' 月${fmtNum(k.volume)}회·경쟁 ${k.competition}${cpc}`;
}
function line_law(law) {
  if (!law) return '·';
  if (law.status !== 'ok') return law.status === 'no-homepage' ? '홈페이지 미발견' : '스캔 불가';
  return law.pass ? '양호 🟢' : `주의 ${law.forbidden.length}건 ⚠`;
}

// ── 뷰: SEO 상세 ───────────────────────────────────────
function renderSeo(report) {
  const name = displayName(report);
  const seo = report.seo || {};
  if (seo.status !== 'ok') {
    return skill([simpleText(`🔎 ${name} SEO\n\n${line_seo(seo)}\n${seo.note || ''}`)], viewQuickReplies(name));
  }
  const sc = seo.scores || {};
  const L = [`🔎 ${name} SEO 진단`, ''];
  L.push(`종합 ${seo.score100}/100 ${scoreIcon(seo.score100)}`);
  L.push(`· 성능 ${valOr(sc.performance)} / SEO ${valOr(sc.seo)} / 접근성 ${valOr(sc.accessibility)}`);
  if (seo.lab && seo.lab.lcpMs) L.push(`· 최대콘텐츠표시(LCP) ${(seo.lab.lcpMs / 1000).toFixed(1)}초`);
  if (seo.topFixes && seo.topFixes.length) {
    L.push('');
    L.push('개선 우선순위:');
    seo.topFixes.forEach((f, i) => L.push(`${i + 1}. ${f}`));
  }
  L.push('');
  L.push(`대상: ${seo.url}`);
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name));
}

// ── 뷰: 광고 상세 ──────────────────────────────────────
function renderAds(report) {
  const name = displayName(report);
  const ads = report.ads || {};
  if (ads.status !== 'ok' || !ads.keywords || !ads.keywords.length) {
    const why = ads.status === 'unconfigured' ? '검색광고 API가 아직 연결되지 않았습니다.' : (ads.note || '데이터를 불러오지 못했습니다.');
    return skill([simpleText(`💰 ${name} 광고\n\n${why}`)], viewQuickReplies(name));
  }
  const hasCpc = ads.cpc && ads.cpc.status === 'ok';
  const L = [`💰 ${name} 광고 컨설팅`, '', hasCpc ? '키워드 · 월검색량 · 경쟁 · CPC' : '키워드 · 월검색량 · 경쟁도'];
  ads.keywords.slice(0, 6).forEach((k) => {
    const cpc = k.cpc != null ? `  ₩${fmtNum(k.cpc)}` : '';
    L.push(`• ${k.keyword}  ${fmtNum(k.volume)}회  (${k.competition})${cpc}`);
  });
  L.push('');
  L.push(hasCpc ? '※ CPC = 모바일 평균 2위 노출 추정 입찰가.' : '※ CPC(입찰가)는 검색광고 키 설정 시 표시됩니다.');
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name));
}

// ── 뷰: 로컬 상세 ──────────────────────────────────────
function renderLocal(report) {
  const name = displayName(report);
  const local = report.local || {};
  const L = [`📍 ${name} 네이버 로컬`, ''];
  L.push(`플레이스: ${local.place && local.place.registered != null ? (local.place.registered ? '등록 확인' : '미등록/미확인') : '·'}`);
  L.push(`블로그 노출: ${local.blog && local.blog.total != null ? fmtNum(local.blog.total) + '건' : '·'}`);
  L.push(`뉴스/PR: ${local.news && local.news.total != null ? fmtNum(local.news.total) + '건' : '·'}`);
  if (local.signals && local.signals.length) {
    L.push('');
    local.signals.forEach((s) => L.push(`· ${s}`));
  }
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name));
}

// ── 뷰: GEO 상세(P0) ──────────────────────────────────
function renderGeo(report) {
  const name = displayName(report);
  const geo = report.geo || {};

  if (geo.status === 'unconfigured') {
    return skill([simpleText(`🤖 ${name} GEO·AI검색\n\nAI 엔진 키가 설정되지 않아 실측할 수 없습니다.\n(PERPLEXITY/OPENAI/GEMINI/ANTHROPIC 중 1개 이상 필요)`)], viewQuickReplies(name));
  }
  if (geo.status === 'ready') {
    const L = [`🤖 ${name} GEO·AI검색`, '', `준비된 AI 엔진: ${(geo.engines || []).join(', ') || '·'}`, '', '진단 질문(예):'];
    (geo.prompts || []).slice(0, 4).forEach((p) => L.push(`· ${p}`));
    L.push('', '실측하려면 다시 "geo"를 눌러 주세요(20초 내외 소요).');
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name));
  }
  if (geo.status === 'done') {
    const senti = { positive: '긍정 🟢', neutral: '중립 ⚪', negative: '부정 🔴' }[geo.sentiment] || '·';
    const L = [`🤖 ${name} GEO·AI검색 실측`, ''];
    L.push(`등급 ${gradeIcon(geo.grade)} ${geo.grade}`);
    L.push(`· 인용률 ${pctText(geo.citationRate)} (${geo.mentionedCount}/${geo.asked}건 언급)`);
    L.push(`· 답변 내 점유율(SoV) ${pctText(geo.shareOfVoice)}`);
    L.push(`· 언급 톤 ${senti}`);
    L.push(`· 엔진 ${(geo.engines || []).join(', ')}`);
    if (geo.competitors && geo.competitors.length) {
      L.push('', '함께 언급된 경쟁 병원:');
      geo.competitors.slice(0, 3).forEach((c) => L.push(`  · ${c.name} (${c.mentions}회)`));
    }
    if (geo.samples && geo.samples.length) {
      L.push('', `예: "${geo.samples[0].excerpt}…" (${geo.samples[0].engine})`);
    }
    L.push('', '※ 공개 AI 검색 실측(참고용).');
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name));
  }
  return skill([simpleText(`🤖 ${name} GEO·AI검색\n\n측정할 수 없습니다.`)], viewQuickReplies(name));
}

// ── 뷰: 상담 CTA ───────────────────────────────────────
function renderContact() {
  const out = {
    textCard: {
      title: '베놈 무료 컨설팅 신청',
      description: `진단 결과를 바탕으로 베놈 컨설턴트가 맞춤 전략을 제안드립니다.\n전화 ${TEL}`,
      buttons: [
        { action: 'webLink', label: '카카오 상담 연결', webLinkUrl: CHANNEL_URL },
        { action: 'phone', label: `전화 ${TEL}`, phoneNumber: TEL },
      ],
    },
  };
  return skill([out]);
}

// ── 상태/오류/거절/진행 ────────────────────────────────
function renderRefusal() {
  return skill([simpleText('🔒 베노미는 베놈 내부 직원 전용 진단 도구입니다.\n접근 권한이 필요하면 관리자에게 문의해 주세요.')]);
}
function renderAsk() {
  return skill([simpleText('진단할 병원명을 입력해 주세요.\n예) 대구 수성구 OO치과')]);
}
function renderError(msg) {
  return skill([simpleText(`진단 중 문제가 발생했습니다.\n${msg || ''}\n잠시 후 다시 시도해 주세요.`)]);
}
function ackData(hospital) {
  return { text: `🩺 "${hospital}" 진단 중이에요… 20초 내로 결과를 보내드릴게요.` };
}

// ── 헬퍼 ──────────────────────────────────────────────
function displayName(report) {
  const p = report && report.resolved && report.resolved.place;
  if (p && p.found && p.name) return p.name;
  return (report && report.query && report.query.name) || '병원';
}
function fmtNum(n) { return n == null ? '·' : Number(n).toLocaleString('ko-KR'); }
function valOr(v) { return v == null ? '·' : v; }
function pctText(v) { return v == null ? '·' : `${Math.round(v * 100)}%`; }

// 뷰 → 렌더러 디스패치
function render(report, view) {
  switch (view) {
    case 'seo': return renderSeo(report);
    case 'ads': return renderAds(report);
    case 'local': return renderLocal(report);
    case 'geo': return renderGeo(report);
    default: return renderSummary(report);
  }
}

module.exports = {
  parseCommand, render,
  renderSummary, renderSeo, renderAds, renderLocal, renderGeo, renderContact,
  renderRefusal, renderAsk, renderError, ackData,
  skill, simpleText, viewQuickReplies, displayName, reportUrl, reportLinkCard,
  CHANNEL_URL, TEL,
};
