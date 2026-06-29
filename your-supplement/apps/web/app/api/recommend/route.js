// POST /api/recommend — 설문 입력 → 추천 결과 (공유 엔진 ESM 포트 사용)
// body: { profile, concerns:[...], medications:[...], allergies:[...], lifestyle }
import { recommend } from '../../../lib/engine';

export const runtime = 'nodejs';

export async function POST(request) {
  let user;
  try {
    user = await request.json();
  } catch {
    return Response.json({ error: '잘못된 요청 형식입니다.' }, { status: 400 });
  }

  if (!user || !Array.isArray(user.concerns) || user.concerns.length === 0) {
    return Response.json({ error: 'concerns(고민)를 1개 이상 선택하세요.' }, { status: 400 });
  }

  const result = recommend({
    concerns: user.concerns,
    medications: Array.isArray(user.medications) ? user.medications : [],
    allergies: Array.isArray(user.allergies) ? user.allergies : [],
  });

  // 최저가(best_price) 결합은 프론트가 /api/offers 로 항목별 조회 → 여기선 추천만 책임.
  return Response.json(result);
}
