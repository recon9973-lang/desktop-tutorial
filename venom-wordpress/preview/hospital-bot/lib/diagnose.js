'use strict';

// ============================================================
// diagnose — 베노미 코어 진단 오케스트레이터 (P0)
// ------------------------------------------------------------
// 입력: 병원명(+선택 지역) → 6대 진단을 병렬 수행 → 구조화 진단서 JSON.
//
// 재사용(기존 저장소 자산):
//   ../../lib/naver-searchad     검색량·경쟁도 (검색광고 키워드도구)
//   ../../lib/psi                PageSpeed(성능·SEO)
//   ../../lib/medical-ad-validator  의료광고 금지어 스캔
//   ./naver-openapi              병원 탐지·로컬(플레이스/블로그/뉴스)
//   ./geo-probe                  GEO/AI 노출(P0 스텁 → P1 활성)
//
// 설계 원칙:
//   · 모든 외부 호출은 개별 try/catch — 하나가 실패해도 진단서는 나온다(부분 성공).
//   · 없는 수치를 지어내지 않는다. 미설정/미구현은 status로 정직하게 표기.
//   · 의존성 주입(deps)으로 네트워크·키 없이 오프라인 검증 가능.
// ============================================================

const https = require('https');
const http = require('http');

// 기본 의존성(실제 구현) — 테스트에서 deps로 교체 가능
function defaultDeps() {
  return {
    naverOpenapi: require('./naver-openapi'),
    geoProbe: require('./geo-probe'),
    compete: require('./compete'),
    proposal: require('./proposal'),
    searchad: require('../../lib/naver-searchad'),
    psi: require('../../lib/psi'),
    adValidator: require('../../lib/medical-ad-validator'),
    cache: require('../../lib/cache'),
    fetchHtml,
  };
}

const CACHE_TTL = 60 * 60 * 24; // 24h
function cacheNorm(s) { return String(s || '').replace(/\s+/g, '').toLowerCase(); }
async function safe(promise) { try { return await promise; } catch (e) { return null; } }

// ── 유틸 ──────────────────────────────────────────────
// 광역/특별시·도(구로 끝나는 '대구'가 자치구로 오인되지 않게 별도 처리)
const METROS = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '제주',
  '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남'];
// 자치구·시·군 토큰(1음절 자치구 '중구·동구' 포함). 광역시명은 아래 METROS로 거른다.
const REGION_TOKEN_RE = /[가-힣]+(?:구|시|군)/g;

function isMetroToken(tok) {
  return METROS.some((m) => tok === m || tok.startsWith(m)); // '대구','대구광역시' 모두 제외
}

// 자치구(구/군) 우선, 없으면 시(市). 광역시명은 제외.
function extractRegion(text) {
  const toks = (String(text || '').match(REGION_TOKEN_RE) || []).filter((t) => !isMetroToken(t));
  if (!toks.length) return '';
  const district = toks.find((t) => /(?:구|군)$/.test(t));
  return district || toks[0];
}

function parseInput(raw) {
  const s = String(raw || '').trim().replace(/\s+/g, ' ');
  const region = extractRegion(s);
  // 병원명 = 지역/광역 토큰 제거 후 남은 것(없으면 원문)
  const all = (s.match(REGION_TOKEN_RE) || []);
  let name = s;
  for (const t of all) name = name.split(t).join(' ');
  name = name.replace(/\s+/g, ' ').trim() || s;
  return { raw: s, name, region };
}

function regionFromAddress(addr) {
  return extractRegion(addr);
}

function simplifyDept(category) {
  const c = String(category || '');
  const m = c.match(/(치과|피부과|성형외과|정형외과|한의원|한방|안과|내과|이비인후과|산부인과|비뇨기과|가정의학|통증|재활)/);
  return m ? m[1] : '';
}

// 의료 업종 여부 — 의료광고법 등 병원 전용 기능의 on/off 판단
const MED_RE = /병원|의원|의료|치과|한의|한방|성형외과|피부과|정형외과|안과|내과|이비인후과|산부인과|비뇨|가정의학|통증의학|재활의학|클리닉|메디컬|약국/;
function isMedical(category, name) {
  return MED_RE.test(String(category || '')) || /병원|의원|치과|한의원|클리닉/.test(String(name || ''));
}
// 네이버 카테고리("음식점>카페,디저트")에서 대표 업종 라벨 추출(비의료 일반 업종용)
function businessCategory(category) {
  const c = String(category || '').trim();
  if (!c) return '';
  const seg = c.split('>').filter(Boolean).pop() || c;
  return (seg.split(',')[0] || '').trim();
}

