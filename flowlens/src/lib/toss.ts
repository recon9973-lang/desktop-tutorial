// 토스페이먼츠 결제 승인(confirm) 서버 로직.
// 클라이언트가 결제 요청 → successUrl로 리다이렉트되며 paymentKey/orderId/amount 전달 →
// 서버가 이 값으로 토스 confirm API를 호출해 최종 승인한다. (금액 위변조 방지)
//
// 키:
//   NEXT_PUBLIC_TOSS_CLIENT_KEY : 클라이언트(공개) 키. 테스트키는 test_ck_... / 라이브는 live_ck_...
//   TOSS_SECRET_KEY             : 서버(비공개) 키. 테스트키는 test_sk_... / 라이브는 live_sk_...
// 토스 개발자센터(https://developers.tosspayments.com)에서 발급. 테스트 모드는 실제 결제가 일어나지 않는다.

const CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm";

export function tossConfigured(): boolean {
  return !!process.env.TOSS_SECRET_KEY && !!process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY;
}

export type ConfirmResult =
  | { ok: true; data: { orderId: string; totalAmount: number; method?: string; approvedAt?: string } }
  | { ok: false; code: string; message: string };

export async function confirmPayment(paymentKey: string, orderId: string, amount: number): Promise<ConfirmResult> {
  const secret = process.env.TOSS_SECRET_KEY;
  if (!secret) return { ok: false, code: "NO_KEY", message: "TOSS_SECRET_KEY가 설정되지 않았습니다." };

  // Basic 인증: base64(secretKey + ":")
  const auth = Buffer.from(`${secret}:`).toString("base64");

  try {
    const res = await fetch(CONFIRM_URL, {
      method: "POST",
      headers: { Authorization: `Basic ${auth}`, "Content-Type": "application/json" },
      body: JSON.stringify({ paymentKey, orderId, amount }),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, code: data.code ?? "ERROR", message: data.message ?? "결제 승인 실패" };
    return { ok: true, data };
  } catch (e) {
    return { ok: false, code: "NETWORK", message: "결제 서버 통신 오류" };
  }
}
