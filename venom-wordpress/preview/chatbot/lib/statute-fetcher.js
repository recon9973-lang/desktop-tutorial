'use strict';

/**
 * 의료법 조문 수집 공유 로직 — 국가법령정보센터(law.go.kr) DRF Open API.
 * CLI(pipeline/fetch-statutes.js)와 API(api/statutes-refresh.js)가 공용으로 사용.
 *
 * 방식:
 *   ① lawService를 법령명(LM=의료법)으로 직접 조회 → 검색 단계의 오선택 방지
 *   ② 실패 시 lawSearch로 '의료법' 정확 일치 MST를 찾아 재조회(정확 일치 없으면 중단 — 엉뚱한 법 방지)
 *   ③ <조문단위> 파싱, 실패하면 <조문내용> 블록으로 폴백
 *   ④ 그래도 실패 시 제56조 실제 원문 스니펫을 debug로 반환(구조 확인용)
 *
 * http get 함수 주입 가능(테스트/모킹). 조문을 임의 생성하지 않는다.
 */

const https = require('https');
const enc = encodeURIComponent;

const TARGETS = [
  { law: '의료법', article: '제56조', title: '의료광고의 금지 등' },
  { law: '의료법', article: '제57조', title: '의료광고의 심의' },
  { law: '의료법', article: '제57조의2', title: '의료광고에 관한 심의위원회' },
  { law: '의료법', article: '제57조의3', title: '자율심의기구의 심의 등에 대한 모니터링' },
];

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

function pick(re, s) { const m = (s || '').match(re); return m ? m[1] : ''; }
function clean(s) {
  return (s || '').replace(/<!\[CDATA\[|\]\]>/g, '').replace(/<[^>]+>/g, ' ')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
}
function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function hasErr(b) { return !b || /<error|로그인이 필요|허용되지 않|사용자ID|등록되지/.test(b); }

// 법령명(언더스코어 유무·태그 변형 모두 허용)
function lawNameOf(body) {
  return clean(
    pick(/<법령명_?한글>([\s\S]*?)<\/법령명_?한글>/, body) ||
    pick(/<법령명>([\s\S]*?)<\/법령명>/, body)
  );
}

// lawSearch 결과에서 '의료법' 정확 일치 MST. 없으면 '' (엉뚱한 폴백 금지).
// 주의: 결과 태그는 <law id="1"> 처럼 속성이 붙는다 → <law\b[^>]*> 로 매칭.
function selectMst(searchBody) {
  const blocks = searchBody.match(/<law\b[^>]*>[\s\S]*?<\/law>/g) || [];
  const matches = blocks.filter(b => lawNameOf(b) === '의료법');
  if (!matches.length) return '';
  // 현행본 우선(연혁본 배제)
  const current = matches.find(b => /현행/.test(pick(/<현행연혁코드>([\s\S]*?)<\/현행연혁코드>/, b)));
  return pick(/<법령일련번호>(\d+)<\/법령일련번호>/, current || matches[0]);
}

function labelOf(no, branch) {
  const b = String(branch || '').replace(/[^0-9]/g, '');
  return b && b !== '0' ? `제${no}조의${parseInt(b, 10)}` : `제${no}조`;
}

// 본문 body에서 대상 조문 추출(2중 전략)
function parseArticles(body, mst) {
  const out = [];
  // 전략 1: <조문단위>
  const units = body.match(/<조문단위>[\s\S]*?<\/조문단위>/g) || [];
  for (const u of units) {
    const no = pick(/<조문번호>(\d+)<\/조문번호>/, u);
    if (!no) continue;
    const label = labelOf(no, pick(/<조문가지번호>([\s\S]*?)<\/조문가지번호>/, u));
    const t = TARGETS.find(x => x.article === label);
    if (!t) continue;
    const title = clean(pick(/<조문제목>([\s\S]*?)<\/조문제목>/, u)) || t.title;
    const text = clean(u);
    if (text) out.push({ law: t.law, article: label, title, text, mst });
  }
  if (out.length) return { statutes: out, via: '조문단위', units: units.length };

  // 전략 2: <조문내용> 블록에서 대상 조문 라벨로 시작하는 것 매칭
  const contents = body.match(/<조문내용>[\s\S]*?<\/조문내용>/g) || [];
  for (const c of contents) {
    const text = clean(c);
    for (const t of TARGETS) {
      if (new RegExp('^' + esc(t.article) + '\\s*[\\(（]').test(text) && !out.find(o => o.article === t.article)) {
        out.push({ law: t.law, article: t.article, title: t.title, text, mst });
      }
    }
  }
  return { statutes: out, via: '조문내용', units: units.length, contents: contents.length };
}

