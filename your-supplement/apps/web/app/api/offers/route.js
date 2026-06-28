// GET /api/offers?ingredient_id=vitamin_d
// 네이버쇼핑 API로 실제 최저가(가성비=하루당 가격 기준)를 가져온다.
// 키는 apps/web/.env.local 의 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 에서 읽음.
// (쿠팡·아이허브는 공개 상품검색 API가 없어 검색 딥링크로만 연결 — UI의 buyLinks 참고)

export const runtime = 'nodejs';

const NAVER_SHOP_URL = 'https://openapi.naver.com/v1/search/shop.json';

// 성분 → 검색 키워드 + 1일 복용 정수(하루당 가격 계산용)
const INGREDIENT_QUERY = {
  vitamin_d:         { keyword: '비타민D 2000IU',          dosePerDay: 1 },
  vitamin_b_complex: { keyword: '비타민B 컴플렉스',         dosePerDay: 1 },
  lutein:            { keyword: '루테인 지아잔틴',           dosePerDay: 1 },
  magnesium:         { keyword: '마그네슘 글리시네이트',     dosePerDay: 1 },
  omega3:            { keyword: '알티지 오메가3',            dosePerDay: 1 },
  vitamin_c:         { keyword: '비타민C 1000mg',           dosePerDay: 1 },
  zinc:              { keyword: '아연 15mg',                dosePerDay: 1 },
  iron:              { keyword: '철분 영양제',              dosePerDay: 1 },
  calcium:           { keyword: '칼슘 마그네슘 비타민D',     dosePerDay: 2 },
  probiotics:        { keyword: '유산균 프로바이오틱스',     dosePerDay: 1 },
};

const stripTags = (s) => s.replace(/<[^>]+>/g, '');

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const ingredientId = searchParams.get('ingredient_id');
  const meta = INGREDIENT_QUERY[ingredientId];

  if (!meta) {
    return Response.json({ error: '알 수 없는 ingredient_id' }, { status: 400 });
  }

  const clientId = process.env.NAVER_CLIENT_ID;
  const clientSecret = process.env.NAVER_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    // 키가 없으면 best:null → 프론트가 샘플 데이터로 폴백
    return Response.json({ ingredient_id: ingredientId, best: null, reason: 'NO_KEY' });
  }

  const url = new URL(NAVER_SHOP_URL);
  url.searchParams.set('query', meta.keyword);
  url.searchParams.set('display', '30');
  url.searchParams.set('sort', 'asc'); // 가격 오름차순

  let data;
  try {
    const res = await fetch(url.toString(), {
      headers: { 'X-Naver-Client-Id': clientId, 'X-Naver-Client-Secret': clientSecret },
    });
    if (!res.ok) {
      const body = await res.text();
      return Response.json({ ingredient_id: ingredientId, best: null, reason: `NAVER_${res.status}`, detail: body }, { status: 200 });
    }
    data = await res.json();
  } catch (e) {
    return Response.json({ ingredient_id: ingredientId, best: null, reason: 'FETCH_ERROR', detail: e.message }, { status: 200 });
  }

  // 제목에서 정/캡슐 수량 파싱 → 하루당 가격 계산. 가성비(하루당 최저) 1위 선정.
  const candidates = (data.items ?? [])
    .map((item) => {
      const title = stripTags(item.title);
      const price = parseInt(item.lprice, 10) || 0;
      const m = title.match(/(\d+)\s*(?:정|캡슐|구미|포|일분|개월|박스)?\s*x?\s*(\d+)?\s*(?:정|캡슐)/i)
             || title.match(/(\d+)\s*(?:정|캡슐|구미|포)/i);
      const count = m ? parseInt(m[1], 10) * (m[2] ? parseInt(m[2], 10) : 1) : null;
      if (!count || count < 20 || price < 3000) return null; // 샘플·소량팩 제외
      const days = count / meta.dosePerDay;
      return {
        product: title,
        price,
        count,
        per_day: Math.round(price / days),
        vendor: '네이버',
        mall: item.mallName,
        link: item.link,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.per_day - b.per_day); // 하루당 가격 최저 = 가성비 1위

  return Response.json({
    ingredient_id: ingredientId,
    best: candidates[0] ?? null,
    alternatives: candidates.slice(1, 4),
  });
}