// 업종 + 지역 → 광고 키워드 시드(최대 5). medical=false면 일반 업종 의도 키워드.
function keywordSeeds(dept, region, medical) {
  const isMed = medical !== false; // 하위호환: 생략 시 의료로 간주
  const d = dept || (isMed ? '병원' : '업체');
  const medBase = {
    '치과': ['임플란트', '치아교정', '충치치료'],
    '피부과': ['여드름', '피부관리', '점빼기'],
    '성형외과': ['쌍꺼풀', '코성형', '지방흡입'],
    '정형외과': ['도수치료', '무릎통증', '허리디스크'],
    '한의원': ['다이어트한약', '교통사고', '추나요법'],
    '안과': ['라식', '백내장', '드림렌즈'],
    '내과': ['건강검진', '위내시경', '갑상선'],
  }[d];
  const r = region || '';
  let seeds;
  if (isMed) {
    const base = medBase || ['진료', '예약', '비용'];
    seeds = [r ? `${r}${d}` : d].concat(base.map((b) => (r ? `${r}${b}` : b)));
  } else {
    // 일반 업종: 지역+업종, 지역+업종+의도(예약/가격/후기/추천)
    const intent = ['예약', '가격', '후기', '추천'];
    seeds = [r ? `${r}${d}` : d].concat(intent.map((b) => (r ? `${r}${d} ${b}` : `${d} ${b}`)));
  }
  return Array.from(new Set(seeds.filter(Boolean))).slice(0, 5);
}

