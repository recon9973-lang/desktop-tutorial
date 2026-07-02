'use strict';

// 실시간 연관 키워드·질문 리서치 (글쓰기 엔진용)
// - 네이버 자동완성(ac.search.naver.com): "함께 많이 찾는"·연관 검색어
// - 구글 자동완성(google.com/complete): "관련 검색어"·연관 질문(PAA 근사)
// - 네이버 검색광고 키워드도구(api.searchad.naver.com): 실제 월 검색량 동반 연관키워드
// 모든 호출은 짧은 타임아웃 + try/catch로 감싸 실패해도 글 생성은 절대 막지 않는다.
// (이 모듈은 Vercel 서버리스에서 동작 — 외부 HTTPS 허용 환경 기준)

const https = require('https');
const crypto = require('crypto');

// ── 공통 HTTPS GET ──
function httpGet(urlOrOpts, { timeout = 7000, headers = {} } = {}) {
  return new Promise((resolve) => {
    let opts;
    if (typeof urlOrOpts === 'string') {
      const u = new URL(urlOrOpts);
      opts = { hostname: u.hostname, path: u.pathname + u.search, method: 'GET' };
    } else {
      opts = Object.assign({ method: 'GET' }, urlOrOpts);
    }
    opts.headers = Object.assign({
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept': '*/*',
    }, opts.headers || {}, headers);
    const req = https.request(opts, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('error', () => resolve({ status: 0, body: '' }));
    req.setTimeout(timeout, () => { req.destroy(); resolve({ status: 0, body: '' }); });
    req.end();
  });
}

// ── 질문형 판별 (관련질문 분류용) ──
// 구조적 의문 표지만 사용 — "추천/후기/순위/비용/가격" 같은 평이한 검색어는 연관키워드로 둠.
const Q_HINT = /[?？]|까요|ㄹ까요|을까요|나요\b|가요\?|인가요|은가요|던가요|어떻게|어떤|얼마|언제|어디|무엇|뭐예|뭔가|왜\s|되나요|하나요|있나요|없나요|알려\s*주|추천\s*해\s*주|좋을까|할까요|되는지|무슨/;
function looksLikeQuestion(s) {
  const t = String(s || '');
  // 끝이 '주세요/주실/알려' 등 요청형도 질문 취급
  if (/주세요|주실|알려|궁금/.test(t)) return true;
  return Q_HINT.test(t);
}

// ── 1. 네이버 자동완성 ("함께 많이 찾는"·연관 근사) ──
async function naverAutocomplete(keyword) {
  const q = encodeURIComponent(keyword);
  const url = `https://ac.search.naver.com/nx/ac?q=${q}&q_enc=UTF-8&st=100&frm=nv&r_format=json&r_enc=UTF-8&r_unicode=0&t_koreng=1&ans=2&run=2&rev=4&con=1`;
  const r = await httpGet(url, { headers: { 'Referer': 'https://search.naver.com/' } });
  if (r.status !== 200 || !r.body) return [];
  try {
    const j = JSON.parse(r.body);
    // 구조: { items: [ [ ["키워드", ...], ["키워드2", ...] ], ... ] }
    const out = [];
    (j.items || []).forEach((grp) => {
      (grp || []).forEach((row) => {
        if (Array.isArray(row) && row[0]) out.push(String(row[0]).trim());
        else if (typeof row === 'string') out.push(row.trim());
      });
    });
    return out;
  } catch (e) { return []; }
}

// ── 2. 구글 자동완성 ("관련 검색어"·연관 질문 근사) ──
async function googleAutocomplete(keyword) {
  const q = encodeURIComponent(keyword);
  // client=chrome → ["query",[suggestions...],...] 형식 JSON
  const url = `https://www.google.com/complete/search?client=chrome&hl=ko&gl=kr&q=${q}`;
  const r = await httpGet(url);
  if (r.status !== 200 || !r.body) return [];
  try {
    const j = JSON.parse(r.body);
    return Array.isArray(j[1]) ? j[1].map((s) => String(s).trim()) : [];
  } catch (e) { return []; }
}

// ── 3. 네이버 검색광고 키워드도구 (실제 월 검색량 동반 연관키워드) ──
// 검색광고 API 자격증명 — 신·구 변수명 모두 허용 (저장소 통합 전 등록분 호환)
function adCreds() {
  return {
    key: (process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE || '').trim(),
    secret: (process.env.NAVER_AD_SECRET || process.env.NAVER_SECRET_KEY || '').trim(),
    customer: (process.env.NAVER_AD_CUSTOMER_ID || process.env.NAVER_CUSTOMER_ID || '').trim(),
  };
}
function searchAdHeaders(method, apiPath) {
  const ts = String(Date.now());
  const ad = adCreds();
  const sign = crypto
    .createHmac('sha256', ad.secret)
    .update(`${ts}.${method}.${apiPath}`)
    .digest('base64');
  return {
    'X-Timestamp': ts,
    'X-API-KEY': ad.key,
    'X-Customer': ad.customer,
    'X-Signature': sign,
  };
}
function adToNum(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    if (/<\s*10/.test(v)) return 5;
    const n = parseInt(v.replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : n;
  }
  return 0;
}
async function naverRelKeywords(keyword) {
  const ad = adCreds();
  if (!ad.key || !ad.secret || !ad.customer) return [];
  const hint = String(keyword).replace(/\s+/g, '');
  const apiPath = '/keywordstool';
  const r = await httpGet({
    hostname: 'api.searchad.naver.com',
    path: `${apiPath}?hintKeywords=${encodeURIComponent(hint)}&showDetail=1`,
    headers: searchAdHeaders('GET', apiPath),
  });
  if (r.status !== 200 || !r.body) return [];
  try {
    const j = JSON.parse(r.body);
    if (!Array.isArray(j.keywordList)) return [];
    return j.keywordList
      .map((k) => ({ keyword: String(k.relKeyword || '').trim(), volume: adToNum(k.monthlyPcQcCnt != null ? k.monthlyPcQcCnt : k.monthlyPcQcnt) + adToNum(k.monthlyMobileQcCnt != null ? k.monthlyMobileQcCnt : k.monthlyMobileQcnt) }))
      .filter((k) => k.keyword)
      .sort((a, b) => b.volume - a.volume);
  } catch (e) { return []; }
}

// ── 정규화 ──
function norm(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
function dedupe(arr) {
  const seen = new Set(); const out = [];
  for (const x of arr) {
    const k = norm(x).toLowerCase();
    if (!k || seen.has(k)) continue;
    seen.add(k); out.push(norm(x));
  }
  return out;
}

// ── 메인: 키워드 리서치 ──
// 반환: { related:[문자열], questions:[문자열], volumes:[{keyword,volume}], sources:{naver,google,searchad} }
async function researchKeywords(keyword, { region = '', limitRelated = 14, limitQuestions = 8 } = {}) {
  const base = norm(keyword);
  if (!base) return { related: [], questions: [], volumes: [], sources: {} };
  const q = region ? `${norm(region)} ${base}` : base;

  const [nav, goo, rel] = await Promise.all([
    naverAutocomplete(q).catch(() => []),
    googleAutocomplete(q).catch(() => []),
    naverRelKeywords(base).catch(() => []),
  ]);

  const sources = { naver: nav.length, google: goo.length, searchad: rel.length };

  // 자동완성 합치기 → 질문/연관 분리
  const all = dedupe([...nav, ...goo, ...rel.map((r) => r.keyword)])
    .filter((s) => s.length >= 2 && s.length <= 40)
    // 원 키워드 자체 제외(완전 동일)
    .filter((s) => s.toLowerCase() !== base.toLowerCase() && s.toLowerCase() !== q.toLowerCase());

  const questions = all.filter(looksLikeQuestion).slice(0, limitQuestions);
  const qset = new Set(questions.map((s) => s.toLowerCase()));
  const related = all.filter((s) => !qset.has(s.toLowerCase())).slice(0, limitRelated);

  // 검색량 상위(연관키워드 도구) — 별도 보존(있을 때만)
  const volumes = rel.filter((r) => r.volume > 0).slice(0, 10);

  return { related, questions, volumes, sources };
}

// 배열을 seed만큼 회전 — 같은 주제로 여러 글을 쓸 때 글마다 다른 항목이 앞에 오도록.
function rotate(arr, seed) {
  if (!Array.isArray(arr) || arr.length < 2) return arr || [];
  const k = ((seed % arr.length) + arr.length) % arr.length;
  return arr.slice(k).concat(arr.slice(0, k));
}

// ── 프롬프트 주입용 텍스트 블록 생성 ──
// 데이터가 빈약하면 빈 문자열 반환(프롬프트에 노이즈 추가 안 함)
// seed: 같은 키워드로 N편 작성 시 글마다 다른 연관어·질문을 우선 노출(중복 방지). 0이면 회전 없음.
function buildResearchPrompt(research, seed = 0) {
  if (!research) return '';
  let { related = [], questions = [], volumes = [] } = research;
  if (!related.length && !questions.length) return '';
  if (seed) {
    // 검색량 상위(volumes)는 그대로 우선 노출, 자동완성 연관어·질문만 회전시켜 글마다 다양화
    related = rotate(related, seed);
    questions = rotate(questions, seed);
  }
  const lines = [];
  lines.push('[실제 검색 리서치 데이터 — 네이버/구글 자동완성·연관키워드 기반. 아래를 본문 소제목과 FAQ에 자연스럽게 반영(나열 금지, 검색 의도 충족 목적). 같은 주제의 다른 글과 겹치지 않게 이번 글은 앞쪽 항목 위주로 다룰 것]');
  if (related.length) lines.push('· 연관 검색어(함께 많이 찾는/관련 검색어): ' + related.join(', '));
  if (questions.length) lines.push('· 자주 묻는 질문(관련질문/PAA): ' + questions.join(' / '));
  if (volumes.length) {
    const v = volumes.slice(0, 6).map((x) => `${x.keyword}(월 ${x.volume.toLocaleString()})`).join(', ');
    lines.push('· 실제 월 검색량 상위(우선 공략): ' + v);
  }
  return lines.join('\n');
}

module.exports = { researchKeywords, buildResearchPrompt, looksLikeQuestion, _internal: { naverAutocomplete, googleAutocomplete, naverRelKeywords } };
