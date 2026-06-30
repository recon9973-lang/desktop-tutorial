// 당신의영양제 — 추천 엔진 (웹 ESM 포트)
// ⚠️ 캐노니컬 로직: ../../../engine/recommend.js (Node/CommonJS).
//    Vercel Root=apps/web 이라 레포 루트 밖을 번들할 수 없어, 동일 로직을
//    ESM으로 옮기고 데이터(apps/web/data/*.json)를 직접 import 한다.
//    로직을 고칠 땐 두 파일을 함께 맞춰야 함(추천 결과 동일성 유지).
//
// score = evidence_weight * concern_fit * safety_factor - overlap_penalty + synergy_bonus
// 후기/별점(review)은 점수에 미반영 — 별도 레이어.

import ingredientsData from '../data/ingredients.json';
import concernsData from '../data/concerns.json';
import interactions from '../data/interactions.json';
import rules from '../data/recommendation_rules.json';

const ingredients = ingredientsData.ingredients;
const concerns = concernsData.concerns;

const byId = Object.fromEntries(ingredients.map((i) => [i.id, i]));
const concernById = Object.fromEntries(concerns.map((c) => [c.id, c]));

// 알레르기 키워드 매핑 (user.allergies 코드 → cautions 내 한글 키워드)
const ALLERGY_KEYWORDS = { milk: ['우유'], soy: ['대두', '콩'], peanut: ['땅콩'] };

function evidenceWeight(level) {
  return rules.scoring.evidence_weight[String(level)] ?? 0.4;
}

function concernFit(ingredientId, userConcerns) {
  const w = rules.scoring.concern_fit.rank_weights;
  let best = 0;
  let matchedConcerns = 0;
  for (const cid of userConcerns) {
    const c = concernById[cid];
    if (!c) continue;
    const rank = c.ingredients.indexOf(ingredientId);
    if (rank === -1) continue;
    matchedConcerns++;
    best = Math.max(best, w[rank] ?? w[w.length - 1]);
  }
  return { fit: best, matchedConcerns };
}

// 의약품 상호작용 → exclude / warn
function drugCheck(ingredientId, medications) {
  const result = { action: 'ok', warnings: [], warningSources: [], excludeReason: null };
  for (const di of interactions.drug_interactions) {
    if (!medications.includes(di.drug)) continue;
    if (!di.ingredients.includes(ingredientId)) continue;
    if (di.action === 'exclude') {
      result.action = 'exclude';
      result.excludeReason = di.message;
    } else if (di.action === 'warn' && result.action !== 'exclude') {
      result.action = 'warn';
      result.warnings.push(di.message);
      result.warningSources.push({ text: di.message, source: di.source || null });
    }
  }
  return result;
}

function allergyCheck(ing, allergies) {
  for (const a of allergies) {
    const kws = ALLERGY_KEYWORDS[a] || [];
    const text = (ing.cautions || []).join(' ');
    if (kws.some((k) => text.includes(k))) return true;
  }
  return false;
}

// 두 성분이 시너지/길항 관계인지
function relation(idA, idB) {
  const inPair = (entry) => entry.pair.includes(idA) && entry.pair.includes(idB);
  const syn = interactions.synergy.find(inPair);
  if (syn) return { type: 'synergy', ...syn };
  const ant = interactions.antagonism.find(inPair);
  if (ant) return { type: 'antagonism', ...ant };
  return null;
}

export function recommend(user) {
  const { concerns: userConcerns = [], medications = [], allergies = [] } = user;
  const recommended = [];
  const notRecommended = [];

  // 후보 = 선택한 고민들에 매핑된 성분(중복 제거)
  const candidateIds = [
    ...new Set(userConcerns.flatMap((cid) => concernById[cid]?.ingredients || [])),
  ];

  for (const id of candidateIds) {
    const ing = byId[id];
    if (!ing) continue;

    // 알레르기 제외
    if (allergyCheck(ing, allergies)) {
      notRecommended.push({ ingredient_id: id, name: ing.name_ko, reason: '알레르기 성분 포함' });
      continue;
    }

    // 의약품 제외/경고
    const dc = drugCheck(id, medications);
    if (dc.action === 'exclude') {
      notRecommended.push({ ingredient_id: id, name: ing.name_ko, reason: dc.excludeReason });
      continue;
    }

    const ew = evidenceWeight(ing.evidence.level);
    const { fit, matchedConcerns } = concernFit(id, userConcerns);
    const safety = dc.action === 'warn'
      ? rules.scoring.safety_factor.drug_warn
      : rules.scoring.safety_factor.default;

    // 여러 고민에서 중복 추천 시 통합 패널티 (1회 초과분만)
    const overlap = matchedConcerns > 1
      ? rules.scoring.overlap_penalty.value * (matchedConcerns - 1)
      : 0;

    const score = ew * fit * safety - overlap;

    recommended.push({
      ingredient_id: id,
      name: ing.name_ko,
      evidence_level: ing.evidence.level,
      evidence_sources: ing.evidence.sources || [],
      duration_type: ing.duration_type,
      duration_note: ing.duration_note,
      functions: ing.functions,
      daily_dose: ing.daily_dose,
      cautions: ing.cautions || [],
      warnings: dc.warnings,
      warning_sources: dc.warningSources,
      _baseScore: score,
    });
  }

  // 시너지 보너스: 최종 후보쌍이 시너지면 가점
  const bonusVal = rules.scoring.synergy_bonus.value;
  for (let i = 0; i < recommended.length; i++) {
    for (let j = i + 1; j < recommended.length; j++) {
      const rel = relation(recommended[i].ingredient_id, recommended[j].ingredient_id);
      if (rel?.type === 'synergy') {
        recommended[i]._baseScore += bonusVal;
        recommended[j]._baseScore += bonusVal;
      }
    }
  }

  recommended.forEach((r) => (r.score = Math.round(r._baseScore * 100) / 100));
  recommended.sort((a, b) => b.score - a.score);
  recommended.forEach((r) => delete r._baseScore);

  return {
    recommended,
    not_recommended: notRecommended,
    schedule: buildSchedule(recommended),
    interactions_note: buildInteractionNotes(recommended),
  };
}

// 길항(시간차) 기반 아침/저녁 분리 + 시너지는 같은 시간
function buildSchedule(recommended) {
  const morning = [];
  const evening = [];
  for (const r of recommended) {
    // 이미 아침에 길항 성분이 있으면 저녁으로
    const conflictMorning = morning.some(
      (m) => relation(m, r.ingredient_id)?.type === 'antagonism'
    );
    (conflictMorning ? evening : morning).push(r.ingredient_id);
  }
  const name = (id) => byId[id]?.name_ko || id;
  return { morning: morning.map(name), evening: evening.map(name) };
}

function buildInteractionNotes(recommended) {
  const notes = [];
  const ids = recommended.map((r) => r.ingredient_id);
  for (let i = 0; i < ids.length; i++) {
    for (let j = i + 1; j < ids.length; j++) {
      const rel = relation(ids[i], ids[j]);
      if (!rel) continue;
      const a = byId[ids[i]].name_ko, b = byId[ids[j]].name_ko;
      if (rel.type === 'synergy') notes.push(`🔗 ${a} + ${b}: ${rel.effect} (함께 복용)`);
      else notes.push(`⚠️ ${a} ↔ ${b}: ${rel.problem} (${rel.timing})`);
    }
  }
  return notes;
}
