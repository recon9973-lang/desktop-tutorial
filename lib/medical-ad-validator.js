'use strict';

// 의료법 제56조 + 의료광고심의 기준 기반 금칙/위험 표현 목록
const FORBIDDEN = [
  // 최상급 / 과장
  '최고','최상','최대','최초','유일','넘버원','1등','1위','업계 최고','국내 최고',
  '100% 효과','완치','완전히 낫','완벽한 치료','치료 보장','효과 보장','반드시',
  '무조건','절대적','탁월한 효과','놀라운 효과','기적','기적적',
  // 허위·과대 가능성
  '부작용 없','부작용 전혀','안전한 시술','완전히 안전','100% 안전',
  '통증 없이','통증 전혀','마취 없이도',
  // 비교 광고 (특정 병원/시술 비하)
  '타 병원보다','타 의원보다','경쟁 병원','다른 병원은 안',
  // 환자 유인
  '무료 시술','공짜 이벤트','경품','선착순 혜택','할인 쿠폰 지급',
  // 의료인 아닌 자 광고 금지 표현
  '연예인 추천','○○가 받은 시술','유명인',
  // 비급여 관련 불법 할인 암시
  '최저가 보장','가격 보장','가장 저렴',
];

const RISKY = [
  '효과적인','효능이 있는','우수한','탁월','뛰어난','빠른 회복',
  '빠른 효과','즉각적인','즉시 효과','검증된','임상 확인',
  '의학적으로 증명','과학적으로 검증','특허 받은','수상','인증받은',
  '추천합니다','권장합니다','강력 추천',
];

/**
 * @param {string} text
 * @returns {{ pass: boolean, forbidden: string[], risky: string[] }}
 */
function validateMedicalAd(text) {
  const lower = text.toLowerCase();
  const found_forbidden = FORBIDDEN.filter(w => lower.includes(w.toLowerCase()));
  const found_risky = RISKY.filter(w => lower.includes(w.toLowerCase()));
  return {
    pass: found_forbidden.length === 0,
    forbidden: found_forbidden,
    risky: found_risky,
  };
}

module.exports = { validateMedicalAd, FORBIDDEN, RISKY };
