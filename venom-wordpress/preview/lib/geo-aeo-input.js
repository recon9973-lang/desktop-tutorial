'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · AEO 실측 입력 컴파일러
//   설계: docs/plans/geo-ops-os-design.md §P1-3 (실측 일반화)
//   목적: 거래처 멀티테넌트(geo/clients.json active + geo/prompt-sets.json)를
//         기존 AI Exposure 워크플로가 소비하는 { businesses:[{key,name,cores,questions}] }
//         형태로 변환한다. 이렇게 하면 검증된 측정 로직을 건드리지 않고 N거래처로 확장.
//   폴백: 신규 소스가 비면 기존 ai-expose-input.json 을 그대로 사용(무중단 이관).
//   buildBusinesses 는 순수 함수 → 오프라인 단위 테스트 대상.
// ─────────────────────────────────────────────────────────────────────────

// clients(active) + prompt-sets → businesses[]  (질문 없는 거래처는 제외)
function buildBusinesses(clients, sets) {
  const setByClient = {};
  (sets || []).forEach((s) => { if (s && s.clientId) setByClient[s.clientId] = s; });
  return (clients || [])
    .filter((c) => c && c.id && c.active !== false)
    .map((c) => {
      const set = setByClient[c.id];
      const questions = set && Array.isArray(set.questions)
        ? set.questions.map((q) => (typeof q === 'string' ? q : (q && q.text))).filter(Boolean)
        : [];
      const cores = Array.isArray(c.coreKeywords) && c.coreKeywords.length ? c.coreKeywords : [c.name];
      return { key: c.id, name: c.name, cores, questions };
    })
    .filter((b) => b.questions.length > 0);
}

// fs 주입으로 파일 로드(테스트 용이). 신규 소스 우선, 비면 fallback.
function loadInput(fs, opts) {
  opts = opts || {};
  const clientsPath = opts.clientsPath || 'venom-wordpress/preview/content/geo/clients.json';
  const setsPath = opts.setsPath || 'venom-wordpress/preview/content/geo/prompt-sets.json';
  const fallbackPath = opts.fallbackPath || 'venom-wordpress/preview/content/ai-expose-input.json';

  let clients = [], sets = [];
  try { clients = JSON.parse(fs.readFileSync(clientsPath, 'utf8')).clients || []; } catch { clients = []; }
  try { sets = JSON.parse(fs.readFileSync(setsPath, 'utf8')).sets || []; } catch { sets = []; }

  let businesses = buildBusinesses(clients, sets);
  let source = 'geo';
  if (!businesses.length && fallbackPath) {
    try { businesses = JSON.parse(fs.readFileSync(fallbackPath, 'utf8')).businesses || []; source = 'fallback'; } catch { businesses = []; }
  }
  return { businesses, source };
}

module.exports = { buildBusinesses, loadInput };
