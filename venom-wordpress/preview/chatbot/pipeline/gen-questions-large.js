'use strict';

/**
 * 대규모 질문 생성기 (오더 2번 확장: 법조문 분석 기반 10만 + 합성 9만 = 19만)
 *
 *  - law-based(≈100k): 의료법·시행령·시행규칙·심의기준의 각 조항/호/요건을 분석해
 *    시술·매체·진료과목·표현·지역·어투 슬롯과 조합한 "예상질문". 각 질문에 예상 근거조항 라벨.
 *  - synthetic(≈90k): 기존 조합형 합성질문 확장.
 *
 * 출력: data/eval/questions-full.jsonl  (JSONL, 대용량 — .gitignore로 배포 제외)
 *       data/eval/questions-manifest.json (카운트·분포)
 *       data/eval/questions-sample.json  (검수용 표본 5,000)
 *       data/eval/holdout-large.json     (성능측정 전용 홀드아웃 ids, 2%)
 *
 * 실행: node pipeline/gen-questions-large.js [총목표]  (기본 190000)
 * 결정론적(무작위 없음).
 */

const fs = require('fs');
const path = require('path');

const OUT = path.resolve(__dirname, '..', 'data', 'eval');
const TARGET = parseInt(process.argv[2], 10) || 190000;
const LAW_TARGET = 100000, SYNTH_TARGET = TARGET - LAW_TARGET;
const BUILT_AT = process.env.BUILD_TS || new Date().toISOString();

// ── 슬롯(확장) ────────────────────────────────────────────────────
const 진료과목 = ['성형외과','피부과','치과','한의원','정형외과','안과','내과','이비인후과','산부인과','비뇨의학과','재활의학과','가정의학과','신경외과','흉부외과','마취통증의학과','영상의학과','정신건강의학과','가정의학과'];
const 매체 = ['블로그','인스타그램','유튜브','병원 홈페이지','네이버 카페','현수막','버스 외부 광고','신문 지면','인터넷 배너','페이스북','카카오톡 채널','옥외 전광판','지하철 광고','유튜브 쇼츠','틱톡','네이버 파워링크','당근마켓','앱 푸시'];
const 시술 = ['임플란트','라식','보톡스','필러','지방흡입','치아교정','도수치료','모발이식','코성형','눈성형','레이저 제모','피부 리프팅','치아미백','탈모 치료','하지정맥류 수술','백내장 수술','위내시경','무릎 인공관절','디스크 수술','피부 미백','여드름 치료','비만 치료'];
const 표현 = ['세계 최초','국내 유일','100% 완치','부작용 없는','최저가 보장','통증 없는','흉터 없이','영구적인 효과','강남 1위','후회 없는 선택','기적 같은','완벽한','단 한 번에','가장 안전한','검증된 명의','만족도 1위','전문','명의','최고의','유일무이한'];
const 지역 = ['강남','서울','부산','대구','분당','송파','인천','광주','대전','수원','일산','평촌'];
const 어투Q = ['괜찮나요?','의료법 위반인가요?','사전심의를 통과할 수 있나요?','문제가 되나요?','가능한가요?','주의할 점은 무엇인가요?','어떻게 해야 하나요?','허용되나요?'];

function cross(...arrs) { return arrs.reduce((a, arr) => a.flatMap(x => arr.map(y => [...x, y])), [[]]); }
function* combos(gen) { yield* gen(); }

