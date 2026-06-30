'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GrowthOps · M2 내부링크 최적화 엔진
// ─────────────────────────────────────────────────────────────────────────
// 발행 글(blog-posts.json) 사이의 관련도를 계산해 "자연스러운 내부링크"를
// 제안한다. 화이트햇 원칙:
//   1) 운영자 승인형 — 본문 자동삽입은 마커로 idempotent하게, 언제든 제거 가능
//   2) 앵커텍스트 다양화 — 동일 정확매치 앵커 반복(과최적화) 방지
//   3) 고아 글(인바운드 0) 탐지 — 권위가 흐르지 않는 글을 찾아냄
// 외부 의존성 없음(순수 JS). Vercel 서버리스 + 로컬 CLI 양쪽에서 동작.
//
// 관련도 점수 = 키워드 코사인 유사도(집합)
//             + 같은 진료과목(cat) 가중
//             + 같은 지역(region) 가중
//             + 같은 클러스터(clusters.json) 가중
// ─────────────────────────────────────────────────────────────────────────

// 한국어/영문 공통: 키워드·제목을 토큰 집합으로. 1글자·불용어는 버린다.
const STOP = new Set([
  '베놈', '병원', '마케팅', '전략', '가지', '방법', '가이드', '소개', '위한', '대한',
  'the', 'a', 'an', 'of', 'for', 'and', 'to', 'in', 'on', 'seo', 'top',
]);

function norm(s) {
  return String(s == null ? '' : s).toLowerCase().trim();
}

// 콤마 키워드 + 제목 단어를 합쳐 토큰 집합 생성
function tokensOf(post) {
  const out = new Set();
  const push = (raw) => {
    const t = norm(raw).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
    if (!t) return;
    for (const w of t.split(/\s+/)) {
      if (w.length < 2) continue;       // 1글자 토큰 제거
      if (STOP.has(w)) continue;        // 불용어 제거
      out.add(w);
    }
  };
  // keywords: "대전, SEO 마케팅, C-Rank" 형태(콤마 구분)
  for (const kw of norm(post && post.keywords).split(',')) push(kw);
  // 제목/SEO제목도 토큰 보강(가중 낮게 — 집합이라 자동)
  push(post && post.title);
  push(post && post.seoTitle);
  return out;
}

function jaccardCosine(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  const [small, big] = a.size < b.size ? [a, b] : [b, a];
  for (const x of small) if (big.has(x)) inter++;
  // 집합 코사인: |A∩B| / sqrt(|A|*|B|)
  return inter / Math.sqrt(a.size * b.size);
}

// post.id → 소속 클러스터 id 매핑 (clusters.json이 있을 때)
function buildClusterIndex(clusters) {
  const idx = new Map();
  const list = (clusters && clusters.clusters) || [];
  for (const c of list) {
    for (const st of c.subtopics || []) {
      if (st.postId) idx.set(String(st.postId), c.id);
    }
  }
  return idx;
}

const WEIGHTS = { keyword: 1.0, cat: 0.15, region: 0.1, cluster: 0.25 };

function scorePair(a, b, ta, tb, clusterIdx) {
  let score = WEIGHTS.keyword * jaccardCosine(ta, tb);
  if (a.cat && b.cat && norm(a.cat) === norm(b.cat)) score += WEIGHTS.cat;
  if (a.region && b.region && norm(a.region) === norm(b.region)) score += WEIGHTS.region;
  if (clusterIdx) {
    const ca = clusterIdx.get(String(a.id));
    const cb = clusterIdx.get(String(b.id));
    if (ca && cb && ca === cb) score += WEIGHTS.cluster;
  }
  return score;
}

// 발행 대상만 (status 미지정이면 통과 — 데이터마다 다름)
function isPublished(p) {
  if (!p) return false;
  if (p.publishable === false) return false;
  if (p.status && !/publish|발행|live|done/i.test(p.status)) {
    // status가 draft/임시저장 류면 제외
    if (/draft|임시|hidden|trash|삭제/i.test(p.status)) return false;
  }
  return true;
}

// 본문 html 안에 b를 가리키는 링크가 이미 있는지(슬러그/아이디로 추정)
function hasExistingLink(htmlLower, target) {
  if (!htmlLower) return false;
  const slug = norm(target.slug);
  const id = norm(target.id);
  if (slug && htmlLower.includes(encodeURIComponent(slug).toLowerCase())) return true;
  if (slug && htmlLower.includes(slug)) return true;
  if (id && htmlLower.includes(id)) return true;
  return false;
}

// 앵커 후보(다양화): 제목 / SEO제목 / 대표 키워드구
function anchorCandidates(target) {
  const cands = [];
  if (target.title) cands.push(String(target.title).trim());
  if (target.seoTitle && target.seoTitle !== target.title) cands.push(String(target.seoTitle).trim());
  const firstKw = norm(target.keywords).split(',').map((s) => s.trim()).filter(Boolean)[0];
  if (firstKw) cands.push(firstKw);
  return cands.length ? cands : [String(target.title || target.slug || target.id)];
}

