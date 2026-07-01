// 지식베이스(KB) 공용 헬퍼 — 성분사전·조합분석·근거랭킹 페이지에서 사용.
// 추천 점수 로직은 engine.js(캐노니컬). 여기선 조회·관계·근거 헬퍼만 제공.
import ingredientsData from '../data/ingredients.json';
import concernsData from '../data/concerns.json';
import interactions from '../data/interactions.json';
import evidenceData from '../data/evidence.json';
import medMap from '../data/med_dur_map.json';

export const ingredients = ingredientsData.ingredients;
export const concerns = concernsData.concerns;
export const meds = medMap.map || {};
export { interactions };

export const byId = Object.fromEntries(ingredients.map((i) => [i.id, i]));
export const concernById = Object.fromEntries(concerns.map((c) => [c.id, c]));
export const evById = Object.fromEntries((evidenceData.evidence || []).map((e) => [e.ingredient_id, e]));

export const STRENGTH = {
  established: ['확립된 근거', '#047857'],
  moderate: ['중등도 근거', '#0d9488'],
  limited: ['제한적 근거', '#d97706'],
  insufficient: ['근거 불충분', '#6b7280'],
};
export const DUR_LABEL = { continuous: '🟢 지속', monitor: '🟡 점검', cyclic: '🔴 주기' };

const STRENGTH_RANK = { established: 3, moderate: 2, limited: 1, insufficient: 0 };

// 두 성분의 시너지/길항 관계
export function relation(a, b) {
  const inPair = (e) => e.pair.includes(a) && e.pair.includes(b);
  const syn = interactions.synergy.find(inPair);
  if (syn) return { type: 'synergy', ...syn };
  const ant = interactions.antagonism.find(inPair);
  if (ant) return { type: 'antagonism', ...ant };
  return null;
}

// 성분×복용약 상호작용
export function drugCheck(id, medications) {
  const res = { action: 'ok', warnings: [], excludeReason: null };
  for (const di of interactions.drug_interactions) {
    if (!medications.includes(di.drug)) continue;
    if (!di.ingredients.includes(id)) continue;
    if (di.action === 'exclude') {
      res.action = 'exclude';
      res.excludeReason = di.message;
    } else if (di.action === 'warn' && res.action !== 'exclude') {
      res.action = 'warn';
      res.warnings.push(di.message);
    }
  }
  return res;
}

// 성분의 가장 강한 근거 benefit
export function topBenefit(id) {
  const e = evById[id];
  if (!e || !e.benefits?.length) return null;
  return [...e.benefits].sort(
    (a, b) => (STRENGTH_RANK[b.evidence_strength] ?? 0) - (STRENGTH_RANK[a.evidence_strength] ?? 0)
  )[0];
}

// 공식 권장량/상한 표시(없으면 '미설정'으로 정직 표기)
export function doseLine(id) {
  const d = evById[id]?.dosing;
  const real = (v) => (v && v !== '출처 미확인' ? v : null);
  if (!d) return null;
  const r = real(d.rda_or_ai);
  const u = real(d.ul);
  if (!r && !u) return '공식 권장량·상한 미설정(영양소 아닌 기능성 원료)';
  return `${r ? '권장 ' + r : ''}${r && u ? ' · ' : ''}${u ? '상한 ' + u : ''}`;
}

// 근거 기반 랭킹 점수 = 활용 고민 수×2 + 인정등급
export function rankScore(ing) {
  const cs = concerns.filter((c) => c.ingredients.includes(ing.id));
  return { cs, score: cs.length * 2 + (ing.evidence?.level || 0) };
}
