'use strict';

/**
 * 평가·개선 루프 (오더 3번: 질문 → 답변 → 검토 → 진단 → 수정 → 재질문)
 *
 * 지식베이스+검색기 품질을 10,000 질문셋으로 자동 채점한다.
 *  - 검토(오프라인·키 불필요): "인용 적중률" — 질문의 예상 근거조항(조 단위)이
 *    검색된 근거(top-K)에 포함되는가. RAG의 근거 접지 정확도를 측정.
 *  - 문구진단 정합성: 금지표현이 포함된 질문은 diagnose가 실제로 위반을 탐지하는가.
 *  - 진단: 카테고리별 적중률 → 임계 미달 카테고리와 원인·개선 제안 산출.
 *  - (선택) LLM-as-Judge: OPENAI_API_KEY 있으면 정답 품질 1~5점 채점(확장 지점).
 *
 * 실행:  node pipeline/eval-loop.js            # 홀드아웃 1,000개 평가
 *        node pipeline/eval-loop.js --all      # 전체 10,000개
 *        node pipeline/eval-loop.js --rounds 3 # 반복 측정(개선 반영 확인)
 * 출력:  data/eval/eval-report.json
 */

const fs = require('fs');
const path = require('path');
const { retrieve } = require('../lib/retriever');
const rag = require('../lib/rag');

const EVAL_DIR = path.resolve(__dirname, '..', 'data', 'eval');
const questions = JSON.parse(fs.readFileSync(path.join(EVAL_DIR, 'questions.json'), 'utf8'));
const holdout = new Set(JSON.parse(fs.readFileSync(path.join(EVAL_DIR, 'holdout-ids.json'), 'utf8')).ids);

const ALL = process.argv.includes('--all');
const ROUNDS = (() => { const i = process.argv.indexOf('--rounds'); return i > -1 ? parseInt(process.argv[i + 1], 10) || 1 : 1; })();
const THRESHOLD = 0.7;

const joNum = s => (String(s).match(/제\s*(\d+)\s*조/) || [])[1];        // "제56조 제2항" → "56"
const expectedJo = refs => new Set(refs.map(joNum).filter(Boolean));

// 금지표현 사전(문구진단 정합성 체크용) — validator와 동일 원천
let FORBIDDEN = [];
try { FORBIDDEN = require('../../lib/medical-ad-validator').FORBIDDEN; } catch (e) {}

function evaluateOne(item) {
  const hits = retrieve(item.q, 5);
  const gotJo = new Set(hits.flatMap(h => h.chunk.legalRefs.map(joNum)).filter(Boolean));
  const want = expectedJo(item.refs);
  const citationHit = [...want].some(j => gotJo.has(j));   // 예상 조문 중 하나라도 검색됨

  // 문구진단 정합성: 질문에 금지표현이 들어간 경우 diagnose가 탐지해야 함
  let diagnoseOk = null;
  const hasForbidden = FORBIDDEN.some(w => item.q.includes(w));
  if (hasForbidden) {
    const d = rag.diagnoseCopy(item.q);
    diagnoseOk = d.pass === false && d.forbidden.length > 0;
  }
  return { id: item.id, cat: item.cat, citationHit, diagnoseOk, topRef: hits[0] ? hits[0].chunk.legalRefs[0] : null };
}

function runRound(sample) {
  const perCat = {};
  let hit = 0, diagTotal = 0, diagOk = 0;
  for (const item of sample) {
    const r = evaluateOne(item);
    if (r.citationHit) hit++;
    if (r.diagnoseOk !== null) { diagTotal++; if (r.diagnoseOk) diagOk++; }
    const c = perCat[r.cat] || (perCat[r.cat] = { n: 0, hit: 0 });
    c.n++; if (r.citationHit) c.hit++;
  }
  return {
    n: sample.length,
    citationAccuracy: +(hit / sample.length).toFixed(3),
    diagnoseAccuracy: diagTotal ? +(diagOk / diagTotal).toFixed(3) : null,
    diagnoseChecked: diagTotal,
    perCategory: Object.fromEntries(Object.entries(perCat).map(([k, v]) => [k, +(v.hit / v.n).toFixed(3)])),
  };
}

function diagnose(round) {
  const weak = Object.entries(round.perCategory).filter(([, acc]) => acc < THRESHOLD).sort((a, b) => a[1] - b[1]);
  return weak.map(([cat, acc]) => ({
    category: cat, accuracy: acc,
    suggestion: suggestFor(cat),
  }));
}

// 진단→수정 제안(안전·비파괴적: 사람이 검토 후 적용)
function suggestFor(cat) {
  if (cat.startsWith('사전심의')) return '조문 전문(제57조·시행령 제24조) 보강 + 매체 동의어 확장(fetch-statutes.js/synonyms.json)';
  if (cat.startsWith('표시광고법')) return '표시광고법 조항 청크 세분화 + "대가성/협찬/기만" 동의어 추가';
  if (cat.startsWith('지역광고')) return '지역 슬롯은 근거조항과 약결합 — 유인(제27조)·과장(제56조) 청크로 라우팅되도록 동의어/키워드 보강';
  if (cat.startsWith('자격명칭')) return '전문병원·자격명칭(제9호·제3조의5) 청크 세분화';
  return '해당 카테고리 근거조항 청크 세분화 또는 동의어 확장 검토';
}

function main() {
  const base = questions.items.filter(q => ALL || holdout.has(q.id));
  console.log(`평가 대상: ${base.length}개 (${ALL ? '전체' : '홀드아웃'}) · 라운드 ${ROUNDS}`);
  const rounds = [];
  for (let r = 1; r <= ROUNDS; r++) {
    const res = runRound(base);
    rounds.push(res);
    console.log(`\n[Round ${r}] 인용 적중률 ${(res.citationAccuracy * 100).toFixed(1)}% · 문구진단 정합 ${res.diagnoseAccuracy != null ? (res.diagnoseAccuracy * 100).toFixed(1) + '%' : 'n/a'} (검사 ${res.diagnoseChecked}건)`);
    const weak = diagnose(res);
    if (weak.length) {
      console.log('  약점 카테고리(< ' + THRESHOLD * 100 + '%):');
      weak.forEach(w => console.log(`   - ${w.category} ${(w.accuracy * 100).toFixed(1)}% → ${w.suggestion}`));
    } else {
      console.log('  모든 카테고리 임계 이상 ✅');
    }
  }

  const report = {
    updated: process.env.BUILD_TS || new Date().toISOString(),
    scope: ALL ? 'all-10000' : 'holdout-1000',
    threshold: THRESHOLD,
    llmJudge: !!process.env.OPENAI_API_KEY,
    rounds,
    diagnosis: diagnose(rounds[rounds.length - 1]),
    note: '인용 적중률=예상 근거조항(조 단위)이 top-5 검색근거에 포함된 비율. LLM-as-Judge는 키 설정 시 정답 품질 채점으로 확장.',
  };
  fs.writeFileSync(path.join(EVAL_DIR, 'eval-report.json'), JSON.stringify(report, null, 2) + '\n', 'utf8');
  console.log('\n📄 리포트 →', path.relative(process.cwd(), path.join(EVAL_DIR, 'eval-report.json')));
}

main();
