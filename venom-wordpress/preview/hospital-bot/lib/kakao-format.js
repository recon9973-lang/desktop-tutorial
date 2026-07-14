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
function proposalLinkCard(name) {
  const url = reportUrl(name);
  if (!url) return null;
  return { textCard: { title: '📄 전체 제안서(웹)', description: '제안 솔루션·광고비 추정·기대효과 전체를 웹에서 보고 PDF로 저장.',
    buttons: [{ action: 'webLink', label: '전체 제안서 열기', webLinkUrl: url + '&proposal=1' }] } };
}

// ── 발화 파싱 ─────────────────────────────────────────
const VIEW_KEYWORDS = [
  ['law', /(심의|광고법|의료법)$/],
  ['proposal', /(제안서|견적서|견적|제안)$/],
  ['compete', /(경쟁|경쟁사|순위|동네순위|비교)$/],
  ['ads', /(광고|광고비|키워드|cpc)$/i],
  ['geo', /(geo|지오|ai검색|ai 검색)$/i],
  ['seo', /(seo|에스이오|검색최적화)$/i],
  ['local', /(플레이스|로컬|place|지도)$/i],
  ['contact', /^(상담|문의|컨설팅)$/],
];

function parseCommand(utterance) {
  const s = String(utterance || '').trim().replace(/\s+/g, ' ');
  // 온보딩용: 본인 접근키(botUserKey) 조회 — 화이트리스트 등록에 사용(자연스러운 변형 폭넓게 인식)
  if (/^(내\s*키|키\s*발급|발급\s*요청|발급|키\s*받기|키\s*확인|키\s*조회|내\s*아이디|내아이디|아이디\s*확인|아이디\s*발급|아이디|접근\s*키|등록\s*키|인증\s*키|가입|등록\s*요청|등록|my\s*id|myid|id)$/i.test(s)) return { view: 'myid', hospital: '' };
  // 사용법 안내
  if (/^(도움말|도움|사용법|사용\s*방법|명령어|help|\?|？)$/i.test(s)) return { view: 'help', hospital: '' };
  for (const [view, re] of VIEW_KEYWORDS) {
    if (re.test(s)) {
      if (view === 'contact') return { view: 'contact', hospital: '' };
      const hospital = s.replace(re, '').trim();
      if (hospital) return { view, hospital };
    }
  }
  // URL만 붙여 보낸 경우(뷰 키워드 없음) → SEO 의도로 간주(홈페이지 주소 진단)
  if (/https?:\/\/\S+/i.test(s)) return { view: 'seo', hospital: s };
  // 기본: 업체 확인(종합 진단 대신 '무엇을 확인할까요' 버튼)
  return { view: 'confirm', hospital: s };
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

// 항목별 확인 quickReplies — 지역+병원명을 붙여 항상 정확히 재조회되게 한다.
function viewQuickReplies(name, region) {
  const q = (region ? region + ' ' : '') + name;
  return [
    qr('📍 네이버 로컬', `${q} 로컬`),
    qr('⚖️ 의료광고법', `${q} 심의`),
    qr('💰 광고 기회', `${q} 광고`),
    qr('🔎 SEO(주소필요)', `${q} seo`),
    qr('🤖 AI검색(GEO)', `${q} geo`),
    qr('🏆 동네 순위', `${q} 순위`),
    qr('📄 제안서', `${q} 제안서`),
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
  const place = report.resolved && report.resolved.place;
  const notFound = !!(place && place.found === false);
  const medical = !(report.resolved && report.resolved.medical === false);
  const L = [];
  L.push(`${medical ? '🩺' : '📊'} ${name}${region ? `(${region})` : ''} 마케팅 건강검진`);
  L.push('');
  if (notFound) {
    const typed = (report.query && report.query.name) || name;
    L.push(`⚠️ '${typed}' 정식 등록 정보를 찾지 못했어요.`);
    L.push('지역+정식명칭으로 다시 시도해 주세요. (예: 대구 수성구 ○○치과)');
    L.push('아래는 입력한 이름 기준 참고 결과입니다.');
    L.push('');
  }
  L.push(`▪ 종합등급  ${gradeIcon(s.grade)} ${s.grade || 'N/A'}${s.score != null ? ` (${s.score}점)` : ''}`);
  L.push(`▪ SEO 홈페이지  ${line_seo(report.seo)}`);
  if (report.search && report.search.status === 'ok') L.push(`▪ 구글 실측(GSC)  ${line_search(report.search)}`);
  L.push(`▪ GEO·AI검색  ${line_geo(report.geo)}`);
  L.push(`▪ 네이버 로컬  ${line_local(report.local)}`);
  L.push(`▪ 광고 기회  ${line_ads_top(report.ads)}`);
  if (medical) L.push(`▪ 의료광고법  ${line_law(report.adLaw)}`);
  if (s.urgent && s.urgent.length) {
    L.push('');
    L.push(`가장 시급: ${s.urgent.join(' / ')}`);
  }
  if (s.partial && s.unmeasured && s.unmeasured.length) {
    L.push('');
    L.push(`ℹ️ 선택 지표 미설정: ${s.unmeasured.join('·')} — 키 추가 시 등급 정확도↑`);
  }
  L.push('');
  L.push('※ 공개 데이터 기반 참고용 진단입니다.');
  const outputs = [simpleText(L.join('\n'))];
  const linkCard = reportLinkCard(name);
  if (linkCard) outputs.push(linkCard);
  return skill(outputs, viewQuickReplies(name, report.resolved && report.resolved.region));
}

// ── 뷰: 업체 확인(하나씩 확인 진입점) ──────────────────
function homepageLabel(kind, has) {
  if (!has) return '없음';
  return kind === 'blog' ? '블로그' : kind === 'social' ? 'SNS' : '홈페이지';
}
function renderConfirm(info) {
  info = info || {};
  const name = info.name || '병원';
  if (!info.found) {
    return skill([simpleText(`⚠️ '${name}' 정식 등록 정보를 찾지 못했어요.\n지역(구·동)+정식명칭으로 다시 보내주세요.\n예) 대구 수성구 ○○치과`)]);
  }
  const medical = info.medical !== false;
  const L = [`${medical ? '🩺' : '📊'} ${name}`];
  const sub = [info.region, info.dept || info.category].filter(Boolean).join(' · ');
  if (sub) L.push(sub);
  L.push(`네이버 링크: ${homepageLabel(info.homepageKind, !!info.homepage)}`);
  if (info.confidence === 'low') L.push('⚠ 입력명과 검색결과가 정확히 일치하지 않아요 — 정식명칭 확인');
  L.push('');
  L.push('무엇을 확인할까요? 아래에서 하나씩 눌러보세요.');
  L.push('(항목별로 따로 진단해 정확도를 높였어요)');
  const outputs = [simpleText(L.join('\n'))];
  return skill(outputs, viewQuickReplies(name, info.region));
}
// 지역 필수 안내(항상 지역+병원명)
function renderAskRegion() {
  return skill([simpleText('어느 지역 병원인가요?\n지역(구·동)까지 함께 보내주세요.\n예) 대구 수성구 범어5층치과의원')]);
}

function line_seo(seo) {
  if (!seo) return '·';
  if (seo.status === 'ok') return `${seo.score100}/100 ${scoreIcon(seo.score100)}`;
  if (seo.status === 'no-homepage') return '공식 홈페이지 미발견';
  if (seo.status === 'blog-only') return seo.kind === 'social' ? 'SNS만 등록(홈페이지 아님)' : '블로그만 등록(홈페이지 아님)';
  if (seo.status === 'unavailable') return '측정 보류(홈페이지 수집 실패)';
  return '측정 실패';
}
// GSC 실측 한 줄(관리 고객만) — 28일 클릭·노출·평균순위
function line_search(sc) {
  if (!sc || sc.status !== 'ok') return '·';
  const pos = (sc.topQueries && sc.topQueries.length) ? sc.topQueries[0].position : null;
  const posTxt = pos ? ` · 대표검색어 ${pos}위` : '';
  return `28일 클릭 ${fmtNum(sc.clicks)}·노출 ${fmtNum(sc.impressions)}${posTxt}`;
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
  // 플레이스: 상호 일치 시에만 '등록 확인'. 불일치·0건은 '미등록' 단정 금지 → '검색 미확인'.
  if (local.place) {
    if (local.place.registered === true) parts.push('플레이스 등록 확인');
    else if (local.place.confidence === 'low') parts.push('플레이스 검색 미확인');
  }
  // 블로그: 표본 관련성이 낮으면 부풀려진 건수를 그대로 신뢰하지 않는다.
  if (local.blog && local.blog.total != null) {
    parts.push(local.blog.confidence === 'low' ? '블로그 관련성 낮음' : `블로그 ${fmtNum(local.blog.total)}건`);
  }
  if (local.news && local.news.total != null && local.news.confidence !== 'low') parts.push(`뉴스 ${fmtNum(local.news.total)}건`);
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
  if (law.status === 'na') return '해당 없음(비의료)';
  if (law.status !== 'ok') return law.status === 'no-homepage' ? '홈페이지 미발견' : '스캔 불가';
  return law.pass ? '양호 🟢' : `주의 ${law.forbidden.length}건 ⚠`;
}

// ── 뷰: SEO 상세 ───────────────────────────────────────
// GSC 실측 블록(연결된 관리 고객만) — SEO 상세에 공용
function gscLines(report) {
  const gsc = report && report.search;
  if (!gsc || gsc.status !== 'ok') return [];
  const L = ['', '📈 구글 실측(GSC · 최근 28일):', `· 클릭 ${fmtNum(gsc.clicks)} · 노출 ${fmtNum(gsc.impressions)} · CTR ${pctText(gsc.ctr)}`];
  (gsc.topQueries || []).slice(0, 3).forEach((q) => L.push(`· "${q.query}" ${q.position}위 (클릭 ${fmtNum(q.clicks)})`));
  return L;
}

function renderSeo(report) {
  const name = displayName(report);
  const seo = report.seo || {};
  if (seo.status !== 'ok') {
    const region = report.resolved && report.resolved.region;
    const L = [`🔎 ${name} SEO`, '', line_seo(seo)];
    // 블로그/SNS·홈페이지 미발견 → 실제 홈페이지 주소 입력 안내(하나씩·정확도 우선)
    if (seo.status === 'blog-only' || seo.status === 'no-homepage') {
      L.push('');
      L.push('홈페이지 SEO는 실제 웹사이트 주소가 필요해요.');
      L.push(`아래처럼 주소를 붙여 보내주세요:`);
      L.push(`${(region ? region + ' ' : '')}${name} https://홈페이지주소`);
      L.push('(블로그·SNS는 SEO 대상이 아니에요. 블로그는 "네이버 로컬"에서 확인)');
    } else if (seo.note) {
      L.push(seo.note);
    }
    const gl = gscLines(report);
    if (gl.length) gl.forEach((x) => L.push(x));
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name, region));
  }
  const sc = seo.scores || {};
  const L = [`🔎 ${name} SEO 진단`, ''];
  L.push(`종합 ${seo.score100}/100 ${scoreIcon(seo.score100)}${seo.onPage && seo.onPage.grade ? ` (${seo.onPage.grade})` : ''}`);
  if (seo.onPage) {
    L.push(`· 온페이지 통과 ${valOr(seo.onPage.passed)}개 / 미흡 ${valOr(seo.onPage.failed)}개`);
    L.push(`· 성능 ${valOr(sc.performance)} / 접근성 ${valOr(sc.accessibility)}${seo.source === 'onpage' ? ' (성능은 PSI 키 설정 시)' : ''}`);
  } else {
    L.push(`· 성능 ${valOr(sc.performance)} / SEO ${valOr(sc.seo)} / 접근성 ${valOr(sc.accessibility)}`);
  }
  if (seo.lab && seo.lab.lcpMs) L.push(`· 최대콘텐츠표시(LCP) ${(seo.lab.lcpMs / 1000).toFixed(1)}초`);
  if (seo.autoDetected) L.push(`· ℹ️ 홈페이지 자동 탐색(${seo.autoDetected === 'search' ? '검색' : '네이버 플레이스'} 기준 추정) — 다르면 주소를 함께 입력해 주세요`);
  if (seo.onPage && seo.onPage.renderSuspect) L.push('· ⚠ JS 렌더링/봇 차단 정황 — 일부 항목 정밀분석 필요');
  // GSC 실측(연결된 관리 고객) — 추정 아닌 실제 검색 성과
  gscLines(report).forEach((x) => L.push(x));
  if (seo.topFixes && seo.topFixes.length) {
    L.push('');
    L.push('개선 우선순위:');
    seo.topFixes.forEach((f, i) => L.push(`${i + 1}. ${f}`));
  }
  L.push('');
  L.push(`대상: ${seo.url}`);
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
}

