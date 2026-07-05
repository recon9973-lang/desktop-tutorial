'use strict';

/**
 * 질문 생성기 (오더 2번: 의료광고·심의 관련 질문 10,000개 생성)
 *
 * 실제 차원(진료과목·시술·매체·표현·어투)을 조합해 다양성 있는 질문을 생성.
 * 각 질문에 카테고리·예상 근거조항·난이도 라벨 부여 → 평가셋/합성 Q&A 코퍼스.
 * (실제 협회 FAQ·반려사례 질문은 수집 후 혼합 예정 — origin='synthetic')
 *
 * 실행:  node pipeline/gen-questions.js [목표개수]   (기본 10000)
 * 출력:  data/eval/questions.json  { count, byCategory, items:[{id,q,cat,refs,diff,origin}] }
 *        data/eval/holdout-ids.json  성능 측정 전용 홀드아웃(개선 오염 금지)
 *
 * 결정론적(무작위 없음): 카테고리 라운드로빈으로 균형 있게 목표 개수까지 수집.
 */

const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, '..', 'data', 'eval');
const TARGET = parseInt(process.argv[2], 10) || 10000;
const BUILT_AT = process.env.BUILD_TS || new Date().toISOString();

// ── 슬롯 ─────────────────────────────────────────────────────────
const 진료과목 = ['성형외과', '피부과', '치과', '한의원', '정형외과', '안과', '내과', '이비인후과', '산부인과', '비뇨의학과', '재활의학과', '가정의학과', '신경외과', '흉부외과'];
const 매체 = ['블로그', '인스타그램', '유튜브', '병원 홈페이지', '네이버 카페', '현수막', '버스 외부 광고', '신문 지면', '인터넷 배너', '페이스북', '카카오톡 채널', '옥외 전광판', '지하철 광고', '유튜브 쇼츠'];
const 시술 = ['임플란트', '라식', '보톡스', '필러', '지방흡입', '치아교정', '도수치료', '모발이식', '코성형', '눈성형', '레이저 제모', '피부 리프팅', '치아미백', '탈모 치료', '하지정맥류 수술', '백내장 수술', '위내시경', '무릎 인공관절'];
const 금지표현 = ['세계 최초', '국내 유일', '100% 완치', '부작용 없는', '최저가 보장', '통증 없는', '흉터 없이', '영구적인 효과', '강남 1위', '후회 없는 선택', '기적 같은', '완벽한', '단 한 번에', '가장 안전한', '검증된 명의', '만족도 1위'];
const 지역 = ['강남', '서울', '부산', '대구', '분당', '송파', '인천', '광주'];

// 어투(문장 종결) 변형 — 모두 문법적으로 성립하는 완결형 접미
const A1 = ['써도 의료법상 괜찮나요?', '쓰면 의료법 위반인가요?', '써도 사전심의를 통과할 수 있나요?', '사용해도 되는지 궁금합니다.'];
const A2 = ['올려도 되나요?', '게시하면 문제가 되나요?', '광고로 규제되나요?'];
const A3 = ['사전심의를 받아야 하나요?', '심의 대상인가요?', '광고 전에 어떤 절차가 필요한가요?'];

function cross(...arrs) { // 데카르트 곱
  return arrs.reduce((acc, arr) => acc.flatMap(a => arr.map(b => [...a, b])), [[]]);
}

// ── 카테고리별 템플릿 ────────────────────────────────────────────
const CATEGORIES = [
  {
    key: '금지유형-과장최상급', refs: ['의료법 제56조 제2항 제3호', '의료법 제56조 제2항 제8호'], diff: 'easy',
    gen: () => cross(시술, 금지표현, 매체, A1).map(([s, e, m, a]) => `${m}에 올리는 ${s} 광고에 "${e}"이라는 표현을 ${a}`),
  },
  {
    key: '금지유형-치료경험담', refs: ['의료법 제56조 제2항 제2호'], diff: 'medium',
    gen: () => cross(진료과목, 매체, A2).map(([d, m, a]) => `${d}에서 환자 치료 후기를 ${m}에 ${a}`),
  },
  {
    key: '금지유형-전후사진', refs: ['의료법 제56조 제2항 제2호'], diff: 'hard',
    gen: () => cross(시술, 매체).map(([s, m]) => `${s} 전후 비교 사진을 ${m}에 올리려면 어떤 요건을 갖춰야 하나요?`),
  },
  {
    key: '금지유형-비교비방', refs: ['의료법 제56조 제2항 제4호', '의료법 제56조 제2항 제5호'], diff: 'medium',
    gen: () => cross(진료과목, 시술).map(([d, s]) => `${d} 광고에서 "다른 병원보다 ${s}를 잘한다"는 비교 표현은 허용되나요?`),
  },
  {
    key: '사전심의-대상매체', refs: ['의료법 제57조 제1항', '의료법 시행령 제24조'], diff: 'medium',
    gen: () => cross(진료과목, 매체, A3).map(([d, m, a]) => `${d}가 ${m}에 광고하려면 ${a}`),
  },
  {
    key: '사전심의-절차유효기간', refs: ['의료법 제57조'], diff: 'easy',
    gen: () => cross(진료과목, ['심의 유효기간은 몇 년인가요?', '심의필 번호는 어떻게 표기하나요?', '배너와 랜딩페이지를 함께 심의받아야 하나요?', '심의 내용과 다르게 광고하면 어떻게 되나요?', '어느 자율심의기구에서 심의받나요?'])
      .map(([d, q]) => `${d} 광고의 ${q}`),
  },
  {
    key: '비급여-할인이벤트', refs: ['의료법 제56조 제2항 제13호', '의료법 제27조 제3항'], diff: 'medium',
    gen: () => cross(시술, ['할인', '선착순 이벤트', '무료 체험단', '1+1 이벤트', '친구 추천 할인'], 매체).map(([s, p, m]) => `${m}에서 ${s} ${p} 광고를 할 때 주의할 점은 무엇인가요?`),
  },
  {
    key: '표시광고법-기만후기', refs: ['표시광고법 제3조'], diff: 'hard',
    gen: () => cross(매체, ['대가를 받고 작성한 후기', '협찬 표시 없는 추천글', '체험단 후기'], 진료과목).map(([m, x, d]) => `${d}가 ${m}에 ${x}를 올리면 표시광고법상 문제가 되나요?`),
  },
  {
    key: '주체범위-대행', refs: ['의료법 제56조 제1항'], diff: 'easy',
    gen: () => cross(진료과목, 매체).map(([d, m]) => `${d} 원장이 아닌 마케팅 대행사가 ${m} 광고를 대신 올려도 되나요?`),
  },
  {
    key: '자격명칭-전문병원', refs: ['의료법 제56조 제2항 제9호', '의료법 제3조의5'], diff: 'medium',
    gen: () => cross(진역_또는_과목(), ['"전문병원"이라는 표현', '"○○ 전문"이라는 표현', '"특화 클리닉"이라는 표현', '"명의"라는 표현']).map(([d, x]) => `${d} 광고에 ${x}을 써도 되나요?`),
  },
  {
    key: '지역광고-유인', refs: ['의료법 제56조 제2항', '의료법 제27조 제3항'], diff: 'medium',
    gen: () => cross(지역, 진료과목, 시술.slice(0, 8)).map(([g, d, s]) => `${g} ${d}가 ${s} 관련 지역 타겟 광고를 할 때 유인·과장에 걸리지 않으려면 어떻게 해야 하나요?`),
  },
];

