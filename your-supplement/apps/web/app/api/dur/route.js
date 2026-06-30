// GET /api/dur?q=와파린   — 식약처 DUR(의약품안전사용서비스) 병용금기 등 조회
//  data.go.kr '의약품 안전사용서비스(DUR)' 활용신청 후 명세의 엔드포인트를
//  MFDS_DUR_API_URL 로 주입(serviceKey는 DATA_GO_KR_KEY). 미설정/오류 시 source:'none'.
//  ※ 정확한 오퍼레이션·파라미터는 활용신청 후 명세에만 있으므로 추측 하드코딩하지 않음.
export const runtime = 'nodejs';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q');
  if (!q) return Response.json({ error: 'q(약물/성분명)가 필요합니다.' }, { status: 400 });

  const base = process.env.MFDS_DUR_API_URL;
  const key = process.env.DATA_GO_KR_KEY;
  if (!base || !key) {
    return Response.json({ query: q, source: 'none', items: [], note: 'MFDS_DUR_API_URL 미설정 — data.go.kr DUR(15059486) 활용신청 후 명세 URL 입력 시 동작.' });
  }

  try {
    const url = `${base}?serviceKey=${encodeURIComponent(key)}&type=json&numOfRows=20&pageNo=1&itemName=${encodeURIComponent(q)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('DUR ' + res.status);
    const data = await res.json();
    const rows = data?.body?.items || data?.response?.body?.items?.item || data?.items || [];
    const arr = Array.isArray(rows) ? rows : [rows];
    const items = arr.map((r) => {
      const s = r.item || r;
      return {
        type: s.TYPE_NAME || s.typeName || s.PROHBT_CONTENT ? '병용금기' : (s.MIX_TYPE || '주의'),
        ingredient: s.INGR_KOR_NAME || s.ingrKorName || s.ITEM_NAME || s.itemName || '',
        against: s.MIXTURE_INGR_KOR_NAME || s.mixtureIngrKorName || '',
        reason: s.PROHBT_CONTENT || s.prohbtContent || s.NOTIFICATION_NUM || '',
      };
    }).filter((x) => x.ingredient || x.reason);
    return Response.json({ query: q, source: 'mfds_dur', items, note: '식약처 DUR 조회 결과(병용금기·주의).' });
  } catch (e) {
    return Response.json({ query: q, source: 'error', items: [], reason: e.message });
  }
}
