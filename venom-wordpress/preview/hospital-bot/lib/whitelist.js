'use strict';

// ============================================================
// whitelist — 베노미 내부 직원 발신자 게이팅
// ------------------------------------------------------------
// 카카오 스킬 요청의 userRequest.user.id 를 허용 목록과 대조.
// env VENOMI_WHITELIST = 쉼표구분 카카오 botUserKey 목록.
//   · 미설정 → 'open'(개발/셋업 단계, 누구나 허용) — 로그로 경고.
//   · 설정   → 'enforced'(목록에 있는 직원만 허용).
// 내부 우선 제품이므로, 운영 전환 시 반드시 목록을 채워 enforced로 잠근다.
// ============================================================

function parseList() {
  return String(process.env.VENOMI_WHITELIST || '')
    .split(/[,\s]+/).map((s) => s.trim()).filter(Boolean);
}

function isConfigured() {
  return parseList().length > 0;
}

// { allowed, mode:'open'|'enforced' }
function check(userId) {
  const list = parseList();
  if (!list.length) return { allowed: true, mode: 'open' };
  return { allowed: list.includes(String(userId || '')), mode: 'enforced' };
}

module.exports = { parseList, isConfigured, check };
