'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GrowthOps · M1 토픽 클러스터 엔진 (순수 로직)
// ─────────────────────────────────────────────────────────────────────────
// 검색 권위는 무작위 키워드 나열이 아니라 "필러(Pillar) ↔ 클러스터(Cluster)"
// 구조에서 복리로 쌓인다. 이 모듈은:
//   - 키워드 리서치 결과로 1개 필러 + N개 하위주제(subtopic) 클러스터를 구성
//   - 발행 글을 하위주제 빈칸에 매칭(고아 방지)
//   - 아직 안 채워진 "다음 빈칸"을 찾아 cron이 우선 발행하도록 한다
// 네트워크/IO 없음 — 리서치(researchKeywords)·발행(generatePost)은 호출측에서 주입.
// 영속화는 content/clusters.json (github-store).
// ─────────────────────────────────────────────────────────────────────────

function norm(s) { return String(s == null ? '' : s).toLowerCase().trim(); }

function slugId(category, region, pillar) {
  const base = [category, region, pillar].filter(Boolean).join('-')
    .toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 48);
  return 'cl_' + (base || 'cluster');
}

// 문자열 → 토큰 집합(1글자·중복 제거)
function toks(s) {
  const out = new Set();
  for (const w of norm(s).replace(/[^\p{L}\p{N}]+/gu, ' ').split(/\s+/)) {
    if (w.length >= 2) out.add(w);
  }
  return out;
}

function overlap(aStr, bStr) {
  const a = toks(aStr), b = toks(bStr);
  if (!a.size || !b.size) return 0;
  let inter = 0; for (const x of a) if (b.has(x)) inter++;
  return inter / Math.sqrt(a.size * b.size);
}

/**
 * 클러스터 1개 구성.
 * @param {Object} o
 * @param {string} o.category 진료과목(cat 키)
 * @param {string} [o.region] 지역
 * @param {string} o.pillar 필러 주제(대표 키워드)
 * @param {string[]} [o.related] 연관 키워드(하위주제 후보)
 * @param {string[]} [o.questions] 질문형 키워드(하위주제 후보)
 * @param {number} [o.size=6] 하위주제 개수
 * @param {string} [o.at] 생성 시각(ISO) — Date.now 회피용 주입
 */
function buildCluster(o) {
  const { category, region = '', pillar, related = [], questions = [], size = 6, at } = o || {};
  if (!category) throw new Error('category 필수');
  if (!pillar) throw new Error('pillar 필수');
  // 연관 + 질문을 합쳐 중복 제거 후 size개로 컷
  const seen = new Set([norm(pillar)]);
  const subs = [];
  for (const kw of [].concat(related, questions)) {
    const k = norm(kw);
    if (!k || seen.has(k)) continue;
    seen.add(k);
    subs.push({ kw: String(kw).trim(), postId: null, status: 'open' });
    if (subs.length >= size) break;
  }
  return {
    id: slugId(category, region, pillar),
    pillar: String(pillar).trim(),
    category,
    region,
    createdAt: at || new Date().toISOString(),
    subtopics: subs,
  };
}

/** clustersObj에 클러스터 upsert(동일 id 교체). 새 obj 반환(비파괴). */
function upsertCluster(clustersObj, cluster) {
  const list = (clustersObj && Array.isArray(clustersObj.clusters)) ? clustersObj.clusters.slice() : [];
  const i = list.findIndex((c) => c.id === cluster.id);
  if (i >= 0) {
    // 기존 subtopic의 채움 상태는 보존하면서 새 하위주제 병합
    const prev = list[i];
    const byKw = new Map(prev.subtopics.map((s) => [norm(s.kw), s]));
    cluster.subtopics = cluster.subtopics.map((s) => byKw.get(norm(s.kw)) || s);
    list[i] = Object.assign({}, prev, cluster);
  } else {
    list.unshift(cluster);
  }
  return { clusters: list };
}

/**
 * 발행 글들을 하위주제 빈칸에 매칭해 채운다(고아 방지).
 * 이미 채워진(postId 있는) 칸은 글이 살아있으면 유지, 삭제됐으면 비운다.
 * @returns {{ clusters }} 새 obj
 */
function mergePostsIntoClusters(clustersObj, posts, opts = {}) {
  const minScore = opts.minScore == null ? 0.34 : opts.minScore;
  const live = (posts || []).filter((p) => p && p.id);
  const liveIds = new Set(live.map((p) => String(p.id)));
  const usedPostIds = new Set();
  const clusters = ((clustersObj && clustersObj.clusters) || []).map((c) => ({
    ...c,
    subtopics: c.subtopics.map((s) => ({ ...s })),
  }));

  // 1) 기존 채움 검증(삭제된 글이면 비움)
  for (const c of clusters) {
    for (const s of c.subtopics) {
      if (s.postId && !liveIds.has(String(s.postId))) { s.postId = null; s.status = 'open'; }
      else if (s.postId) usedPostIds.add(String(s.postId));
    }
  }
  // 2) 빈칸을 가장 잘 맞는(미사용) 글로 채움
  for (const c of clusters) {
    for (const s of c.subtopics) {
      if (s.postId) continue;
      let best = null, bestScore = minScore;
      for (const p of live) {
        if (usedPostIds.has(String(p.id))) continue;
        if (p.cat && c.category && norm(p.cat) !== norm(c.category)) continue; // 같은 과목만
        const score = overlap(s.kw, (p.title || '') + ' ' + (p.keywords || ''));
        if (score >= bestScore) { best = p; bestScore = score; }
      }
      if (best) { s.postId = best.id; s.status = 'filled'; usedPostIds.add(String(best.id)); }
    }
  }
  return { clusters };
}

/** 아직 안 채워진 첫 빈칸 → cron이 우선 발행. 없으면 null. */
function nextGap(clustersObj) {
  for (const c of (clustersObj && clustersObj.clusters) || []) {
    const s = c.subtopics.find((x) => !x.postId && x.status !== 'skip');
    if (s) return { clusterId: c.id, category: c.category, region: c.region || '', pillar: c.pillar, kw: s.kw };
  }
  return null;
}

/** 특정 하위주제(kw)를 발행 글 id로 채움(cron 발행 직후 호출). 새 obj 반환. */
function fillSubtopic(clustersObj, clusterId, kw, postId) {
  const clusters = ((clustersObj && clustersObj.clusters) || []).map((c) => {
    if (c.id !== clusterId) return c;
    return {
      ...c,
      subtopics: c.subtopics.map((s) =>
        norm(s.kw) === norm(kw) ? { ...s, postId, status: 'filled' } : s),
    };
  });
  return { clusters };
}

/** 클러스터별 완성도 요약. */
function summary(clustersObj) {
  const clusters = (clustersObj && clustersObj.clusters) || [];
  let totalSub = 0, filled = 0;
  const perCluster = clusters.map((c) => {
    const t = c.subtopics.length;
    const f = c.subtopics.filter((s) => s.postId).length;
    totalSub += t; filled += f;
    return { id: c.id, pillar: c.pillar, category: c.category, region: c.region || '', total: t, filled: f };
  });
  return {
    clusters: clusters.length,
    totalSubtopics: totalSub,
    filled,
    completion: totalSub ? Number((filled / totalSub).toFixed(3)) : 0,
    perCluster,
  };
}

module.exports = {
  buildCluster, upsertCluster, mergePostsIntoClusters, nextGap, fillSubtopic, summary,
  slugId, _internal: { overlap, toks },
};
