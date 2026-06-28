// POST /api/recommend  — 설문 입력 → 추천 결과
// 웹·앱 공유 엔진(engine/recommend.js)을 그대로 사용.
const { recommend } = require('../../engine/recommend');

// 프레임워크 무관 핸들러(Express/Vercel/Next API 등에 맞춰 래핑)
async function handleRecommend(req, res) {
  const user = req.body; // { profile, concerns, medications, allergies }
  if (!user || !Array.isArray(user.concerns) || user.concerns.length === 0) {
    return res.status(400).json({ error: 'concerns(고민)를 1개 이상 선택하세요.' });
  }
  const result = recommend(user);

  // TODO: result.recommended 각 항목에 best_offer(최저가) 결합 → offers.js
  // TODO: recommendation 스냅샷 DB 저장 후 id 반환(카카오 전송·내영양제 등록에 사용)
  return res.status(200).json(result);
}

module.exports = { handleRecommend };
