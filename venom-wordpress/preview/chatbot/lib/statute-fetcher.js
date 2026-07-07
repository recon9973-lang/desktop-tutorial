'use strict';

/**
 * 의료광고 관련 법령 조문 수집 공유 로직 — 국가법령정보센터(law.go.kr) DRF Open API.
 * CLI(pipeline/fetch-statutes.js)·API(api/statutes-refresh.js) 공용.
 *
 * 대상(여러 법령):
 *   - 의료법(법률): 제56·57·57의2·57의3조
 *   - 의료법 시행령(대통령령): 제23·24조
 *
 * 방식(법령별):
 *   ① lawService LM=<법령명> 직접 조회 → 실패 시 ② lawSearch 정확일치 MST 재조회
 *   ③ <조문단위> 파싱 실패 시 <조문내용> 위치 슬라이싱(항·호 포함)
 *
 * 조문을 임의 생성하지 않는다. 실패 시 status/ debug로 보고.
 * (의료광고심의위원회 운영규정은 협회 자율규정이라 법령 API 대상 아님 — 별도 소스로 관리)
 */

const https = require('https');
const enc = encodeURIComponent;

const LAWS = [
  {
    name: '의료법', type: '법률',
    articles: [
      { article: '제56조', title: '의료광고의 금지 등' },
      { article: '제57조', title: '의료광고의 심의' },
      { article: '제57조의2', title: '의료광고에 관한 심의위원회' },
      { article: '제57조의3', title: '자율심의기구의 심의 등에 대한 모니터링' },
    ],
  },
  {
    name: '의료법 시행령', type: '대통령령',
    articles: [
      { article: '제23조', title: '의료광고의 금지 기준' },
      { article: '제24조', title: '의료광고의 심의' },
    ],
  },
];
// 하위호환(기존 참조): 평탄화된 전체 대상
const TARGETS = LAWS.flatMap(l => l.articles.map(a => ({ law: l.name, ...a })));

function defaultGet(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { headers: { 'User-Agent': 'venom-chatbot/1.0' } }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('error', reject);
    req.setTimeout(25000, () => { req.destroy(); reject(new Error('타임아웃')); });
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
// get 재시도 래퍼(일시적 실패·rate limit 대비): 200이고 에러문구 없을 때까지 최대 tries회.
async function getRetry(get, url, tries = 3) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await get(url);
      if (r.status === 200 && !hasErr(r.body)) return r;
      last = r;
    } catch (e) { last = { status: 0, body: '', err: e.message }; }
    await sleep(500 * (i + 1));
  }
  return last || { status: 0, body: '' };
}

function pick(re, s) { const m = (s || '').match(re); return m ? m[1] : ''; }
function clean(s) {
  return (s || '').replace(/<!\[CDATA\[|\]\]>/g, '').replace(/<[^>]+>/g, ' ')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
}
function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
// DRF 오류 응답 감지(명확한 신호만 — 법조문 본문에 흔한 '등록되지/허용되지'는 제외해 오탐 방지)
function hasErr(b) { return !b || /<error|로그인이 필요|OpenAPI|인증키가 유효|사용자 ID를 확인/.test(b); }
// 법령 본문(조문 포함) 여부 — 본문 조회 결과 검증용(긍정 신호)
function isLawBody(b) { return !!b && /<조문내용>|<조문단위>|<조문[\s>]/.test(b); }
// 조문 텍스트 정리: 꼬리 메타데이터 제거 + 중복 항·호 번호 축약
function cleanStatuteText(text) {
  let t = text;
  // 다음 조문 메타가 꼬리에 붙는 경우 제거: "... 57 조문 제목 20260407 N" / "58 전문 20260407 N"
  t = t.replace(/\s+\d+(?:\s+\d+)?\s+(?:조문|전문)(?:\s+[^\d]+?)?\s+\d{8}\s+[NY]\s*$/, '');
  // 중복 번호 축약: "① ①" → "①", "1. 1." → "1.", "가. 가." → "가."
  t = t.replace(/([①-⑳])\s+\1/g, '$1');
  t = t.replace(/(\d+)\.\s+\1\./g, '$1.');
  t = t.replace(/([가-힣])\.\s+\1\./g, '$1.');
  return t.replace(/\s+/g, ' ').trim();
}

function lawNameOf(body) {
  return clean(pick(/<법령명_?한글>([\s\S]*?)<\/법령명_?한글>/, body) || pick(/<법령명>([\s\S]*?)<\/법령명>/, body));
}

// lawSearch 결과에서 지정 법령명 정확 일치 MST(현행 우선). 없으면 ''.
function selectMst(searchBody, lawName) {
  const blocks = searchBody.match(/<law\b[^>]*>[\s\S]*?<\/law>/g) || [];
  const matches = blocks.filter(b => lawNameOf(b) === lawName);
  if (!matches.length) return '';
  const current = matches.find(b => /현행/.test(pick(/<현행연혁코드>([\s\S]*?)<\/현행연혁코드>/, b)));
  return pick(/<법령일련번호>(\d+)<\/법령일련번호>/, current || matches[0]);
}

function labelOf(no, branch) {
  const b = String(branch || '').replace(/[^0-9]/g, '');
  return b && b !== '0' ? `제${no}조의${parseInt(b, 10)}` : `제${no}조`;
}