/**
 * 글마다 추천 내부링크 산출.
 * @param {Array} posts blog-posts.json 배열
 * @param {Object} [opts]
 * @param {number} [opts.perPost=4] 글당 추천 링크 수
 * @param {number} [opts.minScore=0.12] 최소 관련도 임계
 * @param {Object} [opts.clusters] clusters.json (선택)
 * @param {(p)=>string} [opts.urlFor] 글→URL 빌더(기본 ./?p=id)
 * @returns {{ suggestions: Object[], orphans: Object[], stats: Object }}
 */
function suggestLinks(posts, opts = {}) {
  const perPost = opts.perPost || 4;
  const minScore = opts.minScore == null ? 0.12 : opts.minScore;
  const urlFor = opts.urlFor || ((p) => `./?p=${encodeURIComponent(p.id)}`);
  const clusterIdx = opts.clusters ? buildClusterIndex(opts.clusters) : null;

  const live = (posts || []).filter(isPublished);
  const toks = new Map(live.map((p) => [p.id, tokensOf(p)]));

  const inbound = new Map(live.map((p) => [p.id, 0])); // 추천 기준 인바운드 카운트
  const suggestions = [];

  for (const a of live) {
    const ta = toks.get(a.id);
    const htmlLower = norm(a.html);
    const usedAnchors = new Set(); // 같은 출처에서 동일 앵커 반복 방지(과최적화 방지)

    const ranked = [];
    for (const b of live) {
      if (a.id === b.id) continue;
      const s = scorePair(a, b, ta, toks.get(b.id), clusterIdx);
      if (s >= minScore) ranked.push({ b, s });
    }
    ranked.sort((x, y) => y.s - x.s);

    const links = [];
    for (let i = 0; i < ranked.length && links.length < perPost; i++) {
      const { b, s } = ranked[i];
      const already = hasExistingLink(htmlLower, b);
      // 앵커 다양화: 후보 중 아직 이 출처에서 안 쓴 것을 순서대로 선택
      const cands = anchorCandidates(b);
      let anchor = cands.find((c) => !usedAnchors.has(norm(c))) || cands[0];
      usedAnchors.add(norm(anchor));
      links.push({
        targetId: b.id,
        targetSlug: b.slug,
        url: urlFor(b),
        anchor,
        score: Number(s.toFixed(4)),
        alreadyLinked: already,
      });
      if (!already) inbound.set(b.id, (inbound.get(b.id) || 0) + 1);
    }
    suggestions.push({ id: a.id, slug: a.slug, title: a.title, cat: a.cat, links });
  }

  // 고아 글: 추천/기존 통틀어 인바운드 0
  const orphans = live
    .filter((p) => (inbound.get(p.id) || 0) === 0)
    .map((p) => ({ id: p.id, slug: p.slug, title: p.title, cat: p.cat }));

  const totalLinks = suggestions.reduce((n, s) => n + s.links.length, 0);
  const stats = {
    posts: live.length,
    totalSuggestedLinks: totalLinks,
    avgLinksPerPost: live.length ? Number((totalLinks / live.length).toFixed(2)) : 0,
    orphanCount: orphans.length,
    orphanRate: live.length ? Number((orphans.length / live.length).toFixed(3)) : 0,
  };
  return { suggestions, orphans, stats };
}

// ── 본문 삽입(운영자 승인형, idempotent) ────────────────────────────────
const REL_START = '<!-- growthops:related:start -->';
const REL_END = '<!-- growthops:related:end -->';
const REL_BLOCK_RE = new RegExp(
  REL_START.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[\\s\\S]*?' + REL_END.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
  'g'
);

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// "관련 글" HTML 블록 생성
function buildRelatedBlock(links) {
  if (!links || !links.length) return '';
  const items = links
    .map(
      (l) =>
        `    <li><a href="${escapeHtml(l.url)}">${escapeHtml(l.anchor)}</a></li>`
    )
    .join('\n');
  return (
    `${REL_START}\n` +
    `<aside class="related-posts" style="margin:40px 0 8px;padding:20px 22px;background:var(--soft,#f6f9fc);border:1px solid var(--border,#e3e8ee);border-radius:var(--r12,12px)">\n` +
    `  <h3 style="margin:0 0 12px;font-size:1.05rem;color:var(--ink,#0d253d)">함께 보면 좋은 글</h3>\n` +
    `  <ul style="margin:0;padding-left:18px;line-height:1.9">\n${items}\n  </ul>\n` +
    `</aside>\n${REL_END}`
  );
}

/**
 * 본문 html에 관련글 블록을 idempotent하게 주입(기존 블록 교체).
 * 블록을 빼려면 links=[] 또는 removeRelatedBlock 사용.
 */
function injectRelatedBlock(html, links) {
  const base = removeRelatedBlock(html || '');
  const block = buildRelatedBlock(links);
  if (!block) return base;
  return base.replace(/\s*$/, '') + '\n' + block + '\n';
}

function removeRelatedBlock(html) {
  return String(html || '').replace(REL_BLOCK_RE, '').replace(/\n{3,}/g, '\n\n');
}

module.exports = {
  tokensOf,
  suggestLinks,
  buildRelatedBlock,
  injectRelatedBlock,
  removeRelatedBlock,
  // 내부 함수도 테스트용으로 노출
  _internal: { jaccardCosine, scorePair, anchorCandidates, isPublished, buildClusterIndex },
};
