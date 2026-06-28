// 최저가 수집·조회 — 함량당 단가(price_per_active_mg) 기준 랭킹
// 수집: 네이버쇼핑 API 우선(공식/제휴). 크롤링 차단 사이트 지양.

const NAVER_SHOP_URL = 'https://openapi.naver.com/v1/search/shop.json';
const CACHE_TTL_MS = 60 * 60 * 1000; // 1시간

// 성분 ID → 네이버쇼핑 검색 키워드 매핑
// 제품명+함량 조합이어야 함량당 단가 계산에 의미있는 결과가 나옴
const INGREDIENT_KEYWORDS = {
  omega3: '오메가3 EPA DHA',
  vitamin_d: '비타민D 2000IU',
  lutein: '루테인 10mg',
  magnesium: '마그네슘 글리시네이트',
  vitamin_b_complex: '비타민B군 복합',
  vitamin_c: '비타민C 1000mg',
  zinc: '아연 15mg',
  iron: '철분 14mg',
  calcium: '칼슘 마그네슘 비타민D',
  probiotics: '유산균 100억',
};

// { ingredientId → { items: [...], cachedAt: timestamp } }
const offersCache = new Map();

/**
 * 네이버쇼핑 API로 영양제 최저가를 수집해 캐시에 저장.
 * @param {string} ingredientId - INGREDIENT_KEYWORDS 키
 * @param {string} keyword - 검색어 (없으면 INGREDIENT_KEYWORDS 기본값 사용)
 * @param {number} activeMgPerUnit - 1정당 유효성분 함량(mg). 가격÷(개수×mg) = price_per_active_mg
 */
async function refreshOffersFromNaver(ingredientId, keyword, activeMgPerUnit) {
  const clientId = process.env.NAVER_CLIENT_ID;
  const clientSecret = process.env.NAVER_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    throw new Error('NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다');
  }

  const query = keyword ?? INGREDIENT_KEYWORDS[ingredientId];
  if (!query) {
    throw new Error(`알 수 없는 성분 ID: ${ingredientId}. INGREDIENT_KEYWORDS에 키워드를 추가하세요.`);
  }

  const url = new URL(NAVER_SHOP_URL);
  url.searchParams.set('query', query);
  url.searchParams.set('display', '10');
  url.searchParams.set('sort', 'asc'); // 가격 오름차순

  const res = await fetch(url.toString(), {
    headers: {
      'X-Naver-Client-Id': clientId,
      'X-Naver-Client-Secret': clientSecret,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`네이버쇼핑 API 오류 ${res.status}: ${body}`);
  }

  const data = await res.json();

  const items = (data.items ?? []).map((item) => {
    const price = parseInt(item.lprice, 10) || 0;

    // 제목에서 정/캡슐 수량 파싱 시도 (예: "120정", "60캡슐")
    // 파싱 실패 시 1로 처리 — 호출자가 activeMgPerUnit를 정확히 넘겨야 의미있는 비교 가능
    const countMatch = item.title.replace(/(<([^>]+)>)/gi, '').match(/(\d+)\s*(?:정|캡슐|알|tab)/i);
    const unitCount = countMatch ? parseInt(countMatch[1], 10) : 1;

    const mgPerUnit = activeMgPerUnit ?? 1;
    // price_per_active_mg: 원/mg 단위. 낮을수록 가성비 좋음
    const price_per_active_mg = unitCount > 0 && mgPerUnit > 0
      ? price / (unitCount * mgPerUnit)
      : null;

    return {
      title: item.title.replace(/(<([^>]+)>)/gi, ''), // 네이버 응답에 HTML 태그 포함됨
      lprice: price,
      mallName: item.mallName,
      link: item.link,
      unitCount,
      price_per_active_mg,
    };
  });

  // price_per_active_mg 계산 실패 항목은 뒤로 밀어서 랭킹 일관성 유지
  items.sort((a, b) => {
    if (a.price_per_active_mg == null) return 1;
    if (b.price_per_active_mg == null) return -1;
    return a.price_per_active_mg - b.price_per_active_mg;
  });

  offersCache.set(ingredientId, { items, cachedAt: Date.now() });
  return items;
}

/**
 * 인메모리 캐시에서 최저가 목록 반환. TTL 초과 시 재수집.
 * MVP 단계 — DB 없이 프로세스 메모리에 보관하므로 서버 재시작 시 초기화됨.
 */
async function getOffersFromCache(ingredientId, activeMgPerUnit) {
  const cached = offersCache.get(ingredientId);
  const isStale = !cached || Date.now() - cached.cachedAt > CACHE_TTL_MS;

  if (isStale) {
    return refreshOffersFromNaver(ingredientId, undefined, activeMgPerUnit);
  }
  return cached.items;
}

// GET /api/offers?ingredient_id=omega3&active_mg=1000
async function getOffers(req, res) {
  const { ingredient_id, active_mg } = req.query;
  if (!ingredient_id) {
    return res.status(400).json({ error: 'ingredient_id 파라미터가 필요합니다' });
  }

  const activeMgPerUnit = active_mg ? parseFloat(active_mg) : undefined;
  const offers = await getOffersFromCache(ingredient_id, activeMgPerUnit);

  return res.status(200).json({
    ingredient_id,
    best: offers[0] ?? null,
    offers,
  });
}

module.exports = { getOffers, refreshOffersFromNaver, getOffersFromCache, INGREDIENT_KEYWORDS };
