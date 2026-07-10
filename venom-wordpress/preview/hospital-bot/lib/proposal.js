'use strict';

// ============================================================
// proposal — 진단서 → 베놈 제안서/견적 자동 초안 (P3, 트랙 B)
// ------------------------------------------------------------
// 결정론적 생성(LLM·네트워크 불필요). 진단 데이터 → 베놈 서비스 매칭 + 근거.
// 견적: 대행 수수료는 지어내지 않고 "협의" 표기. 광고비만 실제 CPC×검색량으로
//       가정(클릭률)을 명시해 추정. (허위수치·허위가격 금지 — CLAUDE.md 준수)
// ============================================================

const AD_CTR = 0.04; // 상위 노출 시 검색 대비 클릭 가정(추정용, 명시). 4%.

function num(n) { return n == null ? null : Number(n); }
function won(n) { return n == null ? '·' : '₩' + Number(Math.round(n)).toLocaleString('ko-KR'); }
function cnt(n) { return n == null ? '·' : Number(n).toLocaleString('ko-KR'); }

// 진단 gap → 베놈 서비스 추천 규칙
function buildRecommendations(report) {
  const recs = [];
  const seo = report.seo || {}, geo = report.geo || {}, local = report.local || {}, adLaw = report.adLaw || {}, ads = report.ads || {}, cp = report.compete;

  if (seo.status === 'ok' && seo.score100 != null && seo.score100 < 70) {
    recs.push({ priority: 'high', area: 'SEO', finding: `홈페이지 SEO ${seo.score100}/100`, service: '홈페이지 SEO 개선(속도·구조화데이터·모바일)', rationale: '검색 유입의 기반. 상위 개선항목: ' + (seo.topFixes || []).slice(0, 2).join(', ') });
  } else if (seo.status === 'no-homepage') {
    recs.push({ priority: 'high', area: 'SEO', finding: '공식 홈페이지 미발견', service: '병원 홈페이지 제작 + SEO 기본 세팅', rationale: '검색·AI 노출의 근거 페이지가 없어 최우선 필요' });
  }

  if (geo.status === 'done' && geo.grade && 'DF'.includes(geo.grade)) {
    recs.push({ priority: 'high', area: 'GEO', finding: `AI 검색 인용률 ${geo.citationRate != null ? Math.round(geo.citationRate * 100) + '%' : '낮음'} (등급 ${geo.grade})`, service: 'GEO·AEO 최적화(ChatGPT·Perplexity 대응 콘텐츠)', rationale: 'AI 검색에서 병원이 거의 추천되지 않음 — 환자 유입 기회 손실' });
  } else if (geo.status === 'unconfigured' || geo.status === 'ready') {
    recs.push({ priority: 'medium', area: 'GEO', finding: 'AI 검색 노출 미측정', service: 'GEO·AEO 진단 후 최적화', rationale: 'AI 검색 대응은 2026 병원 마케팅의 핵심 축' });
  }

  if (local.blog && local.blog.total != null && local.blog.total < 30) {
    recs.push({ priority: 'medium', area: '콘텐츠', finding: `블로그 노출 ${cnt(local.blog.total)}건`, service: '블로그·파워컨텐츠 콘텐츠 운영', rationale: '정보성 콘텐츠 부족 — 신뢰·검색 노출 동반 강화' });
  }
  if (local.news && local.news.total === 0) {
    recs.push({ priority: 'low', area: 'PR', finding: '언론/PR 노출 없음', service: '언론보도·PR(E-E-A-T 백링크)', rationale: '전문성·신뢰 신호 확보로 검색·AI 인용에 유리' });
  }

  if (ads.status === 'ok' && ads.keywords && ads.keywords.length) {
    const top = ads.keywords[0];
    recs.push({ priority: 'high', area: '광고', finding: `핵심 키워드 '${top.keyword}' 月${cnt(top.volume)}회`, service: '파워링크(+브랜드검색) 검색광고', rationale: '수요가 확인된 키워드에서 즉시 상위 노출 확보' });
  }

  if (adLaw.status === 'ok' && adLaw.pass === false) {
    recs.push({ priority: 'high', area: '의료광고법', finding: `위반 소지 표현 ${(adLaw.forbidden || []).length}건(${(adLaw.forbidden || []).join(', ')})`, service: '의료광고 심의 대응·문구 교정', rationale: '행정처분 리스크 — 광고 집행 전 필수 교정' });
  }

  if (cp && cp.status === 'ok' && cp.targetRank && cp.total && cp.targetRank > Math.ceil(cp.total / 2)) {
    recs.push({ priority: 'medium', area: '경쟁', finding: `동네 ${cp.total}곳 중 ${cp.targetRank}위(하위권)`, service: '통합 마케팅(경쟁 열위 만회)', rationale: '지역 경쟁 열세 — 로컬·콘텐츠·광고 동시 강화 필요' });
  }

  // 우선순위 정렬
  const order = { high: 0, medium: 1, low: 2 };
  recs.sort((a, b) => order[a.priority] - order[b.priority]);
  return recs;
}

