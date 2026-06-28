// 카카오톡 전송 — ① 추천 결과 전송  ② 복용 알람
// 정보성 알림톡(비즈니스 채널)으로 설계해 광고성 규제 회피. 발송 전 사용자 동의(consent_push) 필수.

// 환경변수에서 템플릿 코드를 가져와 코드상 하드코딩 방지
// 카카오 검수 후 발급되는 templateCode는 채널·계정마다 다르므로 반드시 환경변수로 관리
function getTemplates() {
  return {
    recommendation: process.env.KAKAO_TEMPLATE_RECOMMENDATION,
    intake_reminder: process.env.KAKAO_TEMPLATE_REMINDER,
  };
}

const KAKAO_API_BASE = 'https://alimtalk-api.kakao.com/v2/sender';
const RETRY_DELAY_MS = 500;

/**
 * 추천 결과를 카카오 알림톡으로 발송.
 * @param {object} user - { phone, channel: { consent_push }, profile: { nickname } }
 * @param {object} recommendation - { id, recommended: [{ name, evidence_level }], schedule: { morning, evening }, best_offer }
 */
async function sendRecommendation(user, recommendation) {
  if (!user.channel?.consent_push) {
    throw new Error('사용자 푸시 동의 없음');
  }

  const TEMPLATES = getTemplates();
  if (!TEMPLATES.recommendation) {
    throw new Error('KAKAO_TEMPLATE_RECOMMENDATION 환경변수가 설정되지 않았습니다');
  }

  const nickname = user.profile?.nickname || '회원';
  const topItems = (recommendation.recommended ?? []).slice(0, 5);

  // 알림톡 템플릿 변수 매핑 — 템플릿 검수 시 등록한 #{변수명}과 키 일치 필요
  const templateArgs = {
    nickname,
    recommend_list: topItems
      .map((r) => `${r.name} (근거 ${'★'.repeat(r.evidence_level)}${'☆'.repeat(3 - (r.evidence_level ?? 0))})`)
      .join('\n'),
    schedule_morning: (recommendation.schedule?.morning ?? []).join(', ') || '없음',
    schedule_evening: (recommendation.schedule?.evening ?? []).join(', ') || '없음',
    // 최저가 링크는 단축 URL이 필요하지만 MVP에서는 직링 사용
    best_offer_link: recommendation.best_offer?.link ?? `https://app/rec/${recommendation.id}`,
    rec_link: `https://app/rec/${recommendation.id}`,
  };

  return sendAlimtalk(user, TEMPLATES.recommendation, templateArgs);
}

/**
 * 복용 알람 발송. intake_schedule 스케줄러(schedule.js)가 매 분 호출.
 * @param {object} user - { phone, channel: { consent_push } }
 * @param {object} mySupplement - { product_name, ingredient_name }
 * @param {string} time - "08:00" 형태
 */
async function sendIntakeReminder(user, mySupplement, time) {
  if (!user.channel?.consent_push) {
    throw new Error('사용자 푸시 동의 없음');
  }

  const TEMPLATES = getTemplates();
  if (!TEMPLATES.intake_reminder) {
    throw new Error('KAKAO_TEMPLATE_REMINDER 환경변수가 설정되지 않았습니다');
  }

  const ingredientName = mySupplement.ingredient_name ?? mySupplement.product_name ?? '영양제';

  const templateArgs = {
    // ⏰ 이모지는 카카오 알림톡 템플릿 검수에서 허용되는 범위 내 사용
    message: `⏰ [${ingredientName}] 드실 시간이에요 (${time})`,
    product_name: mySupplement.product_name ?? '',
    time,
    my_link: 'https://app/my',
  };

  return sendAlimtalk(user, TEMPLATES.intake_reminder, templateArgs);
}

/**
 * 카카오 비즈메시지 알림톡 실제 발송. 실패 시 1회 retry.
 * @param {object} user - { phone } (E.164 또는 01012345678 형태)
 * @param {string} templateCode - 카카오 검수 완료된 템플릿 코드
 * @param {object} templateArgs - 템플릿 변수 key→value 매핑
 */
async function sendAlimtalk(user, templateCode, templateArgs) {
  const apiKey = process.env.KAKAO_API_KEY;
  const senderKey = process.env.KAKAO_SENDER_KEY;

  if (!apiKey || !senderKey) {
    throw new Error('KAKAO_API_KEY / KAKAO_SENDER_KEY 환경변수가 설정되지 않았습니다');
  }

  const phone = normalizePhone(user.phone);
  const endpoint = `${KAKAO_API_BASE}/${senderKey}/message`;

  const body = {
    to: phone,
    templateCode,
    // templateArgs는 객체이지만 카카오 API v2는 key-value 배열을 요구하지 않음 — 객체 그대로 전달
    templateArgs,
  };

  try {
    return await postWithRetry(endpoint, body, apiKey);
  } catch (err) {
    // 호출자(스케줄러, 라우터)가 알람별로 개별 처리할 수 있도록 래핑해서 던짐
    throw new Error(`알림톡 발송 실패 [template=${templateCode}, phone=${phone}]: ${err.message}`);
  }
}

/**
 * POST 요청 + 500ms 후 1회 retry.
 * 카카오 API는 5xx 오류 시 재시도 권장, 4xx는 재시도 불필요
 */
async function postWithRetry(url, body, apiKey) {
  const doPost = () =>
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `KakaoAK ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

  let res = await doPost();

  if (!res.ok && res.status >= 500) {
    // 서버 오류에 한해 1회만 재시도 (네트워크 순단, 카카오 점검 등 일시적 장애 대응)
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
    res = await doPost();
  }

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`HTTP ${res.status}: ${errorBody}`);
  }

  return res.json();
}

/** 010-1234-5678 → 01012345678, +821012345678 → 01012345678 */
function normalizePhone(phone) {
  if (!phone) throw new Error('user.phone이 없습니다');
  return phone.replace(/[^0-9]/g, '').replace(/^82/, '0');
}

module.exports = { sendRecommendation, sendIntakeReminder };
