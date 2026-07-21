'use strict';

// ============================================================
// GET /api/keyword-discover?region=대구&dept=한의원[&limit=N]
// 실사용 키워드 발굴기 — 조합 → 네이버 검색광고(검색량·경쟁) → 티어 랭킹.
// 반환: { ok, region, dept, tiers:{ representative, subregion, procedure, longtail },
//         flat:[...], configured, source }
// 실패는 graceful: 미설정/오류 시 조합 시드만이라도 tiers에 담아(검색량 null) 리포트 유지.
// ============================================================

const sa = require('../lib/naver-searchad');            // 검색광고 키워드도구 단일 소스
const kd = require('../lib/keyword-discover');           // 조합·분류·랭킹 코어
let research = null;
try { research = require('../lib/keyword-research'); } catch (e) { research = null; } // 자동완성 확장(선택)

// 검색광고 응답 1행 → { keyword, volume, compIdx }
function rowFromNaver(k) {
  const vol = sa.toNum(k.monthlyPcQcCnt != null ? k.monthlyPcQcCnt : k.monthlyPcQcnt)
    + sa.toNum(k.monthlyMobileQcCnt != null ? k.monthlyMobileQcCnt : k.monthlyMobileQcnt);
  return { keyword: String(k.relKeyword || '').trim(), volume: vol, compIdx: k.compIdx != null ? k.compIdx : null };
}

// hint 배열을 5개씩 잘라 배치 조회(제한 동시성). 반환: relKeyword→row 맵.
async function fetchVolumes(hints, concurrency) {
  const batches = [];
  for (let i = 0; i < hints.length; i += 5) batches.push(hints.slice(i, i + 5));
  const map = new Map();
  let cursor = 0;
  async function worker() {
    while (cursor < batches.length) {
      const b = batches[cursor++];
      const r = await sa.fetchKeywordTool(b, { timeout: 8000 });
      if (r && r.keywordList) {
        r.keywordList.forEach((k) => {
          const row = rowFromNaver(k);
          const key = kd.norm(row.keyword);
          if (key && (!map.has(key) || map.get(key).volume < row.volume)) map.set(key, row);
        });
      }
    }
  }
  const lanes = Math.min(concurrency || 3, batches.length || 1);
  await Promise.all(Array.from({ length: lanes }, worker));
  return map;
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const region = (req.query.region || '').toString();
  const dept = (req.query.dept || '').toString();
  if (!region || !dept) { res.status(400).json({ error: 'region·dept 파라미터가 필요합니다.' }); return; }

  const built = kd.buildSeeds(region, dept);
  const ctx = built.ctx;
  if (!built.seeds.length) { res.status(400).json({ error: '조합 시드를 만들 수 없습니다.' }); return; }

  // hint 집합: 조합 시드 + (자동완성 확장, best-effort)
  const hintSet = [];
  const hintSeen = new Set();
  const pushHint = (kw) => { const k = kd.squash(kw); if (k && !hintSeen.has(k)) { hintSeen.add(k); hintSet.push(k); } };
  built.seeds.forEach((s) => pushHint(s.kw));

  // 자동완성 확장(있으면): 대표 조합 기준 연관어 중 지역 포함분만 hint에 추가(롱테일 시드).
  if (research && ctx.base && ctx.deptSuffix) {
    try {
      const rk = await research.researchKeywords(ctx.base + ctx.deptSuffix, { limitRelated: 12, limitQuestions: 0 });
      const regionTok = kd.norm(ctx.base);
      (rk.related || []).forEach((term) => {
        if (kd.norm(term).indexOf(regionTok) >= 0) pushHint(term);
      });
    } catch (e) { /* 자동완성 실패는 무시 */ }
  }

  // 호출 상한(서버리스 시간 보호): hint 최대 20개(=배치 4개).
  const hints = hintSet.slice(0, 20);

  let volMap = new Map();
  let configured = true;
  try {
    volMap = await fetchVolumes(hints, 3);
  } catch (e) { volMap = new Map(); }
  if (!sa.isConfigured()) configured = false;

  // 반환된 실제 검색어 전체를 분류 → 랭킹.
  const rows = [];
  volMap.forEach((row) => {
    const tier = kd.classify(row.keyword, ctx);
    if (tier) rows.push(Object.assign({ tier }, row));
  });

  // 검색광고 미설정/무응답 시: 조합 시드라도 검색량 null로 노출(리포트 유지).
  if (!rows.length) {
    const fallback = built.seeds.map((s) => ({ keyword: s.kw, volume: 0, compIdx: null, tier: s.tier }));
    res.status(200).json({
      ok: false, region: ctx.base || kd.squash(region), dept: (ctx.dept && ctx.dept.key) || kd.squash(dept),
      configured, source: 'seeds-only',
      tiers: { representative: [], subregion: [], procedure: [], longtail: [] },
      seeds: fallback.slice(0, 12),
      note: configured ? '검색량 데이터를 가져오지 못했습니다.' : '네이버 검색광고 API가 설정되지 않았습니다.',
    });
    return;
  }

  const tiers = kd.rankTiers(rows);
  const flat = [].concat(tiers.representative, tiers.subregion, tiers.procedure, tiers.longtail)
    .sort((a, b) => b.score - a.score);
  const limit = Math.min(parseInt(req.query.limit, 10) || 20, 40);

  res.status(200).json({
    ok: true,
    region: ctx.base || kd.squash(region),
    dept: (ctx.dept && ctx.dept.key) || kd.squash(dept),
    configured, source: 'searchad',
    tiers,
    flat: flat.slice(0, limit),
  });
};
