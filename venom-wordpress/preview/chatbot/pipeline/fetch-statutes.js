'use strict';

/**
 * 의료법 조문 전문 수집(CLI) — 공유 로직(lib/statute-fetcher.js) 사용.
 *
 * 사전 준비: https://open.law.go.kr 에서 OC 발급
 * 실행:  LAW_OC=<OC> node pipeline/fetch-statutes.js
 * 출력:  data/sources/statutes.json  (이후 build.js가 지식베이스에 통합)
 *
 * 네트워크/키 없으면 조문을 임의 생성하지 않고 status(pending/error)만 기록.
 * (Vercel 등 허용망 환경에서는 /api/statutes-refresh 엔드포인트로도 실행 가능)
 */

const fs = require('fs');
const path = require('path');
const { fetchStatutes } = require('../lib/statute-fetcher');

const OUT = path.resolve(__dirname, '..', 'data', 'sources', 'statutes.json');
const OC = process.env.LAW_OC || process.env.OC;

(async () => {
  const result = await fetchStatutes(OC);
  const doc = {
    updated: new Date().toISOString(),
    status: result.status,
    source: 'law.go.kr DRF',
    ...(result.reason ? { reason: result.reason } : {}),
    ...(result.mst ? { mst: result.mst } : {}),
    howTo: 'LAW_OC=<OC> node pipeline/fetch-statutes.js  (OC: open.law.go.kr 발급)',
    statutes: result.statutes,
  };
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 2) + '\n', 'utf8');
  if (result.status === 'ok') {
    console.log(`✅ 조문 ${result.statutes.length}건 수집 → ${OUT}`);
    console.log('   다음: node pipeline/build.js 로 지식베이스에 통합');
  } else {
    console.log(`⏸  status=${result.status}: ${result.reason}`);
    console.log('   →', OUT);
  }
})().catch(e => { console.error('수집 실패:', e.message); process.exitCode = 1; });
