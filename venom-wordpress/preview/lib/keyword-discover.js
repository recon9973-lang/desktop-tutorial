'use strict';

// ============================================================
// keyword-discover — 실사용 키워드 발굴 코어(조합·분류·랭킹)
// ============================================================
// 진단기 '핵심 키워드' 카드용. 지역계층(data/regions-kr)·진료과 사전(data/dept-modifiers)을
// '붙여쓰기 조합'으로 결합해 시드를 만들고(buildSeeds), 네이버 검색광고 응답으로 돌아온
// 실제 검색어들을 티어로 분류(classify)·기회점수로 랭킹(rankTiers)한다.
//
// 이 모듈은 순수 함수만 담는다(네트워크 X) → node로 단독 테스트 가능.
// 실제 검색량 조회(searchad 배치)·자동완성 확장은 api/keyword-discover.js가 담당.
// ============================================================

let REGIONS, DEPTS;
try { REGIONS = require('../data/regions-kr.json').regions || []; } catch (e) { REGIONS = []; }
try { DEPTS = require('../data/dept-modifiers.json').depts || {}; } catch (e) { DEPTS = {}; }

// 공백 제거(네이버 hintKeywords는 공백 불허) + 소문자 비교용
function squash(s) { return String(s || '').replace(/\s+/g, ''); }
function norm(s) { return squash(s).toLowerCase(); }

// 진료과 입력값 → 사전 키 해석(별칭 매칭). 미매칭 시 null(=일반 모드).
function resolveDept(dept) {
  const d = squash(dept);
  if (!d) return null;
  if (DEPTS[d]) return Object.assign({ key: d }, DEPTS[d]);
  for (const key of Object.keys(DEPTS)) {
    const meta = DEPTS[key];
    if ((meta.aliases || []).some((a) => squash(a) === d)) return Object.assign({ key }, meta);
  }
  // 부분 포함(예: '비만클리닉' 입력 → '비만')
  for (const key of Object.keys(DEPTS)) {
    const meta = DEPTS[key];
    if ((meta.aliases || []).some((a) => d.indexOf(squash(a)) >= 0 || squash(a).indexOf(d) >= 0)) {
      return Object.assign({ key }, meta);
    }
  }
  return null;
}

// 지역 입력값 → 지역계층 해석. 데이터에 없으면 입력 자체를 대표지역으로(sub 없음).
// 입력이 '대구 북구'처럼 sub를 포함하면 그 sub를 앞으로 끌어올린다.
function resolveRegion(region) {
  const rin = squash(region);
  if (!rin) return null;
  for (const r of REGIONS) {
    const hitAlias = (r.aliases || []).find((a) => rin.indexOf(squash(a)) >= 0);
    if (hitAlias) {
      const sub = (r.sub || []).slice();
      // 입력에 명시된 sub는 최우선
      const named = sub.filter((s) => rin.indexOf(squash(s)) >= 0);
      const rest = sub.filter((s) => rin.indexOf(squash(s)) < 0);
      return { name: r.name, aliases: r.aliases || [r.name], sub: named.concat(rest), known: true };
    }
  }
  return { name: squash(region), aliases: [squash(region)], sub: [], known: false };
}

// ── 조합 시드 생성 ──
// 반환: { seeds:[{kw,tier}], ctx } — seeds는 네이버 hint로 보낼 후보(중복 제거).
// tier: representative | subregion | procedure | longtail(자동완성에서 채움)
// 검색광고가 관련어를 대량 확장해주므로 시드는 '대표 조합'만 절제해서 만든다(호출 절약).
function buildSeeds(region, dept, opts) {
  opts = opts || {};
  const maxSub = opts.maxSub || 4;
  const maxSym = opts.maxSym || 3;
  const maxTre = opts.maxTre || 3;

  const R = resolveRegion(region);
  const D = resolveDept(dept);
  const deptSuffix = D ? D.suffix : squash(dept);      // 미매칭 진료과도 접미어로 사용
  const seeds = [];
  const seen = new Set();
  function add(kw, tier) {
    const k = squash(kw);
    if (!k || seen.has(k)) return;
    seen.add(k); seeds.push({ kw: k, tier });
  }

  if (!R) return { seeds: [], ctx: { region: R, dept: D, deptSuffix } };
  const base = R.name;

  // 1) 대표: {지역}{과}
  if (deptSuffix) add(base + deptSuffix, 'representative');

  // 2) 세부지역: {지역}{sub}{과}. sub가 이미 지역명을 포함하면(예: 동대구역) 중복 방지 위해 {sub}{과}.
  (R.sub || []).slice(0, maxSub).forEach((s) => {
    if (!deptSuffix) return;
    const prefix = squash(s).indexOf(base) >= 0 ? s : base + s;
    add(prefix + deptSuffix, 'subregion');
  });

  // 3) 증상·시술: {지역}{증상}{과} · {지역}{시술}(단독)
  if (D) {
    (D.symptoms || []).slice(0, maxSym).forEach((s) => add(base + s + deptSuffix, 'procedure'));
    (D.treatments || []).slice(0, maxTre).forEach((t) => add(base + t, 'procedure'));
  }

  return { seeds, ctx: { region: R, dept: D, deptSuffix, base } };
}