// ── 법조문 분석 포인트(예상질문 생성 단위) ─────────────────────────
// 각 포인트: 근거조항 + 질문 생성 함수(슬롯 조합)
const LAW_POINTS = [
  // 의료법 제56조 제2항 14개 금지호 — 각 호를 시술×매체×어투로 전개
  { refs:['의료법 제56조 제2항 제1호'], gen:()=>cross(시술,어투Q).map(([s,a])=>`${s}에 대해 "신의료기술평가를 받지 않았다"는 광고를 하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제2호'], gen:()=>cross(진료과목,매체,시술,어투Q).map(([d,m,s,a])=>`${d}가 ${m}에 ${s} 치료경험담·후기를 올리면 ${a}`) },
  { refs:['의료법 제56조 제2항 제2호'], gen:()=>cross(시술,매체,진료과목).map(([s,m,d])=>`${d}가 ${s} 전후 사진을 ${m}에 게시하려면 어떤 요건을 갖춰야 하나요?`) },
  { refs:['의료법 제56조 제2항 제3호'], gen:()=>cross(진료과목,시술,표현,어투Q).map(([d,s,e,a])=>`${d}의 ${s} 광고에 "${e}"이라는 거짓·과장 표현을 쓰면 ${a}`) },
  { refs:['의료법 제56조 제2항 제4호'], gen:()=>cross(진료과목,시술,어투Q).map(([d,s,a])=>`${d} 광고에서 "다른 병원보다 ${s}를 잘한다"고 비교하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제5호'], gen:()=>cross(진료과목,어투Q).map(([d,a])=>`${d} 광고에서 다른 의료기관을 비방하는 표현을 쓰면 ${a}`) },
  { refs:['의료법 제56조 제2항 제6호'], gen:()=>cross(시술,매체).map(([s,m])=>`${s} 수술 장면을 ${m}에 노출하는 광고는 가능한가요?`) },
  { refs:['의료법 제56조 제2항 제7호'], gen:()=>cross(시술,어투Q).map(([s,a])=>`${s} 광고에서 심각한 부작용 정보를 누락하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제8호'], gen:()=>cross(진료과목,시술,표현,어투Q).map(([d,s,e,a])=>`${d}의 ${s} 광고에 "${e}"으로 객관적 사실을 과장하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제4호'], gen:()=>cross(지역,진료과목,시술,어투Q).map(([g,d,s,a])=>`${g} ${d}가 ${s}에 대해 "다른 병원보다 우수하다"고 비교광고하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제9호'], gen:()=>cross(진료과목,어투Q).map(([d,a])=>`${d} 광고에 법적 근거 없는 자격·명칭을 표방하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제10호'], gen:()=>cross(매체,어투Q).map(([m,a])=>`${m}에 기사(記事)나 전문가 의견 형태로 의료광고를 하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제11호','의료법 제57조'], gen:()=>cross(매체,어투Q).map(([m,a])=>`${m} 광고를 사전심의 없이 게재하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제12호','의료법 제27조 제3항'], gen:()=>cross(진료과목,어투Q).map(([d,a])=>`${d}가 외국인환자 유치를 위한 국내광고를 하면 ${a}`) },
  { refs:['의료법 제56조 제2항 제13호'], gen:()=>cross(시술,['할인','면제','이벤트'],어투Q).map(([s,p,a])=>`${s} 비급여 진료비 ${p} 광고에서 소비자를 오인시키면 ${a}`) },
  { refs:['의료법 제56조 제2항 제14호'], gen:()=>cross(진료과목,어투Q).map(([d,a])=>`${d} 광고에 상장·감사장·인증·보증·추천 내용을 쓰면 ${a}`) },
  { refs:['의료법 제56조 제3항 제1호'], gen:()=>cross(시술).map(([s])=>`${s} 광고를 방송으로 하는 것은 가능한가요?`) },
  // 제57조 심의 요건/절차
  { refs:['의료법 제57조 제1항','의료법 시행령 제24조'], gen:()=>cross(지역,진료과목,매체,어투Q).map(([g,d,m,a])=>`${g} ${d}가 ${m}에 광고할 때 사전심의 대상인지 ${a}`) },
  { refs:['의료법 제57조 제3항'], gen:()=>cross(진료과목).map(([d])=>`${d}가 명칭·소재지·전화번호만 광고하면 심의를 받아야 하나요?`) },
  { refs:['의료법 제57조 제8항'], gen:()=>['의료광고 심의 유효기간은 몇 년인가요?','심의 유효기간이 지나면 어떻게 하나요?','유효기간 만료 몇 개월 전에 재심의를 신청해야 하나요?','2018년 9월 28일 이전 심의필의 유효기간은 어떻게 되나요?'].map(q=>`${q}`) },
  { refs:['의료법 제57조의2'], gen:()=>cross(진료과목).map(([d])=>`${d} 광고는 어느 심의위원회에서 심의하나요?`) },
  // 심의 실무(협회 자료 기반)
  { refs:['의료법 제57조'], gen:()=>cross(진료과목,['심의 수수료는 얼마인가요','구비서류는 무엇인가요','심의 절차는 어떻게 되나요','조건부승인이 무엇인가요','사후통보는 어떻게 하나요','심의필번호는 어떻게 표기하나요','재심의청구는 어떻게 하나요']).map(([d,q])=>`${d} 의료광고 ${q}?`) },
  // 표시광고법
  { refs:['표시광고법 제3조'], gen:()=>cross(매체,['대가를 받은 후기','협찬 표시 없는 추천글','체험단 후기']).map(([m,x])=>`${m}에 ${x}를 올리면 표시광고법상 문제가 되나요?`) },
  // 전문병원·자격
  { refs:['의료법 제56조 제2항 제9호','의료법 제3조의5'], gen:()=>cross(지역,진료과목).map(([g,d])=>`${g} ${d}가 "전문병원"이라는 표현을 광고에 써도 되나요?`) },
];

function collect(genFns, target, origin, refsOf) {
  const seen = new Set(), items = [];
  // 각 포인트에서 라운드로빈으로 균형 수집
  const iters = genFns.map(f => ({ list: f.gen(), refs: f.refs || (refsOf && refsOf()) , i: 0 }));
  let progressed = true;
  while (items.length < target && progressed) {
    progressed = false;
    for (const it of iters) {
      if (it.i < it.list.length) {
        const q = it.list[it.i++].trim();
        progressed = true;
        const key = q.replace(/\s+/g, '');
        if (seen.has(key)) continue;
        seen.add(key);
        items.push({ q, refs: it.refs, origin });
        if (items.length >= target) break;
      }
    }
  }
  return items;
}

// 합성(조합형) — 표현×시술×매체×과목×어투 대량
function synthPoints() {
  return [
    { refs:['의료법 제56조 제2항 제3호','의료법 제56조 제2항 제8호'], gen:()=>cross(시술,표현,매체,어투Q).map(([s,e,m,a])=>`${m}에 올리는 ${s} 광고에 "${e}" 표현을 써도 ${a}`) },
    { refs:['의료법 제56조 제2항 제2호'], gen:()=>cross(진료과목,매체,시술).map(([d,m,s])=>`${d}가 ${m}에 ${s} 후기를 올려도 되나요?`) },
    { refs:['의료법 제56조 제2항 제13호'], gen:()=>cross(시술,['할인','선착순','무료 체험','1+1'],매체,지역).map(([s,p,m,g])=>`${g} 지역 ${m}에 ${s} ${p} 이벤트 광고를 하려면 주의할 점은?`) },
    { refs:['의료법 제57조 제1항'], gen:()=>cross(진료과목,매체,지역).map(([d,m,g])=>`${g} ${d}가 ${m}에 의료광고를 하려면 사전심의가 필요한가요?`) },
  ];
}

function main() {
  const law = collect(LAW_POINTS, LAW_TARGET, 'law');
  const synth = collect(synthPoints(), SYNTH_TARGET, 'synthetic');
  // 통합 + 전역 중복 제거
  const seen = new Set(law.map(x => x.q.replace(/\s+/g, '')));
  const all = law.slice();
  for (const s of synth) { const k = s.q.replace(/\s+/g, ''); if (!seen.has(k)) { seen.add(k); all.push(s); } }

  // id 부여 + JSONL 기록(스트리밍)
  fs.mkdirSync(OUT, { recursive: true });
  const ws = fs.createWriteStream(path.join(OUT, 'questions-full.jsonl'), 'utf8');
  const byOrigin = {}; const holdout = [];
  all.forEach((it, i) => {
    it.id = (it.origin === 'law' ? 'L' : 'S') + String(i + 1).padStart(6, '0');
    byOrigin[it.origin] = (byOrigin[it.origin] || 0) + 1;
    if (i % 50 === 0) holdout.push(it.id);           // 2% 홀드아웃
    ws.write(JSON.stringify(it) + '\n');
  });
  ws.end();

  fs.writeFileSync(path.join(OUT, 'questions-manifest.json'), JSON.stringify({
    updated: BUILT_AT, total: all.length, target: TARGET, byOrigin,
    lawTarget: LAW_TARGET, synthTarget: SYNTH_TARGET, holdout: holdout.length,
    note: '전체 질문은 questions-full.jsonl(대용량, 배포 제외). 결정론적 생성기로 재현.',
  }, null, 2) + '\n');
  fs.writeFileSync(path.join(OUT, 'questions-sample.json'), JSON.stringify({
    updated: BUILT_AT, sample: all.filter((_, i) => i % Math.ceil(all.length / 5000) === 0).slice(0, 5000),
  }, null, 1) + '\n');
  fs.writeFileSync(path.join(OUT, 'holdout-large.json'), JSON.stringify({ updated: BUILT_AT, count: holdout.length, ids: holdout }) + '\n');

  console.log(`✅ 대규모 질문 ${all.length}개 (law ${byOrigin.law||0} / synthetic ${byOrigin.synthetic||0})`);
  console.log(`   홀드아웃 ${holdout.length} · questions-full.jsonl(배포 제외) + manifest + sample(5k) 저장`);
  if (all.length < TARGET) console.log(`   ⚠️ 고유 조합 ${all.length} < 목표 ${TARGET} — 슬롯 추가 필요`);
}

main();
