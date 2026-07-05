'use strict';

/**
 * 대규모 평가 루프 (오더 3번: 19만 질문셋에 대한 '딥러닝' 반복 학습 사이클)
 * questions-full.jsonl을 샘플링해 인용 적중률(예상 근거조항이 top-5 검색에 포함)을 측정하고
 * origin(법조문기반/합성)·근거조항별 약점을 진단한다.
 *
 * 실행: node pipeline/eval-large.js [샘플수]   (기본 6000)
 * 출력: data/eval/eval-large-report.json
 * (LLM 정답품질 채점은 배포 키(OPENAI_API_KEY)로 확장 — 여기선 오프라인 인용정밀도)
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { retrieve } = require('../lib/retriever');

const EVAL = path.resolve(__dirname, '..', 'data', 'eval');
const SAMPLE = parseInt(process.argv[2], 10) || 6000;
const joNum = s => (String(s).match(/제\s*(\d+)\s*조/) || [])[1];

async function main() {
  const file = path.join(EVAL, 'questions-full.jsonl');
  if (!fs.existsSync(file)) { console.error('questions-full.jsonl 없음 — gen-questions-large.js 먼저 실행'); process.exit(1); }
  // 총 라인 수 추정 위해 manifest 사용
  const total = JSON.parse(fs.readFileSync(path.join(EVAL, 'questions-manifest.json'), 'utf8')).total;
  const step = Math.max(1, Math.floor(total / SAMPLE));

  const rl = readline.createInterface({ input: fs.createReadStream(file), crlfDelay: Infinity });
  let idx = 0, evaluated = 0, hit = 0;
  const byOrigin = {}, byRef = {};
  for await (const line of rl) {
    if (idx++ % step !== 0) continue;
    let it; try { it = JSON.parse(line); } catch { continue; }
    const hits = retrieve(it.q, 5);
    const got = new Set(hits.flatMap(h => h.chunk.legalRefs.map(joNum)).filter(Boolean));
    const want = new Set((it.refs || []).map(joNum).filter(Boolean));
    const ok = [...want].some(j => got.has(j));
    evaluated++; if (ok) hit++;
    const o = byOrigin[it.origin] || (byOrigin[it.origin] = { n: 0, hit: 0 }); o.n++; if (ok) o.hit++;
    const rk = (it.refs && it.refs[0]) || '기타'; const r = byRef[rk] || (byRef[rk] = { n: 0, hit: 0 }); r.n++; if (ok) r.hit++;
  }

  const pct = (h, n) => n ? +(h / n * 100).toFixed(1) : 0;
  const originRep = Object.fromEntries(Object.entries(byOrigin).map(([k, v]) => [k, `${pct(v.hit, v.n)}% (${v.n})`]));
  const weak = Object.entries(byRef).filter(([, v]) => v.n >= 30 && v.hit / v.n < 0.7)
    .sort((a, b) => a[1].hit / a[1].n - b[1].hit / b[1].n).slice(0, 10)
    .map(([k, v]) => ({ ref: k, acc: pct(v.hit, v.n), n: v.n }));

  const report = {
    updated: process.env.BUILD_TS || new Date().toISOString(),
    scope: `large-sample ${evaluated}/${total}`,
    citationAccuracy: pct(hit, evaluated),
    byOrigin: originRep,
    weakByRef: weak,
    note: '인용 적중률=예상 근거조항(조 단위)이 top-5 검색근거에 포함된 비율. LLM 정답채점은 배포 키로 확장.',
  };
  fs.writeFileSync(path.join(EVAL, 'eval-large-report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`✅ 대규모 평가 완료 — 샘플 ${evaluated}개`);
  console.log(`   인용 적중률: ${report.citationAccuracy}%`);
  console.log(`   origin별: ${JSON.stringify(originRep)}`);
  console.log(`   약점 근거조항(<70%): ${weak.slice(0,6).map(w=>w.ref+' '+w.acc+'%').join(', ') || '없음'}`);
}
main();
