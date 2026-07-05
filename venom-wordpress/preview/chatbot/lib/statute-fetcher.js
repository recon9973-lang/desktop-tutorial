'use strict';

/**
 * 의료법 조문 수집 공유 로직 — 국가법령정보센터(law.go.kr) DRF Open API.
 * CLI(pipeline/fetch-statutes.js)와 API(api/statutes-refresh.js)가 공용으로 사용.
 *
 * http get 함수를 주입 가능(테스트/모킹). 기본은 https.
 * 조문을 임의 생성하지 않는다 — 수집 실패 시 status!=='ok' 로 그대로 보고(법률 정확성 보전).
 */

const https = require('https');

// 수집 대상(의료법 본문 조문). 시행령은 별도 law로 확장 가능.
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
    req.setTimeout(20000, () => { req.destroy(); reject(new Error('타임아웃')); });
  });
}

function pick(re, s) { const m = s.match(re); return m ? m[1] : ''; }
function clean(s) { return s.replace(/<!\[CDATA\[|\]\]>/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); }

/**
 * @param {string} oc  법령API OC(이메일 앞부분)
 * @param {object} opts { get } 주입형 http
 * @returns {Promise<{status:'ok'|'pending'|'error', reason?:string, mst?:string, statutes:Array}>}
 */
async function fetchStatutes(oc, opts = {}) {
  const get = opts.get || defaultGet;
  if (!oc) return { status: 'pending', reason: 'LAW_OC(OC) 미설정 — open.law.go.kr에서 무료 발급 필요', statutes: [] };

  let probe;
  try {
    probe = await get(`https://www.law.go.kr/DRF/lawSearch.do?OC=${encodeURIComponent(oc)}&target=law&type=XML&query=${encodeURIComponent('의료법')}`);
  } catch (e) {
    return { status: 'error', reason: 'law.go.kr 네트워크 도달 불가: ' + e.message, statutes: [] };
  }
  if (probe.status !== 200 || /<error|로그인|허용되지|사용자ID/.test(probe.body)) {
    return { status: 'error', reason: `법령API 응답 이상(status ${probe.status}) — OC 유효성/허용 IP 확인 필요`, statutes: [] };
  }

  const mst = pick(/<법령일련번호>(\d+)<\/법령일련번호>/, probe.body) || pick(/<MST>(\d+)<\/MST>/, probe.body);
  if (!mst) return { status: 'error', reason: '법령일련번호(MST) 파싱 실패', statutes: [] };

  const statutes = [];
  for (const t of TARGETS) {
    const num = t.article.replace(/제|조.*/g, '');           // "제57조의2" → "57"
    const sub = /의(\d+)/.test(t.article) ? RegExp.$1 : '0'; // 가지번호
    const jo = String(parseInt(num, 10)).padStart(4, '0') + String(parseInt(sub, 10)).padStart(2, '0');
    try {
      const r = await get(`https://www.law.go.kr/DRF/lawService.do?OC=${encodeURIComponent(oc)}&target=law&type=XML&MST=${mst}&JO=${jo}`);
      const raw = pick(/<조문내용>([\s\S]*?)<\/조문내용>/, r.body);
      const text = clean(raw);
      if (text) statutes.push({ law: t.law, article: t.article, title: t.title, text, mst });
    } catch (e) { /* 개별 조문 실패는 건너뜀 */ }
  }
  if (!statutes.length) return { status: 'error', reason: '조문 본문 수집 0건 — JO 파라미터/권한 확인', statutes: [] };
  return { status: 'ok', mst, statutes };
}

module.exports = { fetchStatutes, TARGETS };