// 자격명칭 카테고리는 지역+과목 조합으로도 확장
function 진역_또는_과목() {
  return 진료과목.concat(cross(지역, 진료과목).map(([g, d]) => `${g} ${d}`));
}

function main() {
  const seen = new Set();
  const buckets = CATEGORIES.map(c => ({ cat: c, items: [] }));
  for (const b of buckets) {
    for (const q of b.cat.gen()) {
      const key = q.trim();
      if (seen.has(key)) continue;
      seen.add(key);
      b.items.push(key);
    }
  }
  // 라운드로빈으로 균형 있게 목표 개수까지 수집
  const items = [];
  let added = true, round = 0;
  while (items.length < TARGET && added) {
    added = false;
    for (const b of buckets) {
      if (round < b.items.length) {
        items.push({
          id: 'q-' + String(items.length + 1).padStart(5, '0'),
          q: b.items[round], cat: b.cat.key, refs: b.cat.refs, diff: b.cat.diff, origin: 'synthetic',
        });
        added = true;
        if (items.length >= TARGET) break;
      }
    }
    round++;
  }

  // 실제 FAQ 질문 증강(오더 2번 '질문 수집') — 있으면 코퍼스 앞에 편입
  try {
    const real = JSON.parse(fs.readFileSync(path.join(OUT_DIR, 'real-questions.json'), 'utf8'));
    const refOf = q => /심의필|유효기간|사후통보|심의 대상|매체/.test(q) ? ['의료법 제57조'] : /수수료|서류|절차|신청/.test(q) ? ['의료법 제57조', '의료법 시행규칙'] : ['의료법 제56조'];
    const realItems = (real.questions || []).map((q, i) => ({
      id: 'qr-' + String(i + 1).padStart(4, '0'), q, cat: '실제FAQ', refs: refOf(q), diff: 'real', origin: 'faq',
    }));
    items.unshift(...realItems);
    // id 재부여(순서 일관)
    items.forEach((it, i) => { if (it.origin === 'synthetic') it.id = 'q-' + String(i + 1).padStart(5, '0'); });
    console.log(`   + 실제 FAQ 질문 ${realItems.length}개 편입`);
  } catch (e) { /* real-questions 없으면 합성만 */ }

  const byCategory = {};
  for (const it of items) byCategory[it.cat] = (byCategory[it.cat] || 0) + 1;
  const totalCandidates = buckets.reduce((n, b) => n + b.items.length, 0);

  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, 'questions.json'),
    JSON.stringify({ updated: BUILT_AT, count: items.length, target: TARGET, candidatePool: totalCandidates, byCategory, items }) + '\n', 'utf8');

  const holdout = items.filter((_, i) => i % 10 === 0).map(x => x.id);
  fs.writeFileSync(path.join(OUT_DIR, 'holdout-ids.json'),
    JSON.stringify({ updated: BUILT_AT, count: holdout.length, note: '성능 측정 전용(개선에 오염 금지)', ids: holdout }) + '\n', 'utf8');

  console.log(`✅ 질문 ${items.length}개 생성 (목표 ${TARGET}, 고유 후보풀 ${totalCandidates})`);
  console.log('   카테고리 분포:', JSON.stringify(byCategory, null, 0));
  console.log(`   홀드아웃 평가셋: ${holdout.length}개`);
  if (items.length < TARGET) console.log(`   ⚠️ 후보풀 부족(${items.length}<${TARGET}) — 슬롯/템플릿 확장 또는 실제 FAQ 혼합 필요.`);
}

main();
