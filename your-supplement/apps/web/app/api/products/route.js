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

// 자유검색(한글) → DSLD 영문 검색어. DSLD는 영문 DB라 한글 그대로는 0건이므로,
// 우리 17개 KB 밖의 인기 성분도 한글로 검색되게 매핑(키는 공백 제거·소문자).
const KO_EN = {
  '아르기닌': 'arginine', '엘아르기닌': 'l-arginine', '시트룰린': 'citrulline',
  '콜라겐': 'collagen', '비오틴': 'biotin', '바이오틴': 'biotin',
  '글루타민': 'glutamine', '크레아틴': 'creatine', '타우린': 'taurine',
  '글루코사민': 'glucosamine', '콘드로이친': 'chondroitin', '쏘팔메토': 'saw palmetto',
  '은행잎': 'ginkgo biloba', '강황': 'turmeric', '커큐민': 'curcumin', '보스웰리아': 'boswellia',
  '스피루리나': 'spirulina', '클로렐라': 'chlorella', '멜라토닌': 'melatonin', '테아닌': 'l-theanine',
  '셀레늄': 'selenium', '크롬': 'chromium', '망간': 'manganese', '구리': 'copper',
  '비타민a': 'vitamin a', '비타민e': 'vitamin e', '비타민k': 'vitamin k', '비타민b': 'vitamin b complex',
  '엽산': 'folate folic acid', '유산균': 'probiotic', '프리바이오틱스': 'prebiotic', '실리마린': 'silymarin',
  '코큐텐': 'coenzyme q10', '코엔자임q10': 'coenzyme q10', '코엔자임큐텐': 'coenzyme q10', '인삼': 'ginseng',
  '아연': 'zinc', '철분': 'iron', '칼슘': 'calcium', '마그네슘': 'magnesium',
  '비타민d': 'vitamin d', '비타민c': 'vitamin c', '오메가3': 'omega-3 fish oil', '루테인': 'lutein',
};
const toDsldTerm = (q) => KO_EN[String(q).toLowerCase().replace(/\s+/g, '')] || q;

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

// 식약처 건강기능식품 품목 OpenAPI (config-driven)
// 정확한 오퍼레이션/파라미터는 data.go.kr 활용신청 후 명세에만 있으므로,
// 전체 base URL을 MFDS_PRODUCT_API_URL 로 주입받아 표준 data.go.kr 형식으로 호출한다.
//   예) MFDS_PRODUCT_API_URL=http://apis.data.go.kr/1471000/HtfsItemInfoService/getHtfsItem
async function searchMFDS(nameKo) {
  const base = process.env.MFDS_PRODUCT_API_URL;
  const key = process.env.DATA_GO_KR_KEY;
  if (!base || !key) return null; // 미설정 → 국내 쇼핑 딥링크로 폴백
  const url = `${base}?serviceKey=${encodeURIComponent(key)}&type=json&numOfRows=10&pageNo=1&prdlstNm=${encodeURIComponent(nameKo)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('MFDS ' + res.status);
  const data = await res.json();
  const rows = data?.body?.items || data?.response?.body?.items?.item || data?.items || [];
  const arr = Array.isArray(rows) ? rows : [rows];
  return arr.map((r) => {
    const s = r.item || r;
    return {
      name: s.PRDLST_NM || s.prdlstNm || s.PRODUCT || s.itemName || '(제품명 미상)',
      brand: s.BSSH_NM || s.bsshNm || s.company || '',
      no: s.PRDLST_REPORT_NO || s.prdlstReportNo || s.itemReportNo || null,
    };
  }).filter((p) => p.name && p.name !== '(제품명 미상)').slice(0, 10);
}

// Health Canada LNHPD (캐나다 허가 천연건강제품) — config-driven.
// 정확한 리소스 경로는 포털 명세 확인 필요 → LNHPD_API_URL 주입 시 동작(키 불필요).
async function searchLNHPD(term) {
  const base = process.env.LNHPD_API_URL;
  if (!base) return null;
  const url = `${base}${base.includes('?') ? '&' : '?'}type=json&product_name=${encodeURIComponent(term)}`;
  const res = await fetch(url, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error('LNHPD ' + res.status);
  const data = await res.json();
  const rows = Array.isArray(data) ? data : (data?.data || data?.results || []);
  return rows.slice(0, 8).map((r) => ({
    name: r.product_name || r.productName || r.licence_name || '(제품명 미상)',
    brand: r.company_name || r.companyName || '',
    url: r.lnhpd_id ? `https://health-products.canada.ca/lnhpd-bdpsnh/info.do?licence=${r.lnhpd_id}` : null,
  })).filter((p) => p.name && p.name !== '(제품명 미상)');
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

  // 성분칩이면 q가 이미 영문(DSLD_QUERY), 자유검색이면 한글→영문 매핑 적용
  const dsldTerm = ing ? q : toDsldTerm(q);
  let global = { source: 'sample', products: sampleFor(ingredientId) };
  try {
    const products = await searchDSLD(dsldTerm);
    if (products.length) global = { source: 'dsld', products };
  } catch (e) {
    global.reason = e.message;
  }

  // 국내 식약처 품목(설정 시) — 미설정/오류면 null → 쇼핑 딥링크로 안내
  let kr_products = null;
  try {
    const mfds = await searchMFDS(nameKo);
    if (mfds && mfds.length) kr_products = { source: 'mfds', products: mfds };
  } catch (e) {
    kr_products = { source: 'error', reason: e.message, products: [] };
  }

  // 캐나다 LNHPD(설정 시) — 글로벌 제품 확장
  let ca_products = null;
  try {
    const ca = await searchLNHPD(q);
    if (ca && ca.length) ca_products = { source: 'lnhpd', products: ca };
  } catch (e) {
    ca_products = { source: 'error', reason: e.message, products: [] };
  }

  return Response.json({
    ingredient_id: ingredientId || null,
    name_ko: nameKo,
    query: q,
    global,        // 해외(DSLD) 실제 시판 제품
    kr_products,   // 국내(식약처 품목) — MFDS_PRODUCT_API_URL 설정 시
    ca_products,   // 캐나다(LNHPD) — LNHPD_API_URL 설정 시
    kr_search,     // 국내 제품 검색 딥링크(쇼핑·식품안전나라)
    note: kr_products
      ? '국내는 식약처 품목 API, 해외는 NIH DSLD 실시간.'
      : '국내 식약처 건강기능식품 품목 OpenAPI는 활용신청+MFDS_PRODUCT_API_URL 설정 후 동작. 해외는 NIH DSLD 실시간.',
  });
}