// 본문에서 대상 조문 추출(2중 전략). articles: [{article,title}]
function parseArticles(body, mst, lawName, articles) {
  const out = [];
  const wants = a => articles.find(x => x.article === a);

  // 전략 1: <조문단위>
  const units = body.match(/<조문단위>[\s\S]*?<\/조문단위>/g) || [];
  for (const u of units) {
    const no = pick(/<조문번호>(\d+)<\/조문번호>/, u);
    if (!no) continue;
    const t = wants(labelOf(no, pick(/<조문가지번호>([\s\S]*?)<\/조문가지번호>/, u)));
    if (!t) continue;
    const title = clean(pick(/<조문제목>([\s\S]*?)<\/조문제목>/, u)) || t.title;
    const text = cleanStatuteText(clean(u));
    if (text) out.push({ law: lawName, article: t.article, title, text, mst });
  }
  if (out.length) return { statutes: out, via: '조문단위', units: units.length };

  // 전략 2: <조문내용> 위치 슬라이싱(항·호 포함)
  const markers = [];
  const re = /<조문내용>([\s\S]*?)<\/조문내용>/g;
  let m;
  while ((m = re.exec(body)) !== null) markers.push({ index: m.index, header: clean(m[1]) });
  for (let i = 0; i < markers.length; i++) {
    const t = wants((markers[i].header.match(/^(제\d+조(?:의\d+)?)\s*[\(（]/) || [])[1]);
    if (!t || out.find(o => o.article === t.article)) continue;
    const end = i + 1 < markers.length ? markers[i + 1].index : body.length;
    out.push({ law: lawName, article: t.article, title: t.title, text: cleanStatuteText(clean(body.slice(markers[i].index, end))), mst });
  }
  return { statutes: out, via: '조문내용-슬라이스', units: units.length, contents: markers.length };
}

// 법령 1건 조회 → 조문 추출
async function fetchOneLaw(oc, law, get) {
  let body = '', mst = '', via = '';
  // ① LM 직접
  try {
    const r = await get(`https://www.law.go.kr/DRF/lawService.do?OC=${enc(oc)}&target=law&type=XML&LM=${enc(law.name)}`);
    if (r.status === 200 && !hasErr(r.body) && lawNameOf(r.body) === law.name) { body = r.body; via = 'LM'; mst = pick(/법령일련번호>(\d+)</, r.body); }
  } catch (e) { /* 폴백 */ }
  // ② 검색 → 정확일치 MST → 재조회(재시도 포함)
  if (!body) {
    const probe = await getRetry(get, `https://www.law.go.kr/DRF/lawSearch.do?OC=${enc(oc)}&target=law&type=XML&query=${enc(law.name)}&display=50`);
    if (probe.status !== 200 || hasErr(probe.body)) return { name: law.name, status: 'error', reason: `검색 응답 이상(${probe.status})`, statutes: [] };
    mst = selectMst(probe.body, law.name);
    if (!mst) return { name: law.name, status: 'error', reason: `검색에서 '${law.name}' 정확 일치 없음`, statutes: [] };
    const r = await getRetry(get, `https://www.law.go.kr/DRF/lawService.do?OC=${enc(oc)}&target=law&type=XML&MST=${mst}`);
    if (r.status === 200 && isLawBody(r.body)) { body = r.body; via = 'MST'; }
    else return { name: law.name, status: 'error', reason: `본문 조회 실패(재시도 후, status ${r.status}, 법령본문 ${isLawBody(r.body)})`, statutes: [], mst };
  }
  if (!body) return { name: law.name, status: 'error', reason: '본문 조회 실패', statutes: [], mst };

  const parsed = parseArticles(body, mst, law.name, law.articles);
  if (!parsed.statutes.length) {
    const i = body.indexOf(law.articles[0].article);
    return { name: law.name, status: 'error', reason: `조문 매칭 0건(조문단위 ${parsed.units}, 조문내용 ${parsed.contents || 0})`, statutes: [], mst, debug: { via, has: i >= 0, snippet: i >= 0 ? body.slice(i - 20, i + 200) : '' } };
  }
  return { name: law.name, status: 'ok', via, mst, statutes: parsed.statutes };
}

/**
 * 여러 법령(의료법·의료법 시행령) 조문 수집.
 * @returns {Promise<{status, reason?, statutes:[], laws:[], debug?}>}
 */
async function fetchStatutes(oc, opts = {}) {
  const get = opts.get || defaultGet;
  if (!oc) return { status: 'pending', reason: 'LAW_OC(OC) 미설정 — open.law.go.kr에서 무료 발급 필요', statutes: [] };

  const results = [];
  for (let i = 0; i < LAWS.length; i++) {
    if (i > 0) await sleep(800);           // 법령 사이 지연 — law.go.kr 연속요청 제한 회피
    results.push(await fetchOneLaw(oc, LAWS[i], get));
  }

  const statutes = results.flatMap(r => r.statutes);
  const laws = results.map(r => ({ name: r.name, status: r.status, count: r.statutes.length, ...(r.reason ? { reason: r.reason } : {}), ...(r.mst ? { mst: r.mst } : {}) }));
  if (!statutes.length) {
    return { status: 'error', reason: '전체 법령 수집 0건', statutes: [], laws, debug: results.map(r => r.debug).filter(Boolean) };
  }
  const anyErr = results.some(r => r.status !== 'ok');
  return { status: 'ok', partial: anyErr, statutes, laws, mst: results[0].mst };
}

module.exports = { fetchStatutes, LAWS, TARGETS, _internal: { selectMst, labelOf, parseArticles, lawNameOf, fetchOneLaw, cleanStatuteText, isLawBody, hasErr } };
