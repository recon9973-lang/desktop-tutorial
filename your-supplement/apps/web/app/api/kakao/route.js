// POST /api/kakao  — 추천 결과/복용 알림을 카카오 알림톡으로 발송
//  body: { type:'recommendation'|'reminder', phone, args:{...}, consent:true }
//  카카오 알림톡은 발신대행사(예: NHN Toast·Solapi·BizM 등)를 통해 발송되므로,
//  공급사 발송 엔드포인트를 ALIMTALK_API_URL, 인증헤더를 ALIMTALK_API_KEY 로 주입.
//  승인 템플릿 코드는 KAKAO_TEMPLATE_* 환경변수. 미설정/오류 시 sent:false.
export const runtime = 'nodejs';

const TEMPLATE = {
  recommendation: () => process.env.KAKAO_TEMPLATE_RECOMMENDATION,
  reminder: () => process.env.KAKAO_TEMPLATE_REMINDER,
};

export async function POST(request) {
  let body;
  try { body = await request.json(); } catch { return Response.json({ error: '잘못된 요청' }, { status: 400 }); }

  const { type = 'recommendation', phone, args = {}, consent } = body;
  if (!consent) return Response.json({ sent: false, reason: '수신 동의(consent) 필요' }, { status: 400 });
  if (!phone) return Response.json({ sent: false, reason: '수신 번호 필요' }, { status: 400 });

  const templateCode = (TEMPLATE[type] || TEMPLATE.recommendation)();
  const endpoint = process.env.ALIMTALK_API_URL;
  const apiKey = process.env.ALIMTALK_API_KEY;
  const senderKey = process.env.KAKAO_SENDER_KEY;

  if (!endpoint || !apiKey || !templateCode) {
    return Response.json({
      sent: false, source: 'unconfigured',
      reason: '알림톡 미설정 — ALIMTALK_API_URL·ALIMTALK_API_KEY·KAKAO_SENDER_KEY·KAKAO_TEMPLATE_* 설정 후 발송.',
    });
  }

  try {
    // 발신대행사 공통 형식(대행사별 필드명은 ALIMTALK_API_URL 대행사 규격에 맞춰 조정)
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ senderKey, templateCode, recipientList: [{ recipientNo: phone, templateParameter: args }] }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error('alimtalk ' + res.status);
    return Response.json({ sent: true, source: 'alimtalk', provider_response: data });
  } catch (e) {
    return Response.json({ sent: false, source: 'error', reason: e.message }, { status: 502 });
  }
}
