// GET /api/safety?ingredient_id=omega3  (또는 &q=term)
// openFDA CAERS(식이보충제 이상사례) — 제품명 기준 보고 건수 + 상위 증상.
//  ⚠️ 인과관계가 아닌 '보고' 데이터(참고용). 키 불필요. 배포환경에서 실데이터, 샌드박스/오류는 none.
import ingredientsData from '../../../data/ingredients.json';

export const runtime = 'nodejs';

const byId = Object.fromEntries(ingredientsData.ingredients.map((i) => [i.id, i]));
const TERM = {
  vitamin_d: 'vitamin d', vitamin_c: 'vitamin c', vitamin_b_complex: 'vitamin b',
  folate: 'folic acid', calcium: 'calcium', magnesium: 'magnesium', iron: 'iron',
  zinc: 'zinc', omega3: 'fish oil', lutein: 'lutein', probiotics: 'probiotic',
  coq10: 'coq10', milk_thistle: 'milk thistle', red_yeast_rice: 'red yeast rice',
  korean_ginseng: 'ginseng', msm: 'msm', lactium: 'lactium',
};
const FDA = 'https://api.fda.gov/food/event.json';

async function fda(url) {
  const res = await fetch(url, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error('openFDA ' + res.status);
  return res.json();
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('ingredient_id');
  const ing = id ? byId[id] : null;
  const term = searchParams.get('q') || (id ? (TERM[id] || (ing && ing.name_en)) : '');
  if (!term) return Response.json({ error: 'ingredient_id 또는 q가 필요합니다.' }, { status: 400 });

  const search = `products.name_brand:"${term}"`;
  try {
    // 총 보고 건수
    const totalRes = await fda(`${FDA}?search=${encodeURIComponent(search)}&limit=1`);
    const total = totalRes?.meta?.results?.total ?? 0;
    // 상위 증상(반응)
    let top_reactions = [];
    try {
      const rx = await fda(`${FDA}?search=${encodeURIComponent(search)}&count=reactions.exact`);
      top_reactions = (rx?.results || []).slice(0, 6).map((r) => ({ term: r.term, count: r.count }));
    } catch {}
    return Response.json({
      ingredient_id: id || null, query: term, source: 'openfda',
      total, top_reactions,
      disclaimer: 'FDA 이상사례 보고(CAERS) — 제품명 기준 단순 보고 건수이며 인과관계를 의미하지 않습니다.',
    });
  } catch (e) {
    return Response.json({ ingredient_id: id || null, query: term, source: 'none', total: null, top_reactions: [], reason: e.message });
  }
}
