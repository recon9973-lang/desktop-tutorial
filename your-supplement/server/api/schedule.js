// 섭취 알람 스케줄러 + 복용기간 점검 알림
// 알람 채널: 카카오 알림톡 + 앱 푸시(이중). 둘 중 사용자 설정 채널로 발송.

const { sendIntakeReminder } = require('./kakao');

// 내 영양제 등록 시: 복용기간 타입에 따라 점검 알림 예약
function planReviewReminder(mySupplement, durationPolicy) {
  const policy = durationPolicy[mySupplement.duration_type];
  if (!policy?.review_after_days) return null; // 🟢지속형은 점검 알림 없음
  // review_due_at = started_at + review_after_days  (🟡90일 / 🔴56일)
  return { type: 'review', after_days: policy.review_after_days, message: policy.reminder };
}

// 매 분 실행되는 틱: next_fire_at 도래한 스케줄 발송
async function tickIntakeAlarms(nowISO) {
  const due = await queryDueSchedules(nowISO); // intake_schedule where next_fire_at <= now & active
  for (const sch of due) {
    const user = await getUser(sch.user_id);
    const my = await getMySupplement(sch.my_supplement_id);
    try {
      if (sch.channel === 'kakao') await sendIntakeReminder(user, my, currentTime(sch));
      else await sendPush(user, my, currentTime(sch)); // 앱 푸시(Expo)
    } finally {
      await advanceNextFire(sch); // 다음 요일/시간 계산해 next_fire_at 갱신
    }
  }
}

// ── DB/푸시 스텁 (구현 예정) ──
async function queryDueSchedules(_now) { return []; }
async function getUser(_id) { return {}; }
async function getMySupplement(_id) { return {}; }
async function advanceNextFire(_sch) {}
async function sendPush(_user, _my, _time) { /* TODO: Expo Push API */ }
function currentTime(sch) { return sch.times?.[0] || ''; }

module.exports = { planReviewReminder, tickIntakeAlarms };