// 광고비 추정(실제 CPC×검색량, 가정 명시). CPC 없으면 도달량만.
function estimateAdBudget(ads) {
  if (!ads || ads.status !== 'ok' || !ads.keywords || !ads.keywords.length) {
    return { status: 'unavailable', note: '검색광고 데이터 없음' };
  }
  const top = ads.keywords.slice(0, 3);
  const hasCpc = top.some((k) => k.cpc != null);
  const rows = top.map((k) => {
    const clicks = Math.round((num(k.volume) || 0) * AD_CTR);
    const monthly = k.cpc != null ? clicks * k.cpc : null;
    return { keyword: k.keyword, volume: num(k.volume), estClicks: clicks, cpc: num(k.cpc), estMonthly: monthly };
  });
  const total = rows.reduce((s, r) => s + (r.estMonthly || 0), 0);
  return {
    status: hasCpc ? 'ok' : 'partial',
    ctrAssumed: AD_CTR,
    rows,
    monthlyRec: hasCpc ? total : null,
    monthlyMin: hasCpc ? Math.round(total * 0.7) : null,
    monthlyMax: hasCpc ? Math.round(total * 1.3) : null,
    note: hasCpc
      ? `상위 3개 키워드 상위노출 가정(클릭률 ${Math.round(AD_CTR * 100)}%) 월 광고비 추정. 대행 수수료 별도 협의.`
      : 'CPC 미제공 — 검색 수요(도달)만 산정. 검색광고 키 설정 시 광고비 추정 제공.',
  };
}

