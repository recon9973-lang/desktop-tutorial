// POST /api/drug/ocr  { image: "<base64 data URL or raw base64>" }
// 알약 사진 → 각인(식별문자) OCR 추출. 결과는 후보 검색용 힌트(자동 확진 아님).
//  - 기획서 원칙: 현장 인식률 한계 → "보조 도구". 추출 각인으로 /drug 필터검색에 프리필.
//  - config-driven: 네이버 CLOVA OCR(권장) 또는 Google Vision. 미설정 시 준비중 안내.
//    CLOVA:  CLOVA_OCR_INVOKE_URL + CLOVA_OCR_SECRET
//    Vision: GOOGLE_VISION_API_KEY
export const runtime = 'nodejs';

// 각인 후보 정제: 영문 대문자·숫자 토큰만(약 각인 특성)
function extractImprint(text) {
  if (!text) return '';
  const tokens = text.toUpperCase().match(/[A-Z0-9]{2,}/g) || [];
  return [...new Set(tokens)].slice(0, 6).join(' ');
}

async function clovaOCR(base64) {
  const url = process.env.CLOVA_OCR_INVOKE_URL;
  const secret = process.env.CLOVA_OCR_SECRET;
  if (!url || !secret) return null;
  const body = {
    version: 'V2', requestId: 'pill-' + Date.now(), timestamp: Date.now(),
    images: [{ format: 'jpg', name: 'pill', data: base64 }],
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-OCR-SECRET': secret },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('CLOVA ' + res.status);
  const data = await res.json();
  const fields = data?.images?.[0]?.fields || [];
  return fields.map((f) => f.inferText).join(' ');
}

async function visionOCR(base64) {
  const key = process.env.GOOGLE_VISION_API_KEY;
  if (!key) return null;
  const res = await fetch(`https://vision.googleapis.com/v1/images:annotate?key=${key}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requests: [{ image: { content: base64 }, features: [{ type: 'TEXT_DETECTION' }] }] }),
  });
  if (!res.ok) throw new Error('VISION ' + res.status);
  const data = await res.json();
  return data?.responses?.[0]?.fullTextAnnotation?.text || '';
}

export async function POST(request) {
  let image = '';
  try {
    const b = await request.json();
    image = b.image || '';
  } catch {
    return Response.json({ error: '이미지가 필요합니다.' }, { status: 400 });
  }
  const base64 = image.includes(',') ? image.split(',')[1] : image;
  if (!base64) return Response.json({ error: '이미지가 비어 있습니다.' }, { status: 400 });

  const hasClova = process.env.CLOVA_OCR_INVOKE_URL && process.env.CLOVA_OCR_SECRET;
  const hasVision = process.env.GOOGLE_VISION_API_KEY;
  if (!hasClova && !hasVision) {
    return Response.json({
      source: 'unconfigured',
      imprint: '',
      note: '사진 각인 인식(OCR)은 CLOVA_OCR_INVOKE_URL/CLOVA_OCR_SECRET 또는 GOOGLE_VISION_API_KEY 설정 시 동작. 지금은 모양·색·각인 필터 검색을 이용하세요.',
    });
  }

  try {
    const text = hasClova ? await clovaOCR(base64) : await visionOCR(base64);
    const imprint = extractImprint(text);
    return Response.json({ source: hasClova ? 'clova' : 'vision', raw: text || '', imprint });
  } catch (e) {
    return Response.json({ source: 'error', reason: e.message, imprint: '' });
  }
}