/**
 * @param {string} oc  법령API OC
 * @param {object} opts { get }
 */
async function fetchStatutes(oc, opts = {}) {
  const get = opts.get || defaultGet;
  if (!oc) return { status: 'pending', reason: 'LAW_OC(OC) 미설정 — open.law.go.kr에서 무료 발급 필요', statutes: [] };

  let body = '', mst = '', via = '';

  // ① 법령명 직접 조회
  try {
    const r = await get(`https://www.law.go.kr/DRF/lawService.do?OC=${enc(oc)}&target=law&type=XML&LM=${enc('의료법')}`);
    if (r.status === 200 && !hasErr(r.body) && lawNameOf(r.body) === '의료법') { body = r.body; via = 'LM'; mst = pick(/법령일련번호>(\d+)</, r.body); }
  } catch (e) { /* 폴백 */ }

  // ② 폴백: 검색 → 정확 일치 MST → 재조회
  if (!body) {
    let probe;
    try {
      probe = await get(`https://www.law.go.kr/DRF/lawSearch.do?OC=${enc(oc)}&target=law&type=XML&query=${enc('의료법')}&display=30`);
    } catch (e) {
      return { status: 'error', reason: 'law.go.kr 네트워크 도달 불가: ' + e.message, statutes: [] };
    }
    if (probe.status !== 200 || hasErr(probe.body)) {
      return { status: 'error', reason: `법령API 응답 이상(status ${probe.status}) — OC 유효성 확인`, statutes: [], debug: { head: (probe.body || '').slice(0, 200) } };
    }
    mst = selectMst(probe.body);
    if (!mst) return { status: 'error', reason: "검색 결과에서 '의료법' 정확 일치를 찾지 못함", statutes: [], debug: { searchHead: probe.body.slice(0, 400) } };
    try {
      const r = await get(`https://www.law.go.kr/DRF/lawService.do?OC=${enc(oc)}&target=law&type=XML&MST=${mst}`);
      if (r.status === 200 && !hasErr(r.body)) { body = r.body; via = 'MST'; }
    } catch (e) {
      return { status: 'error', reason: '본문 조회 네트워크 실패: ' + e.message, statutes: [], mst };
    }
  }

  if (!body) return { status: 'error', reason: '의료법 본문 조회 실패', statutes: [], mst };
  const name = lawNameOf(body);
  if (name && name !== '의료법') {
    return { status: 'error', reason: `잘못된 법령 조회됨: ${name}`, statutes: [], mst, debug: { name, via } };
  }

  const parsed = parseArticles(body, mst);
  if (!parsed.statutes.length) {
    const i = body.indexOf('제56조');
    return {
      status: 'error',
      reason: `조문 매칭 0건(법령 ${name || '?'}, 조문단위 ${parsed.units}, 조문내용 ${parsed.contents || 0})`,
      statutes: [], mst,
      debug: { name, via, units: parsed.units, contents: parsed.contents || 0, has56: i >= 0, art56: i >= 0 ? body.slice(i - 30, i + 220) : '(제56조 없음)' },
    };
  }
  return { status: 'ok', mst, via, statutes: parsed.statutes };
}

module.exports = { fetchStatutes, TARGETS, _internal: { selectMst, labelOf, parseArticles, lawNameOf } };
