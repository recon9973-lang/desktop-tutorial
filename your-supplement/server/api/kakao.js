// 카카오톡 전송 — ① 추천 결과 전송  ② 복용 알람
// 정보성 알림톡(비즈니스 채널)으로 설계해 광고성 규제 회피. 발송 전 사용자 동의(consent_push) 필수.

const TEMPLATES = {
  recommendation: 'your_supplement_result',
  intake_reminder: 'intake_reminder',
};

// 추천 결과를 카카오톡으로 전송
async function sendRecommendation(user, recommendation) {
  if (!user.channel?.consent_push) throw new Error('사용자 푸시 동의 없음');
  const payload = {
    title: `🧬 ${user.profile?.nickname || '회원'}님의 영양제`,
    items: recommendation.recommended
      .slice(0, 5)
      .map((r) => `${r.name}(근거${'⭐'.repeat(r.evidence_level)})`),
    schedule: `아침: ${recommendation.schedule.morning.join(', ')} / 저녁: ${recommendation.schedule.evening.join(', ')}`,
    link: `https://app/rec/${recommendation.id}`,
  };
  return sendAlimtalk(user, TEMPLATES.recommendation, payload);
}

// 복용 알람 전송 (intake_schedule 스케줄러가 호출)
async function sendIntakeReminder(user, mySupplement, time) {
  const payload = {
    title: '⏰ 영양제 드실 시간이에요',
    body: `${mySupplement.product_name} (${time})`,
    link: `https://app/my`,
  };
  return sendAlimtalk(user, TEMPLATES.intake_reminder, payload);
}

async function sendAlimtalk(_user, _template, _payload) {
  // TODO: 카카오 비즈메시지(알림톡) API 호출. kakao_message 레코드 status 갱신.
  throw new Error('NOT_IMPLEMENTED: 카카오 비즈니스 채널/알림톡 키 연결 필요');
}

module.exports = { sendRecommendation, sendIntakeReminder };
