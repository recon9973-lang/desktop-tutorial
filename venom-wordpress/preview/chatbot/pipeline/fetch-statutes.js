'use strict';

/**
 * 의료법 조문 전문 수집 — 국가법령정보센터(law.go.kr) DRF Open API 클라이언트.
 * 수집 대상: 의료법 제56·57조, 시행령 제23·24조 등(TARGETS).
 *
 * 사전 준비:
 *   1) https://open.law.go.kr 에서 OC(이메일 앞부분) 발급
 *   2) 실행:  LAW_OC=<발급받은OC> node pipeline/fetch-statutes.js
 *
 * 출력: data/sources/statutes.json (조문 원문 + 시행일·개정정보)
 *       이후 build.js가 이를 지식베이스에 통합(원문 근거 보강).
 *
 * 주의: 조문은 공공저작물이나, 본 스크립트는 "임의 생성"을 하지 않는다.
 *       네트워크/키가 없으면 수집을 건너뛰고 pending 상태만 기록한다(법률 정확성 보전).
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const OUT = path.resolve(__dirname, '..', 'data', 'sources', 'statutes.json');
const OC = process.env.LAW_OC || process.env.OC;

// 수집 대상(법령ID·조문). MST(법령 마스터번호)는 최신본 조회로 획득.
const TARGETS = [
  { law: '의료법', article: '제56조', title: '의료광고의 금지 등' },
  { law: '의료법', article: '제57조', title: '의료광고의 심의' },
  { law: '의료법 시행령', article: '제23조', title: '의료광고의 금지 기준' },
  { law: '의료법 시행령', article: '제24조', title: '의료광고의 심의' },
];

function get(url) {
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

function writePending(reason) {
  const doc = {
    updated: new Date().toISOString(),
    status: 'pending',
    reason,
    targets: TARGETS,
    howTo: 'https://open.law.go.kr 에서 OC 발급 후  LAW_OC=<OC> node pipeline/fetch-statutes.js',
    statutes: [],
  };
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 2) + '\n', 'utf8');
  console.log('⏸  조문 수집 보류(pending) 기록:', reason);
  console.log('   →', OUT);
}

async function main() {
  if (!OC) return writePending('LAW_OC(OC) 미설정 — 법령API 키 없음');

  // 도달성 확인
  let probe;
  try {
    probe = await get(`https://www.law.go.kr/DRF/lawSearch.do?OC=${encodeURIComponent(OC)}&target=law&type=XML&query=${encodeURIComponent('의료법')}`);
  } catch (e) {
    return writePending('네트워크 도달 불가(law.go.kr): ' + e.message);
  }
  if (probe.status !== 200 || /<error|로그인|허용되지/.test(probe.body)) {
    return writePending(`법령API 응답 이상(status ${probe.status}) — OC 유효성/허용 IP 확인 필요`);
  }

  // MST 추출 → 조문 본문 조회(lawService target=law, JO=조문)
  const mst = (probe.body.match(/<법령일련번호>(\d+)<\/법령일련번호>/) || [])[1];
  const statutes = [];
  for (const t of TARGETS.filter(x => x.law === '의료법')) {
    const jo = String(parseInt(t.article.replace(/[^0-9]/g, ''), 10)).padStart(4, '0') + '00';
    try {
      const r = await get(`https://www.law.go.kr/DRF/lawService.do?OC=${encodeURIComponent(OC)}&target=law&type=XML&MST=${mst}&JO=${jo}`);
      const text = (r.body.match(/<조문내용>([\s\S]*?)<\/조문내용>/) || [])[1] || '';
      statutes.push({ law: t.law, article: t.article, title: t.title, text: text.replace(/<!\[CDATA\[|\]\]>/g, '').trim(), mst });
      console.log('  ✓', t.law, t.article);
    } catch (e) {
      console.log('  ✗', t.article, e.message);
    }
  }
  fs.writeFileSync(OUT, JSON.stringify({ updated: new Date().toISOString(), status: 'ok', source: 'law.go.kr DRF', statutes }, null, 2) + '\n', 'utf8');
  console.log(`✅ 조문 ${statutes.length}건 수집 → ${OUT}`);
}

main().catch(e => { console.error('수집 실패:', e.message); process.exitCode = 1; });
