'use strict';

/**
 * 의료법 조문 수집 공유 로직 — 국가법령정보센터(law.go.kr) DRF Open API.
 * CLI(pipeline/fetch-statutes.js)와 API(api/statutes-refresh.js)가 공용으로 사용.
 *
 * 방식: ① lawSearch로 '의료법' 법령일련번호(MST) 조회
 *       ② lawService로 의료법 전체 XML 1회 조회 → <조문단위>를 파싱해 제56·57조 등 추출
 *       (개별 JO 파라미터 방식은 불안정 → 전체 파싱이 안정적)
 *
 * http get 함수 주입 가능(테스트/모킹). 조문을 임의 생성하지 않는다 —
 * 수집 실패 시 status!=='ok' + 진단정보(debug)로 그대로 보고(법률 정확성 보전).
 */

const https = require('https');

// 수집 대상(의료법 본문 조문). label로 매칭.
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
function clean(s) { return (s || '').replace(/<!\[CDATA\[|\]\]>/g, '').replace(/<[^>]+>/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim(); }

// lawSearch 결과에서 '의료법'(정확 일치) 법령일련번호 선택. 실패 시 첫 결과.
function selectMst(body) {
  const blocks = body.match(/<law>[\s\S]*?<\/law>/g) || [];
  for (const b of blocks) {
    const nm = clean(pick(/<법령명한글>([\s\S]*?)<\/법령명한글>/, b));
    if (nm === '의료법') { const m = pick(/<법령일련번호>(\d+)<\/법령일련번호>/, b); if (m) return m; }
  }
  return pick(/<법령일련번호>(\d+)<\/법령일련번호>/, body) || pick(/<MST>(\d+)<\/MST>/, body);
}

// 조문 라벨 생성: 조문번호 + 조문가지번호 → "제57조" / "제57조의2"
function labelOf(no, branch) {
  const b = String(branch || '').replace(/[^0-9]/g, '');
  return b && b !== '0' ? `제${no}조의${parseInt(b, 10)}` : `제${no}조`;
}

/**
 * @param {string} oc  법령API OC
 * @param {object} opts { get }
 * @returns {Promise<{status:'ok'|'pending'|'error', reason?, mst?, statutes:Array, debug?}>}
 */
async function fetchStatutes(oc, opts = {}) {
  const get = opts.get || defaultGet;
  if (!oc) return { status: 'pending', reason: 'LAW_OC(OC) 미설정 — open.law.go.kr에서 무료 발급 필요', statutes: [] };

  // ① MST 조회
  let probe;
  try {
    probe = await get(`https://www.law.go.kr/DRF/lawSearch.do?OC=${encodeURIComponent(oc)}&target=law&type=XML&query=${encodeURIComponent('의료법')}&display=20`);
  } catch (e) {
    return { status: 'error', reason: 'law.go.kr 네트워크 도달 불가: ' + e.message, statutes: [] };
  }
  if (probe.status !== 200 || /<error|로그인|허용되지|사용자ID|등록되지/.test(probe.body)) {
    return { status: 'error', reason: `법령API 응답 이상(status ${probe.status}) — OC 유효성 확인`, statutes: [], debug: { probeHead: (probe.body || '').slice(0, 200) } };
  }
  const mst = selectMst(probe.body);
  if (!mst) return { status: 'error', reason: '법령일련번호(MST) 파싱 실패', statutes: [], debug: { probeHead: probe.body.slice(0, 200) } };

  // ② 의료법 전체 XML 조회 → 조문 파싱
  let full;
  try {
    full = await get(`https://www.law.go.kr/DRF/lawService.do?OC=${encodeURIComponent(oc)}&target=law&type=XML&MST=${mst}`);
  } catch (e) {
    return { status: 'error', reason: '본문 조회 네트워크 실패: ' + e.message, statutes: [], mst };
  }
  if (probeHasError(full.body)) {
    return { status: 'error', reason: `본문 조회 응답 이상(status ${full.status})`, statutes: [], mst, debug: { head: (full.body || '').slice(0, 200) } };
  }

  const units = full.body.match(/<조문단위>[\s\S]*?<\/조문단위>/g) || [];
  const statutes = [];
  for (const u of units) {
    const no = pick(/<조문번호>(\d+)<\/조문번호>/, u);
    if (!no) continue;
    const branch = pick(/<조문가지번호>([\s\S]*?)<\/조문가지번호>/, u);
    const label = labelOf(no, branch);
    const target = TARGETS.find(t => t.article === label);
    if (!target) continue;
    const title = clean(pick(/<조문제목>([\s\S]*?)<\/조문제목>/, u)) || target.title;
    const text = clean(u);            // 조문단위 전체(제목·항·호 포함) → 원문 텍스트
    if (text) statutes.push({ law: target.law, article: label, title, text, mst });
  }

  if (!statutes.length) {
    return {
      status: 'error',
      reason: `조문 매칭 0건 — 전체법령 파싱 실패(조문단위 ${units.length}개 발견). XML 태그 구조 확인 필요.`,
      statutes: [], mst,
      debug: { units: units.length, sample: (full.body || '').slice(0, 300) },
    };
  }
  return { status: 'ok', mst, statutes };
}

function probeHasError(body) {
  return !body || /<error|로그인이 필요|허용되지 않|사용자ID/.test(body);
}

module.exports = { fetchStatutes, TARGETS, _internal: { selectMst, labelOf, clean } };