// 조합 후보 전체(분류 상대성 판단용) — 지역·sub·증상·시술 토큰 집합.
function tokenSets(ctx) {
  const R = ctx.region, D = ctx.dept;
  const regionTokens = R ? [R.name].concat(R.aliases || []).map(squash) : [];
  const subTokens = R ? (R.sub || []).map(squash) : [];
  const modTokens = D ? [].concat(D.symptoms || [], D.treatments || []).map(squash) : [];
  return { regionTokens, subTokens, modTokens, suffix: squash(ctx.deptSuffix || '') };
}

// 반환된 실제 검색어 하나를 티어로 분류. 지역 무관·진료과 무관어는 null(제외).
// 우선순위: 증상·시술 > 세부지역 > 대표 > 롱테일.
function classify(keyword, ctx) {
  const kw = norm(keyword);
  if (!kw) return null;
  const { regionTokens, subTokens, modTokens, suffix } = tokenSets(ctx);

  const hasRegion = regionTokens.some((t) => t && kw.indexOf(t) >= 0);
  const hasSub = subTokens.some((t) => t && kw.indexOf(t) >= 0);
  // 지역 관련성: 대표지역명 또는 세부지역명 중 하나는 포함해야 로컬 키워드로 채택
  if (!hasRegion && !hasSub) return null;

  const hasMod = modTokens.some((t) => t && kw.indexOf(t) >= 0);
  const hasSuffix = suffix && kw.indexOf(suffix) >= 0;
  // 진료과 관련성: 과 접미어·증상/시술 중 하나는 포함(순수 지역명만은 제외)
  if (!hasSuffix && !hasMod) return null;

  if (hasMod) return 'procedure';
  if (hasSub) return 'subregion';
  if (hasSuffix) return 'representative';
  return 'longtail';
}

// 경쟁도 가중(기회점수 = 검색량 ÷ 경쟁가중). 문자열('높음')·숫자 인덱스 모두 허용.
function compWeight(compIdx) {
  if (typeof compIdx === 'number') return compIdx <= 33 ? 1 : compIdx <= 66 ? 2 : 4;
  const s = String(compIdx || '');
  if (/낮음|low/i.test(s)) return 1;
  if (/중간|mid/i.test(s)) return 2;
  if (/높음|high/i.test(s)) return 4;
  return 2; // 미상 → 중간
}

function opportunity(volume, compIdx) {
  const v = Number(volume) || 0;
  return Math.round((v / compWeight(compIdx)) * 10) / 10;
}

// rows: [{ keyword, volume, compIdx, tier }] → 티어별 그룹·기회점수 랭킹·상위 N.
// perTier: { representative, subregion, procedure, longtail }
function rankTiers(rows, perTier) {
  const caps = Object.assign({ representative: 3, subregion: 5, procedure: 6, longtail: 5 }, perTier || {});
  const order = ['representative', 'subregion', 'procedure', 'longtail'];
  const byTier = { representative: [], subregion: [], procedure: [], longtail: [] };
  const seen = new Set();
  rows.forEach((r) => {
    const k = norm(r.keyword);
    if (!k || seen.has(k) || !byTier[r.tier]) return;
    seen.add(k);
    byTier[r.tier].push({
      keyword: r.keyword,
      volume: Number(r.volume) || 0,
      compIdx: r.compIdx != null ? r.compIdx : null,
      score: opportunity(r.volume, r.compIdx),
    });
  });
  const tiers = {};
  order.forEach((t) => {
    tiers[t] = byTier[t]
      .filter((x) => x.volume > 0)
      .sort((a, b) => b.score - a.score || b.volume - a.volume)
      .slice(0, caps[t]);
  });
  return tiers;
}

module.exports = {
  squash, norm, resolveDept, resolveRegion,
  buildSeeds, classify, compWeight, opportunity, rankTiers, tokenSets,
  _data: { REGIONS: () => REGIONS, DEPTS: () => DEPTS },
};