// ── 뷰: 광고 상세 ──────────────────────────────────────
function renderAds(report) {
  const name = displayName(report);
  const ads = report.ads || {};
  if (ads.status !== 'ok' || !ads.keywords || !ads.keywords.length) {
    const why = ads.status === 'unconfigured' ? '검색광고 API가 아직 연결되지 않았습니다.' : (ads.note || '데이터를 불러오지 못했습니다.');
    return skill([simpleText(`💰 ${name} 광고\n\n${why}`)], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  const hasCpc = ads.cpc && ads.cpc.status === 'ok';
  const L = [`💰 ${name} 광고 컨설팅`, '', hasCpc ? '키워드 · 월검색량 · 경쟁 · CPC' : '키워드 · 월검색량 · 경쟁도'];
  ads.keywords.slice(0, 6).forEach((k) => {
    const cpc = k.cpc != null ? `  ₩${fmtNum(k.cpc)}` : '';
    L.push(`• ${k.keyword}  ${fmtNum(k.volume)}회  (${k.competition})${cpc}`);
  });
  L.push('');
  L.push(hasCpc ? '※ CPC = 모바일 평균 2위 노출 추정 입찰가.' : '※ CPC(입찰가)는 검색광고 키 설정 시 표시됩니다.');
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
}

// ── 뷰: 로컬 상세 ──────────────────────────────────────
function renderLocal(report) {
  const name = displayName(report);
  const local = report.local || {};
  const L = [`📍 ${name} 네이버 로컬`, ''];
  // 플레이스: 상호 일치 시 '등록 확인', 아니면 '검색 미확인'(미등록 단정 금지 — 색인 한계)
  const pl = local.place || {};
  const placeTxt = pl.registered === true ? '등록 확인'
    : pl.confidence === 'low' ? '검색 미확인 (네이버 지도에서 직접 확인 권장)'
    : pl.error ? '조회 실패' : '·';
  L.push(`플레이스: ${placeTxt}`);
  // 핵심 키워드 실제 순위(유의미 데이터) — 플레이스 top5 · 블로그 top20
  const ranks = local.keywordRanks || [];
  if (ranks.length) {
    L.push('');
    L.push('🔑 핵심 키워드 순위:');
    ranks.forEach((r) => {
      const p = r.placeRank ? `플레이스 ${r.placeRank}위` : (r.placeChecked ? '플레이스 5위밖' : '플레이스 —');
      const b = r.blogRank ? `블로그 ${r.blogRank}위` : (r.blogChecked ? '블로그 20위밖' : '블로그 —');
      L.push(`· ${r.keyword}`);
      L.push(`   ${p} · ${b}`);
    });
    L.push('※ 플레이스=상위5위·블로그=상위20위 기준(네이버 검색 API)');
  }
  // 블로그/뉴스: 검색 총계 + 표본 관련성(동명 혼입 정직 표기)
  const relTxt = (x) => (x && x.matchRate != null && x.confidence === 'low')
    ? ` (표본 ${x.sampled}건 중 관련 ${x.matched}건)` : '';
  L.push('');
  L.push(`블로그 노출: ${local.blog && local.blog.total != null ? fmtNum(local.blog.total) + '건' + relTxt(local.blog) : '·'}`);
  L.push(`뉴스/PR: ${local.news && local.news.total != null ? fmtNum(local.news.total) + '건' + relTxt(local.news) : '·'}`);
  if (local.signals && local.signals.length) {
    L.push('');
    local.signals.forEach((s) => L.push(`· ${s}`));
  }
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
}

// ── 뷰: GEO 상세(P0) ──────────────────────────────────
function renderGeo(report) {
  const name = displayName(report);
  const geo = report.geo || {};

  if (geo.status === 'unconfigured') {
    return skill([simpleText(`🤖 ${name} GEO·AI검색\n\nAI 엔진 키가 설정되지 않아 실측할 수 없습니다.\n(PERPLEXITY/OPENAI/GEMINI/ANTHROPIC 중 1개 이상 필요)`)], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  if (geo.status === 'ready') {
    const L = [`🤖 ${name} GEO·AI검색`, '', `준비된 AI 엔진: ${(geo.engines || []).join(', ') || '·'}`, '', '진단 질문(예):'];
    (geo.prompts || []).slice(0, 4).forEach((p) => L.push(`· ${p}`));
    L.push('', '실측하려면 다시 "geo"를 눌러 주세요(20초 내외 소요).');
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
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
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  return skill([simpleText(`🤖 ${name} GEO·AI검색\n\n측정할 수 없습니다.`)], viewQuickReplies(name, report.resolved && report.resolved.region));
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
function renderRefusal(userId) {
  const keyLine = userId
    ? `\n\n내 접근키(botUserKey):\n${userId}\n관리자에게 이 키를 전달해 등록을 요청하세요.`
    : '\n접근 권한이 필요하면 관리자에게 문의해 주세요.';
  return skill([simpleText(`🔒 베노미는 베놈 내부 직원 전용 진단 도구입니다.${keyLine}`)]);
}
// 온보딩: 본인 접근키(botUserKey) 안내 — 화이트리스트 등록용
function renderMyId(userId) {
  const id = userId || '(확인 불가)';
  return skill([simpleText(`🪪 내 베노미 접근키(botUserKey)\n\n${id}\n\n이 값을 관리자에게 전달하면 직원 화이트리스트에 등록됩니다.\n(등록 후 병원명을 입력하면 진단이 시작됩니다.)`)]);
}
// 사용법 안내
function renderHelp() {
  const L = [
    '🩺 베노미 사용법',
    '',
    '지역+병원명을 넣으면 업체를 확인하고,',
    '항목을 하나씩 눌러 정확히 진단해요.',
    '예) 대구 수성구 ○○치과',
    '',
    '항목(버튼 또는 발화):',
    '· ○○치과 로컬   네이버 플레이스·블로그',
    '· ○○치과 심의   의료광고법 위반 문구 위치',
    '· ○○치과 광고   검색량·CPC',
    '· ○○치과 seo    홈페이지 SEO (주소 필요)',
    '· ○○치과 geo    AI 검색 노출 실측',
    '· ○○치과 순위   동네 경쟁 비교',
    '',
    'SEO는 실제 홈페이지 주소를 함께 넣어주세요:',
    '예) 대구 수성구 ○○치과 https://real-site.com',
    '(블로그·SNS는 SEO 대상 아님)',
    '',
    '기타: 내키(직원 등록) · 상담',
    '※ 항상 지역(구·동)+정식명칭으로 보내주세요.',
  ];
  return skill([simpleText(L.join('\n'))]);
}
function renderAsk() {
  return skill([simpleText('진단할 병원명을 입력해 주세요.\n예) 대구 수성구 OO치과')]);
}
function renderError(msg) {
  return skill([simpleText(`진단 중 문제가 발생했습니다.\n${msg || ''}\n잠시 후 다시 시도해 주세요.`)]);
}
// 동기 응답이 5초를 넘길 때(콜드스타트·느린 홈페이지) '무응답' 대신 재시도 안내
function renderSlow(hospital) {
  const name = hospital ? `'${hospital}' ` : '';
  return skill([simpleText(`⏳ ${name}진단을 준비 중이에요.\n첫 요청은 서버가 깨어나느라 조금 느릴 수 있어요.\n5초 뒤 한 번만 다시 보내주세요. 🙏`)]);
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

// ── 뷰: 경쟁사 비교(동네 순위) ─────────────────────────
function renderCompete(report) {
  const name = displayName(report);
  const cp = report.compete;
  if (!cp || cp.status === 'insufficient') {
    return skill([simpleText(`🏆 ${name} 동네 순위\n\n${(cp && cp.note) || '비교할 경쟁 병원을 찾지 못했습니다.'}`)], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  if (cp.status !== 'ok') {
    return skill([simpleText(`🏆 ${name} 동네 순위\n\n비교를 완료하지 못했습니다.`)], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  const head = `🏆 ${cp.region ? cp.region + ' ' : ''}${cp.dept || ''} 동네 순위`.replace(/\s+/g, ' ').trim();
  const L = [head, ''];
  cp.rows.forEach((r) => {
    const star = r.isTarget ? '★ ' : '';
    const bits = [];
    if (r.blog != null) bits.push(`블로그 ${fmtNum(r.blog)}`);
    if (r.news != null) bits.push(`뉴스 ${fmtNum(r.news)}`);
    if (r.geoMentions != null) bits.push(`AI ${r.geoMentions}회`);
    L.push(`${r.rank}. ${star}${r.name}  (${bits.join(' · ') || '·'})`);
  });
  if (cp.targetRank) {
    L.push('');
    L.push(`👉 우리 병원: ${cp.total}곳 중 ${cp.targetRank}위`);
  }
  L.push('');
  L.push(`※ ${cp.note}`);
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
}

// ── 뷰: 제안서 초안(요약 카드 + 웹 전체 링크) ──────────
function renderProposal(report) {
  const name = displayName(report);
  const p = report.proposal;
  if (!p || p.error) {
    return skill([simpleText(`📄 ${name} 제안 초안\n\n제안서를 생성하지 못했습니다.`)], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  const L = [`📄 ${name} 마케팅 제안 초안`, p.summaryLine, ''];
  L.push('핵심 제안:');
  (p.recommendations || []).slice(0, 4).forEach((r) => L.push(`• [${r.priority.toUpperCase()}] ${r.area} — ${r.service}`));
  if (!p.recommendations || !p.recommendations.length) L.push('• (데이터 보강 후 상세 제안)');
  const b = p.budget || {};
  L.push('');
  if (b.status === 'ok') L.push(`예상 월 광고비: ₩${fmtNum(b.monthlyMin)} ~ ₩${fmtNum(b.monthlyMax)} (권장 ₩${fmtNum(b.monthlyRec)})`);
  else if (b.status === 'partial') L.push('예상 광고비: 검색광고 키 설정 시 산정(현재 수요만 확인)');
  else L.push('예상 광고비: 검색광고 데이터 없음');
  L.push('※ 대행 수수료 별도 협의 · 의료광고법 준수');

  const outputs = [simpleText(L.join('\n'))];
  const link = proposalLinkCard(name);
  if (link) outputs.push(link);
  return skill(outputs, viewQuickReplies(name, report.resolved && report.resolved.region));
}

// ── 뷰: 의료광고법 상세(위반 문구 위치·링크) ──────────
function renderLaw(report) {
  const name = displayName(report);
  const law = report.adLaw || {};
  // 확인한 페이지 종류(블로그/SNS/홈페이지)를 정확히 라벨링
  const kind = report.resolved && report.resolved.homepageKind;
  const pageKind = kind === 'blog' ? '블로그' : kind === 'social' ? 'SNS' : '홈페이지';
  const L = [`⚖️ ${name} · 의료광고법 점검`, ''];
  if (law.status === 'na') {
    L.push('이 업종은 의료광고법 대상이 아니에요(비의료).');
    L.push('병원·의원·치과·한의원 등 의료 업종에서만 심의 점검을 제공합니다.');
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  if (law.status !== 'ok') {
    L.push(law.status === 'no-homepage' ? '점검할 페이지를 찾지 못했습니다.' : `${pageKind} 본문 점검에 실패했습니다.`);
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  if (law.pass) {
    L.push(`${pageKind} 본문에서 금지 표현이 발견되지 않았습니다(참고용).`);
    if (law.checkedUrl) { L.push(''); L.push(`확인한 ${pageKind}: ${law.checkedUrl}`); }
    return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
  }
  const hits = (law.hits && law.hits.length) ? law.hits
    : (law.forbidden || []).map((w) => ({ term: w, kind: 'forbidden', count: 0, contexts: [] }));
  L.push(`위반·주의 소지 ${hits.length}건 — 위치:`);
  hits.forEach((h) => {
    const mark = h.kind === 'forbidden' ? '🚫' : '⚠️';
    L.push('');
    L.push(`${mark} ${h.term}${h.count > 1 ? ` (본문 ${h.count}곳)` : ''}`);
    (h.contexts || []).slice(0, 2).forEach((c) => L.push(`  └ ${c}`));
  });
  if (law.checkedUrl) { L.push(''); L.push(`확인한 페이지: ${law.checkedUrl}`); L.push('(링크에서 Ctrl+F로 위 문구를 찾으세요)'); }
  L.push('');
  L.push('※ 전후사진·효과보장·최상급 표현은 위반 소지가 있습니다.');
  return skill([simpleText(L.join('\n'))], viewQuickReplies(name, report.resolved && report.resolved.region));
}

// 뷰 → 렌더러 디스패치
function render(report, view) {
  switch (view) {
    case 'seo': return renderSeo(report);
    case 'ads': return renderAds(report);
    case 'local': return renderLocal(report);
    case 'geo': return renderGeo(report);
    case 'law': return renderLaw(report);
    case 'help': return renderHelp(report);
    case 'compete': return renderCompete(report);
    case 'proposal': return renderProposal(report);
    default: return renderSummary(report);
  }
}

module.exports = {
  parseCommand, render,
  renderConfirm, renderAskRegion,
  renderSummary, renderSeo, renderAds, renderLocal, renderGeo, renderLaw, renderCompete, renderProposal, renderContact,
  renderRefusal, renderMyId, renderHelp, renderAsk, renderError, renderSlow, ackData,
  skill, simpleText, viewQuickReplies, displayName, reportUrl, reportLinkCard,
  CHANNEL_URL, TEL,
};
