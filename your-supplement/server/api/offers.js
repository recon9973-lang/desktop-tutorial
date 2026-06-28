// 최저가 수집·조회 — 함량당 단가(price_per_active_mg) 기준 랭킹
// 수집: 네이버쇼핑 API 우선(공식/제휴). 크롤링 차단 사이트 지양.

// GET /api/offers?ingredient_id=omega3  → 가성비 랭킹
async function getOffers(req, res) {
  const { ingredient_id } = req.query;
  // TODO: DB price_offer 조회 → price_per_active_mg 오름차순 정렬
  const offers = await queryOffers(ingredient_id);
  offers.sort((a, b) => a.price_per_active_mg - b.price_per_active_mg);
  return res.status(200).json({ ingredient_id, best: offers[0] || null, offers });
}

// 배치(스케줄러): 네이버쇼핑 API에서 가격 갱신
async function refreshOffersFromNaver(ingredientKeyword) {
  // TODO: 네이버쇼핑 검색 API 호출 → 제품/가격/용량 파싱
  // active_mg_per_unit = 유효성분 함량, price_per_active_mg = price / (count * active_mg)
  // upsert price_offer
  throw new Error('NOT_IMPLEMENTED: 네이버쇼핑 API 키 연결 필요');
}

async function queryOffers(_ingredientId) {
  // TODO: DB 연결
  return [];
}

module.exports = { getOffers, refreshOffersFromNaver };
