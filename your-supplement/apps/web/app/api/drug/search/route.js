// GET /api/drug/search?q=&shape=&color=&imprint=&form=
// 의약품 '낱알식별' 검색 — 이름/성분 + 모양·색·각인·제형 필터.
//  - 데이터: 식약처 의약품 낱알식별 정보 OpenAPI (data.go.kr 15057639)
//    정확한 오퍼레이션/파라미터는 활용신청 후 명세에만 있으므로 base URL을
//    MFDS_PILL_API_URL 로 주입받아 표준 data.go.kr 형식으로 호출(추측 하드코딩 없음).
//    예) MFDS_PILL_API_URL=http://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService01/getMdcinGrnIdntfcInfoList01
//  - 미설정/차단 시: source:'unconfigured' + 의약품안전나라 낱알식별 검색 딥링크로 안내.
export const runtime = 'nodejs';

// 식약처 낱알식별 모양/색 표준값(필터 UI와 공유)
export const SHAPES = ['원형', '타원형', '장방형', '반원형', '삼각형', '사각형', '마름모형', '오각형', '육각형', '팔각형', '기타'];
export const COLORS = ['하양', '노랑', '주황', '분홍', '빨강', '갈색', '연두', '초록', '청록', '파랑', '남색', '보라', '회색', '검정', '투명'];

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const q = (searchParams.get('q') || '').trim();
  const shape = searchParams.get('shape') || '';
  const color = searchParams.get('color') || '';
  const imprint = (searchParams.get('imprint') || '').trim();
  const form = searchParams.get('form') || '';

  if (!q && !shape && !color && !imprint) {
    return Response.json({ error: '검색어나 필터(모양·색·각인)를 1개 이상 지정하세요.', results: [] }, { status: 400 });
  }

  // 의약품안전나라 검색 딥링크(항상 제공 — 키 없어도 이름 검색 가능)
  const nedrug_search = q
    ? `https://nedrug.mfds.go.kr/searchDrug?searchKeyword=${encodeURIComponent(q)}`
    : 'https://nedrug.mfds.go.kr/pbp/CCBGA01/getItem';

  const base = process.env.MFDS_PILL_API_URL;
  const key = process.env.DATA_GO_KR_KEY;

  if (!base || !key) {
    return Response.json({
      q, shape, color, imprint, form,
      source: 'unconfigured',
      results: [],
      nedrug_search,
      note: '식약처 낱알식별 실데이터는 data.go.kr 15057639 활용신청 + MFDS_PILL_API_URL·DATA_GO_KR_KEY 설정 시 동작. 지금은 의약품안전나라 검색으로 안내.',
    });
  }

  // 식약처 낱알식별 표준 파라미터
  const p = new URLSearchParams({ serviceKey: key, type: 'json', numOfRows: '20', pageNo: '1' });
  if (q) p.set('item_name', q);
  if (shape) p.set('drug_shape', shape);
  if (color) p.set('color_class1', color);
  if (imprint) { p.set('print_front', imprint); }
  if (form) p.set('form_code_name', form);

  try {
    const res = await fetch(`${base}?${p.toString()}`, { headers: { accept: 'application/json' } });
    if (!res.ok) throw new Error('MFDS ' + res.status);
    const data = await res.json();
    const rows = data?.body?.items || data?.response?.body?.items?.item || data?.items || [];
    const arr = Array.isArray(rows) ? rows : [rows].filter(Boolean);
    const results = arr.map((r) => {
      const s = r.item || r;
      return {
        name: s.ITEM_NAME || s.itemName || '(제품명 미상)',
        company: s.ENTP_NAME || s.entpName || '',
        shape: s.DRUG_SHAPE || s.drugShape || '',
        color: s.COLOR_CLASS1 || s.colorClass1 || '',
        imprint: [s.PRINT_FRONT, s.PRINT_BACK].filter(Boolean).join(' / ') || s.printFront || '',
        form: s.FORM_CODE_NAME || s.formCodeName || '',
        image: s.ITEM_IMAGE || s.itemImage || null,
        chart: s.CHART || s.chart || '',
        item_seq: s.ITEM_SEQ || s.itemSeq || null,
      };
    }).filter((x) => x.name && x.name !== '(제품명 미상)');
    return Response.json({ q, shape, color, imprint, form, source: 'mfds', results, nedrug_search });
  } catch (e) {
    return Response.json({ q, shape, color, imprint, form, source: 'error', reason: e.message, results: [], nedrug_search });
  }
}