// 홈페이지 HTML 수집(가드형) — 의료광고법 스캔용
function fetchHtml(url, { timeout = 7000, maxBytes = 500000 } = {}) {
  return new Promise((resolve) => {
    if (!url || !/^https?:\/\//.test(url)) return resolve({ ok: false, error: 'invalid url', text: '' });
    const lib = url.startsWith('https') ? https : http;
    let received = 0; const chunks = [];
    const req = lib.get(url, { headers: { 'User-Agent': 'VenomiBot/0.1 (+diagnostic)' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.destroy();
        return resolve(fetchHtml(new URL(res.headers.location, url).toString(), { timeout, maxBytes }));
      }
      res.on('data', (d) => {
        received += d.length;
        if (received <= maxBytes) chunks.push(d);
        else res.destroy();
      });
      res.on('end', () => {
        const html = Buffer.concat(chunks).toString('utf8');
        const text = html
          .replace(/<script[\s\S]*?<\/script>/gi, ' ')
          .replace(/<style[\s\S]*?<\/style>/gi, ' ')
          .replace(/<[^>]+>/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
        resolve({ ok: true, status: res.statusCode, text, bytes: received });
      });
    });
    req.on('error', (e) => resolve({ ok: false, error: e.message, text: '' }));
    req.setTimeout(timeout, () => { req.destroy(); resolve({ ok: false, error: 'timeout', text: '' }); });
  });
}

// ── 개별 진단 ─────────────────────────────────────────
async function diagnoseSeo(deps, homepage) {
  if (!homepage) return { status: 'no-homepage', note: '공식 홈페이지를 찾지 못했습니다.' };
  try {
    const p = await deps.psi.fetchPsi(homepage, { strategy: 'mobile' });
    if (!p || !p.ok) return { status: 'unavailable', url: homepage, note: (p && p.reason) || 'PSI 미설정' };
    const s = p.scores || {};
    const score100 = Math.round(((s.performance || 0) + (s.seo || 0)) / 2);
    const topFixes = [];
    if (s.performance != null && s.performance < 70) topFixes.push('모바일 페이지 속도 개선(이미지·스크립트 최적화)');
    if (p.lab && p.lab.lcpMs && p.lab.lcpMs > 2500) topFixes.push('LCP 2.5초 초과 — 대표 이미지 최적화');
    if (s.seo != null && s.seo < 90) topFixes.push('기본 SEO 태그(title/meta/구조화데이터) 보강');
    if (s.accessibility != null && s.accessibility < 80) topFixes.push('접근성(alt·대비) 개선');
    return { status: 'ok', url: homepage, scores: s, score100, lab: p.lab || null, topFixes: topFixes.slice(0, 3) };
  } catch (e) {
    return { status: 'error', url: homepage, error: e.message };
  }
}

async function diagnoseLocal(deps, name, region) {
  const out = { place: null, blog: null, news: null, signals: [] };
  const q = [region, name].filter(Boolean).join(' ').trim() || name;
  try {
    const local = await deps.naverOpenapi.searchJson('local', q, { display: 3 });
    out.place = local.ok ? { registered: local.items.length > 0, count: local.items.length } : { registered: null, error: local.error };
  } catch (e) { out.place = { registered: null, error: e.message }; }
  try {
    const blog = await deps.naverOpenapi.searchJson('blog', name, { display: 3, sort: 'date' });
    out.blog = blog.ok ? { total: blog.total } : { total: null, error: blog.error };
  } catch (e) { out.blog = { total: null, error: e.message }; }
  try {
    const news = await deps.naverOpenapi.searchJson('news', name, { display: 3, sort: 'date' });
    out.news = news.ok ? { total: news.total } : { total: null, error: news.error };
  } catch (e) { out.news = { total: null, error: e.message }; }

  if (out.blog && out.blog.total != null) {
    out.signals.push(out.blog.total >= 30 ? '블로그 노출 활발' : '블로그 콘텐츠 부족 — 포스팅 강화 필요');
  }
  if (out.news && out.news.total != null && out.news.total === 0) out.signals.push('언론/PR 노출 없음 — E-E-A-T 백링크 기회');
  return out;
}

async function diagnoseAds(deps, dept, region, medical) {
  const seeds = keywordSeeds(dept, region, medical);
  try {
    const r = await deps.searchad.fetchKeywordTool(seeds, { timeout: 8000 });
    if (!r || !r.keywordList) return { status: r && r.configured === false ? 'unconfigured' : 'unavailable', seeds, note: (r && r.error) || '검색광고 API 미응답' };
    const toNum = deps.searchad.toNum;
    const keywords = r.keywordList.slice(0, 8).map((k) => {
      const pc = toNum(k.monthlyPcQcCnt != null ? k.monthlyPcQcCnt : k.monthlyPcQcnt);
      const mo = toNum(k.monthlyMobileQcCnt != null ? k.monthlyMobileQcCnt : k.monthlyMobileQcnt);
      return {
        keyword: k.relKeyword,
        volume: pc + mo,
        pc, mobile: mo,
        competition: k.compIdx || '-',                       // 높음/중간/낮음
        avgAdDepth: k.plAvgDepth != null ? k.plAvgDepth : null, // 평균 노출 광고 수(경쟁 신호)
        cpc: null,                                           // 아래에서 입찰가 추정 부착
      };
    }).sort((a, b) => b.volume - a.volume);

    // CPC(입찰가 추정) — 상위 5개 키워드, 모바일 2위 노출 기준. 실패해도 검색량 결과는 유지.
    let cpcMeta = { status: 'unavailable', note: '입찰가 추정 미제공' };
    if (typeof deps.searchad.fetchBidEstimate === 'function') {
      try {
        const top = keywords.slice(0, 5).map((k) => k.keyword);
        const bid = await deps.searchad.fetchBidEstimate(top, { device: 'MOBILE', position: 2 });
        if (bid && bid.bids) {
          keywords.forEach((k) => { if (bid.bids[k.keyword] != null) k.cpc = bid.bids[k.keyword]; });
          cpcMeta = { status: 'ok', device: bid.device, position: bid.position, note: '모바일 평균 2위 노출 추정 입찰가(원).' };
        } else {
          cpcMeta = { status: bid && bid.configured === false ? 'unconfigured' : 'unavailable', note: (bid && bid.error) || '입찰가 추정 미응답' };
        }
      } catch (e) {
        cpcMeta = { status: 'error', note: e.message };
      }
    }
    return { status: 'ok', seeds, keywords, cpc: cpcMeta };
  } catch (e) {
    return { status: 'error', seeds, error: e.message };
  }
}

// 본문에서 매칭 표현의 앞뒤 문맥을 뽑아 "어디에 있는지"를 알려준다(모든 발생, 표현당 최대 cap곳).
function locateTerm(text, term, radius, cap) {
  radius = radius || 26; cap = cap || 3;
  const lower = String(text).toLowerCase();
  const t = String(term).toLowerCase();
  const out = [];
  let from = 0, idx;
  while (t && (idx = lower.indexOf(t, from)) >= 0 && out.length < cap) {
    const start = Math.max(0, idx - radius);
    const end = Math.min(text.length, idx + term.length + radius);
    let snip = text.slice(start, end).replace(/\s+/g, ' ').trim();
    if (start > 0) snip = '…' + snip;
    if (end < text.length) snip = snip + '…';
    out.push(snip);
    from = idx + term.length;
  }
  return out;
}

async function diagnoseAdLaw(deps, homepage) {
  if (!homepage) return { status: 'no-homepage', pass: null, forbidden: [], risky: [], hits: [] };
  try {
    const page = await deps.fetchHtml(homepage, { timeout: 3500 });
    if (!page.ok) return { status: 'fetch-failed', checkedUrl: homepage, error: page.error, pass: null, forbidden: [], risky: [], hits: [] };
    const text = page.text || '';
    const v = deps.adValidator.validateMedicalAd(text);
    const mkHits = (terms, kind) => (terms || []).map((term) => {
      const contexts = locateTerm(text, term);
      return { term, kind, count: contexts.length, contexts };
    });
    const hits = mkHits(v.forbidden, 'forbidden').concat(mkHits(v.risky, 'risky'));
    return {
      status: 'ok',
      checkedUrl: homepage,
      pass: v.pass,
      forbidden: v.forbidden || [],
      risky: v.risky || [],
      hits,
      note: v.pass ? '홈페이지 본문에서 금지 표현이 발견되지 않았습니다(참고용).' : `금지 소지 표현 ${(v.forbidden || []).length}건 발견.`,
    };
  } catch (e) {
    return { status: 'error', checkedUrl: homepage, error: e.message, pass: null, forbidden: [], risky: [], hits: [] };
  }
}

// ── 종합 등급(휴리스틱) ────────────────────────────────
function summarize(report) {
  const urgent = [];
  let score = 0, weight = 0;

  if (report.seo && report.seo.status === 'ok') {
    score += report.seo.score100 * 0.4; weight += 0.4;
    if (report.seo.score100 < 60) urgent.push('홈페이지 SEO/속도 개선');
  }
  // GEO: 실측(done)이면 낮은 등급을 시급 항목으로. preview면 안내만.
  if (report.geo) {
    if (report.geo.status === 'done') {
      if (report.geo.grade && 'DF'.includes(report.geo.grade)) urgent.push('AI 검색(GEO) 노출 강화');
    } else if (report.geo.status === 'ready') {
      urgent.push("AI 검색(GEO) 실측 권장 — 'geo' 명령");
    }
  }

  if (report.local && report.local.blog && report.local.blog.total != null) {
    const blogScore = Math.min(100, (report.local.blog.total / 50) * 100);
    score += blogScore * 0.3; weight += 0.3;
    if (report.local.blog.total < 10) urgent.push('블로그 콘텐츠 확대');
  }
  if (report.adLaw && report.adLaw.status === 'ok') {
    const lawScore = report.adLaw.pass ? 100 : Math.max(0, 100 - report.adLaw.forbidden.length * 25);
    score += lawScore * 0.3; weight += 0.3;
    if (!report.adLaw.pass) urgent.push('의료광고법 위반 소지 문구 수정');
  }

  const norm = weight > 0 ? score / weight : null;
  const grade = norm == null ? 'N/A'
    : norm >= 90 ? 'A' : norm >= 80 ? 'B' : norm >= 70 ? 'C' : norm >= 55 ? 'D' : 'F';
  const headline = norm == null
    ? '데이터가 부족해 종합 등급을 산정하지 못했습니다(키/설정 확인 필요).'
    : `종합등급 ${grade} · 우선 개선 ${Math.min(urgent.length, 3)}건`;
  // 부분 진단 투명성: 선택 키 미설정으로 미측정된 지표를 표기(등급 오해 방지)
  const unmeasured = [];
  if (!(report.seo && report.seo.status === 'ok')) unmeasured.push('SEO');
  if (report.geo && report.geo.status === 'unconfigured') unmeasured.push('GEO');
  if (report.ads && report.ads.status === 'unconfigured') unmeasured.push('광고');
  return {
    grade, score: norm == null ? null : Math.round(norm), headline,
    urgent: urgent.slice(0, 3),
    measuredWeight: Math.round(weight * 100) / 100,
    partial: unmeasured.length > 0,
    unmeasured,
  };
}

// 베이스 번들(값싼 5대 진단 + 병원탐지 + GEO preview) — 24h 캐시 단위
async function computeBase(deps, q) {
  const warnings = [];
  let place;
  try { place = await deps.naverOpenapi.findHospital(q.raw, {}); }
  catch (e) { place = { found: false, error: e.message, source: 'naver-local' }; }
  if (!place.found) warnings.push('업체 탐지 실패 — 지역·정식명칭으로 재시도 권장');

  const region = q.region || regionFromAddress(place.address) || '';
  const rawCat = place.category || '';
  const gname = place.found ? place.name : q.name;
  const medical = isMedical(rawCat, gname);
  const dept = medical
    ? (simplifyDept(rawCat) || simplifyDept(q.raw) || '병원')
    : (businessCategory(rawCat) || '');
  const homepage = place.homepage || null;

  const [seo, local, ads, adLaw, geoPreview] = await Promise.all([
    diagnoseSeo(deps, homepage),
    diagnoseLocal(deps, gname, region),
    diagnoseAds(deps, dept, region, medical),
    // 의료광고법은 병원·의원 등 의료 업종에만 적용(비의료는 해당 없음)
    medical ? diagnoseAdLaw(deps, homepage)
            : Promise.resolve({ status: 'na', reason: '비의료 업종', pass: null, forbidden: [], risky: [], hits: [] }),
    deps.geoProbe.preview(gname, { category: rawCat, region }),
  ]);
  return { place, region, dept, medical, homepage, gname, seo, local, ads, adLaw, geoPreview, warnings };
}

// ── 메인 오케스트레이터 ────────────────────────────────
async function diagnose(rawInput, opts = {}) {
  const deps = opts.deps || defaultDeps();
  const cache = deps.cache;
  const useCache = opts.cache !== false && cache && cache.configured && cache.configured();
  const started = opts.now || 0; // Date.now는 서버 핸들러에서 주입(스크립트 재현성)
  const q = parseInput(rawInput);
  if (opts.region) q.region = opts.region;
  const geoMode = opts.geoMode === 'full' ? 'full' : 'light';
  const cacheHit = { base: false, geo: false, compete: false };

  // 1) 베이스 번들(24h 캐시): 업체탐지 + 값싼 5대 + GEO preview
  const baseKey = `venomi:base:v3:${cacheNorm(q.raw)}|${q.region || ''}`;
  let base = useCache ? await safe(cache.getJson(baseKey)) : null;
  if (base) cacheHit.base = true;
  else {
    base = await computeBase(deps, q);
    if (useCache) await safe(cache.setJson(baseKey, base, CACHE_TTL));
  }
  const { place, region, dept, medical, homepage, gname, seo, local, ads, adLaw } = base;
  const warnings = (base.warnings || []).slice();

  // 2) GEO — light면 preview 재사용, full이면 실 프로빙(별도 24h 캐시)
  let geo = base.geoPreview;
  if (geoMode === 'full') {
    const geoKey = `venomi:geo:v2:${cacheNorm(gname)}|${region}`;
    let g = useCache ? await safe(cache.getJson(geoKey)) : null;
    if (g) cacheHit.geo = true;
    else {
      g = await deps.geoProbe.probe(gname, { category: place.category || '', region });
      if (useCache && g && g.status === 'done') await safe(cache.setJson(geoKey, g, CACHE_TTL));
    }
    geo = g;
  }

  // 3) 경쟁사 비교(opt-in, 24h 캐시) — GEO 경쟁 목록 재활용
  let compete = null;
  if (opts.compete) {
    const cKey = `venomi:compete:v2:${cacheNorm(gname)}|${region}`;
    compete = useCache ? await safe(cache.getJson(cKey)) : null;
    if (compete) cacheHit.compete = true;
    else {
      try {
        compete = await deps.compete.compareCompetitors(gname, {
          region, dept, deps, existingCompetitors: (geo && geo.competitors) || [],
        });
      } catch (e) { compete = { status: 'error', error: e.message, rows: [] }; }
      if (useCache && compete && compete.status === 'ok') await safe(cache.setJson(cKey, compete, CACHE_TTL));
    }
  }

  const report = {
    ok: true,
    query: q,
    resolved: { region, dept, medical, homepage, place },
    seo, geo, local, ads, adLaw,
    compete,
    disclaimer: '본 진단은 공개 데이터 기반 참고용이며, 실제 성과·심의 통과를 보장하지 않습니다.',
    meta: {
      reused: ['naver-searchad', 'psi', 'medical-ad-validator', 'naver-openapi'],
      generatedAtMs: started || null,
      warnings,
      cache: useCache ? cacheHit : { enabled: false },
    },
  };
  report.summary = summarize(report);

  // 4) 제안서 자동 초안(opt-in) — 결정론적, report 완성 후 변환
  if (opts.proposal) {
    try { report.proposal = deps.proposal.buildProposal(report); }
    catch (e) { report.proposal = { error: e.message }; }
  }

  return report;
}

module.exports = { diagnose, computeBase, parseInput, keywordSeeds, summarize, regionFromAddress, simplifyDept, isMedical, businessCategory, fetchHtml, defaultDeps };
