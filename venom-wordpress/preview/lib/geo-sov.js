'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · Share of Voice(경쟁사 대비 AI 노출 점유율)
//   설계: docs/plans/geo-ops-os-design.md §4.1, 리서치 §2.3(상대지표 우선)
//   원칙: 절대 인용%가 아니라 "자사 vs 경쟁사" 상대 점유율. 실측 answer 텍스트에서
//         자사 core / 경쟁사명 언급을 세어 SOV = self / (self + 경쟁사합) 로 산출.
//   모두 순수 함수 → 오프라인 단위 테스트. (측정은 워크플로가 cell 단위로 수집)
// ─────────────────────────────────────────────────────────────────────────

function norm(s) { return String(s || '').replace(/\s+/g, '').toLowerCase(); }

// 텍스트에 등장하는 이름 목록 반환(정규화 부분일치)
function mentions(text, names) {
  const t = norm(text);
  if (!t) return [];
  return (names || []).filter((n) => n && t.includes(norm(n)));
}

// cells: [{ selfHit:bool, compHits:[경쟁사명...] }] → SOV 집계
function buildSov(cells) {
  let selfMentions = 0;
  const compMentions = {};
  (cells || []).forEach((c) => {
    if (c && c.selfHit) selfMentions++;
    (c && c.compHits || []).forEach((name) => { compMentions[name] = (compMentions[name] || 0) + 1; });
  });
  const totalComp = Object.values(compMentions).reduce((a, b) => a + b, 0);
  const denom = selfMentions + totalComp;
  return {
    selfMentions,
    compMentions,
    totalComp,
    sovPct: denom ? Math.round(selfMentions / denom * 100) : null, // 아무도 언급 없으면 null(측정불가)
  };
}

module.exports = { norm, mentions, buildSov };