function buildProposal(report, opts = {}) {
  const name = (report.resolved && report.resolved.place && report.resolved.place.found && report.resolved.place.name) || (report.query && report.query.name) || '병원';
  const region = (report.resolved && report.resolved.region) || '';
  const dept = (report.resolved && report.resolved.dept) || '';
  const s = report.summary || {};
  const recs = buildRecommendations(report);
  const budget = estimateAdBudget(report.ads);

  const strengths = [];
  const weaknesses = [];
  if (report.seo && report.seo.status === 'ok') (report.seo.score100 >= 80 ? strengths : weaknesses).push(`SEO ${report.seo.score100}/100`);
  if (report.local && report.local.blog && report.local.blog.total != null) (report.local.blog.total >= 30 ? strengths : weaknesses).push(`블로그 노출 ${cnt(report.local.blog.total)}건`);
  if (report.geo && report.geo.status === 'done') (('AB'.includes(report.geo.grade)) ? strengths : weaknesses).push(`AI검색 등급 ${report.geo.grade}`);
  if (report.adLaw && report.adLaw.status === 'ok') (report.adLaw.pass ? strengths : weaknesses).push(report.adLaw.pass ? '광고문구 양호' : `광고법 위반소지 ${(report.adLaw.forbidden || []).length}건`);

  const expectedEffects = [];
  if (recs.some((r) => r.area === 'SEO')) expectedEffects.push('검색 유입 기반 강화(홈페이지 신뢰·속도 개선)');
  if (recs.some((r) => r.area === 'GEO')) expectedEffects.push('AI 검색(ChatGPT·Perplexity) 추천 노출 확보');
  if (recs.some((r) => r.area === '광고')) expectedEffects.push('핵심 키워드 상위 노출로 신환 문의 즉시 증대');
  if (recs.some((r) => r.area === '의료광고법')) expectedEffects.push('의료광고법 리스크 제거(행정처분 예방)');

  const proposal = {
    title: `${name} 마케팅 제안 초안`,
    hospital: name, region, dept,
    grade: s.grade || null,
    summaryLine: `${region ? region + ' ' : ''}${dept || ''} · 종합등급 ${s.grade || 'N/A'}${s.score != null ? ` (${s.score}점)` : ''}`.trim(),
    strengths, weaknesses,
    priorities: (s.urgent || []).slice(0, 3),
    recommendations: recs,
    budget,
    expectedEffects,
    compliance: '본 제안은 공개 데이터 기반 진단에 근거한 초안입니다. 모든 광고 소재는 의료법 제56·57조 및 심의기준을 준수하며, 전후사진·효과보장·최상급 표현은 배제합니다. 대행 수수료·계약 조건은 별도 협의합니다.',
    disclaimer: report.disclaimer || '공개 데이터 기반 참고용.',
  };
  proposal.markdown = toMarkdown(proposal);
  return proposal;
}

function toMarkdown(p) {
  const L = [];
  L.push(`# ${p.title}`);
  L.push('');
  L.push(`> ${p.summaryLine}`);
  L.push('');
  if (p.strengths.length) L.push(`**강점**: ${p.strengths.join(' · ')}`);
  if (p.weaknesses.length) L.push(`**약점**: ${p.weaknesses.join(' · ')}`);
  if (p.priorities.length) { L.push(''); L.push('## 가장 시급한 개선'); p.priorities.forEach((u, i) => L.push(`${i + 1}. ${u}`)); }

  L.push(''); L.push('## 제안 솔루션');
  if (!p.recommendations.length) L.push('- (추가 데이터 확보 후 상세 제안)');
  p.recommendations.forEach((r) => {
    L.push(`- **[${r.priority.toUpperCase()}] ${r.area} — ${r.service}**`);
    L.push(`  - 진단: ${r.finding}`);
    L.push(`  - 근거: ${r.rationale}`);
  });

  L.push(''); L.push('## 예상 광고비(추정)');
  const b = p.budget;
  if (b.status === 'ok') {
    L.push(`| 키워드 | 월검색량 | 예상클릭 | CPC | 월 광고비(추정) |`);
    L.push(`|---|--:|--:|--:|--:|`);
    b.rows.forEach((r) => L.push(`| ${r.keyword} | ${cnt(r.volume)} | ${cnt(r.estClicks)} | ${won(r.cpc)} | ${won(r.estMonthly)} |`));
    L.push('');
    L.push(`**월 광고비 밴드(추정)**: ${won(b.monthlyMin)} ~ ${won(b.monthlyMax)} (권장 ${won(b.monthlyRec)})`);
  } else if (b.status === 'partial') {
    L.push('검색 수요는 확인됨(아래). CPC 미제공으로 광고비는 키 설정 후 산정.');
    b.rows.forEach((r) => L.push(`- ${r.keyword}: 월 ${cnt(r.volume)}회 · 예상클릭 ${cnt(r.estClicks)}`));
  } else {
    L.push('- 검색광고 데이터 없음(키 설정 후 제공).');
  }
  L.push(''); L.push(`> ${b.note || ''}`);

  if (p.expectedEffects.length) { L.push(''); L.push('## 기대 효과'); p.expectedEffects.forEach((e) => L.push(`- ${e}`)); }

  L.push(''); L.push('---');
  L.push(p.compliance);
  return L.join('\n');
}

module.exports = { buildProposal, buildRecommendations, estimateAdBudget, toMarkdown, AD_CTR };
