// GET /api/products?ingredient_id=vitamin_d  (또는 &q=키워드)
// 시판 영양제 '제품'을 성분 단위로 검색.
//  - 해외: NIH DSLD(라벨 20만건+, 무료·키 불필요) — 배포환경에서 실데이터, 실패/샌드박스는 샘플.
//  - 국내: 식약처 건강기능식품 품목 OpenAPI 연동은 키 활용신청 후(TODO) — 현재는 쇼핑 검색 딥링크 제공.
import ingredientsData from '../../../data/ingredients.json';

export const runtime = 'nodejs';

const byId = Object.fromEntries(ingredientsData.ingredients.map((i) => [i.id, i]));

// 성분 → DSLD 영문 검색어
const DSLD_QUERY = {
  vitamin_d: 'vitamin d', vitamin_c: 'vitamin c', vitamin_b_complex: 'vitamin b complex',
  folate: 'folate folic acid', calcium: 'calcium', magnesium: 'magnesium', iron: 'iron',
  zinc: 'zinc', omega3: 'omega-3 fish oil', lutein: 'lutein', probiotics: 'probiotic',
  coq10: 'coenzyme q10', milk_thistle: 'milk thistle', red_yeast_rice: 'red yeast rice',
  korean_ginseng: 'korean ginseng', msm: 'msm', lactium: 'lactium',
};

// DSLD 미도달(샌드박스/오류) 시 보여줄 예시 해외 제품
const SAMPLE_GLOBAL = {
  vitamin_d: [
    { name: 'Vitamin D3 2000 IU', brand: 'NOW Foods' },
    { name: 'Vitamin D-3 5000 IU', brand: "Nature's Bounty" },
  ],
  omega3: [
    { name: 'Ultimate Omega', brand: 'Nordic Naturals' },
    { name: 'Triple Strength Omega-3', brand: 'Sports Research' },
  ],
  magnesium: [{ name: 'Magnesium Glycinate', brand: 'Doctor’s Best' }],
  lutein: [{ name: 'Lutein 20mg', brand: 'NOW Foods' }],
  probiotics: [{ name: 'Ultimate Flora Probiotic', brand: 'Renew Life' }],
};

const sampleFor = (id) => (SAMPLE_GLOBAL[id] || []).map((p) => ({ ...p, url: null }));

async function searchDSLD(query) {
  const url = `https://api.ods.od.nih.gov/dsld/v9/search-filter?q=${encodeURIComponent(query)}&size=10`;
  const res = await fetch(url, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error('DSLD ' + res.status);
  const data = await res.json();
  // DSLD v9 search-filter: { hits: [ { id, fullName, brandName, src, ingredientRows, ... } ] }
  // (버전/래퍼 차이를 모두 흡수)
  const rows = data?.hits?.hits || data?.hits || data?.results || [];
  return rows.slice(0, 10).map((h) => {
    const s = h._source || h.src || h;
    const dsldId = h.id || h._id || s.id || s.dsldId;
    return {
      name: s.fullName || h.fullName || s.productName || s.brandName || h.brandName || '(제품명 미상)',
      brand: s.brandName || h.brandName || s.brandIngredientName || '',
      url: dsldId ? `https://dsld.od.nih.gov/label/${dsldId}` : null,
    };
  }).filter((p) => p.name && p.name !== '(제품명 미상)');
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const ingredientId = searchParams.get('ingredient_id');
  const ing = ingredientId ? byId[ingredientId] : null;
  const q = searchParams.get('q') || (ing ? (DSLD_QUERY[ingredientId] || ing.name_en) : '');

  if (!q) return Response.json({ error: 'ingredient_id 또는 q가 필요합니다.' }, { status: 400 });

  const nameKo = ing ? ing.name_ko : q;
  const qKo = encodeURIComponent(nameKo);
  const kr_search = [
    { vendor: '네이버쇼핑', url: `https://search.shopping.naver.com/search/all?query=${qKo}` },
    { vendor: '쿠팡', url: `https://www.coupang.com/np/search?q=${qKo}` },
    { vendor: '식품안전나라', url: 'https://various.foodsafetykorea.go.kr/nutrient/' },
  ];

  let global = { source: 'sample', products: sampleFor(ingredientId) };
  try {
    const products = await searchDSLD(q);
    if (products.length) global = { source: 'dsld', products };
  } catch (e) {
    global.reason = e.message;
  }

  return Response.json({
    ingredient_id: ingredientId || null,
    name_ko: nameKo,
    query: q,
    global,        // 해외(DSLD) 실제 시판 제품
    kr_search,     // 국내 제품 검색(쇼핑·식약처) — 품목 API는 키 연동 예정
    note: '국내 식약처 건강기능식품 품목 OpenAPI 연동 예정(키 활용신청 후). 해외는 NIH DSLD 실시간.',
  });
}
