// GET /api/nearby?type=pharmacy|er|kids&sido=서울특별시&sigungu=강남구
// 공공데이터(국립중앙의료원 E-Gen) 약국·응급실 정보. 키(DATA_GO_KR_KEY) 있으면 실데이터, 없으면 샘플.
// 키 발급: data.go.kr → '전국 약국 정보 조회 서비스' / '전국 응급의료기관 정보 조회 서비스' 활용신청

export const runtime = 'nodejs';

const EGEN_BASE = 'http://apis.data.go.kr/B552657';
const ENDPOINT = {
  pharmacy: `${EGEN_BASE}/ErmctInsttInfoInqireService/getParmacyListInfoInqire`,
  er:       `${EGEN_BASE}/ErmctInfoInqireService/getEgytListInfoInqire`,
  kids:     `${EGEN_BASE}/ErmctInfoInqireService/getEgytListInfoInqire`, // 달빛어린이병원은 별도 필터 필요
};

// 키 없을 때 보여줄 샘플 (서울 강남 일대 예시)
const SAMPLE = {
  pharmacy: [
    { name: '연세온누리약국', addr: '서울 강남구 강남대로 390', tel: '02-558-1004', lat: 37.4979, lng: 127.0276, open: '09:00', close: '24:00', is24h: false, tags: ['심야'] },
    { name: '강남세브란스약국', addr: '서울 강남구 언주로 211', tel: '02-2019-1004', lat: 37.4926, lng: 127.0473, open: '00:00', close: '24:00', is24h: true, tags: ['24시'] },
    { name: '온누리H약국', addr: '서울 강남구 테헤란로 152', tel: '02-565-1004', lat: 37.5006, lng: 127.0366, open: '08:30', close: '22:00', is24h: false, tags: [] },
    { name: '행복한약국', addr: '서울 강남구 봉은사로 213', tel: '02-501-1004', lat: 37.5089, lng: 127.0421, open: '09:00', close: '21:00', is24h: false, tags: ['공휴일'] },
  ],
  er: [
    { name: '삼성서울병원 응급실', addr: '서울 강남구 일원로 81', tel: '02-3410-2060', lat: 37.4881, lng: 127.0856, open: '00:00', close: '24:00', is24h: true, beds: 7, tags: ['권역응급'] },
    { name: '강남세브란스병원 응급실', addr: '서울 강남구 언주로 211', tel: '02-2019-3333', lat: 37.4926, lng: 127.0473, open: '00:00', close: '24:00', is24h: true, beds: 3, tags: ['지역응급'] },
  ],
  kids: [
    { name: '연세곰돌이소아청소년과', addr: '서울 강남구 도곡로 408', tel: '02-575-7585', lat: 37.4901, lng: 127.0469, open: '09:00', close: '23:00', is24h: false, tags: ['달빛어린이병원'] },
    { name: '우리아이들병원', addr: '서울 구로구 새말로 117', tel: '02-858-0100', lat: 37.4954, lng: 126.8874, open: '09:00', close: '23:00', is24h: false, tags: ['달빛어린이병원'] },
  ],
};

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type') || 'pharmacy';
  const sido = searchParams.get('sido') || '서울특별시';
  const sigungu = searchParams.get('sigungu') || '강남구';

  const serviceKey = process.env.DATA_GO_KR_KEY;

  // 키 없으면 샘플 반환 (화면이 항상 뜨도록)
  if (!serviceKey || !ENDPOINT[type]) {
    return Response.json({ type, sido, sigungu, source: 'sample', items: SAMPLE[type] || [] });
  }

  try {
    const url = new URL(ENDPOINT[type]);
    url.searchParams.set('serviceKey', serviceKey);
    url.searchParams.set('Q0', sido);
    url.searchParams.set('Q1', sigungu);
    url.searchParams.set('pageNo', '1');
    url.searchParams.set('numOfRows', '20');
    url.searchParams.set('_type', 'json');

    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`E-Gen ${res.status}`);
    const data = await res.json();
    const rows = data?.response?.body?.items?.item ?? [];
    const list = (Array.isArray(rows) ? rows : [rows]).map((r) => ({
      name: r.dutyName,
      addr: r.dutyAddr,
      tel: r.dutyTel1,
      lat: Number(r.wgs84Lat) || null,
      lng: Number(r.wgs84Lon) || null,
      // 요일별 영업시간 필드(dutyTime1s~8c) — 표시 단순화를 위해 원자료도 함께 전달
      raw: r,
      tags: [],
    }));
    return Response.json({ type, sido, sigungu, source: 'live', items: list });
  } catch (e) {
    return Response.json({ type, sido, sigungu, source: 'sample', reason: e.message, items: SAMPLE[type] || [] });
  }
}
