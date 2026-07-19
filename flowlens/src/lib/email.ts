// 트랜잭션 이메일 발송 (Resend REST API — 별도 패키지 없이 fetch로 호출).
// ⚠️ RESEND_API_KEY가 없으면 조용히 no-op 한다 → 키 설정 전에도 앱이 절대 깨지지 않는다.
// 활성화: (1) resend.com 가입·도메인 인증 (2) 환경변수 RESEND_API_KEY, EMAIL_FROM 설정.

type SendArgs = { to: string; subject: string; html: string };

export async function sendEmail({ to, subject, html }: SendArgs): Promise<{ ok: boolean; skipped?: boolean; error?: string }> {
  const key = process.env.RESEND_API_KEY;
  const from = process.env.EMAIL_FROM || "FlowLens <onboarding@flow.seokorea.org>";
  if (!key) return { ok: false, skipped: true }; // 미설정 → 발송하지 않음(정상)
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ from, to, subject, html }),
    });
    if (!r.ok) return { ok: false, error: `resend ${r.status}` };
    return { ok: true };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

// ---- 템플릿 (인라인 스타일 — 메일 클라이언트 호환) ----
const WRAP = (inner: string) =>
  `<div style="font-family:-apple-system,Segoe UI,Malgun Gothic,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#1a1917;line-height:1.6">
    <div style="font-weight:800;font-size:18px;margin-bottom:16px">FlowLens</div>
    ${inner}
    <hr style="border:none;border-top:1px solid #e6e6e6;margin:24px 0"/>
    <div style="font-size:12px;color:#a39e98">주식회사 베놈 · flow.seokorea.org · venomad@naver.com</div>
  </div>`;

export function welcomeHtml(name: string): string {
  return WRAP(
    `<h2 style="font-size:20px;margin:0 0 10px">${escapeHtml(name)}님, 환영합니다 🎉</h2>
     <p>FlowLens 무료 체험이 시작됐습니다. 첫 사이트에 추적 코드 한 줄만 넣으면 방문자 행동이 히트맵으로 보입니다.</p>
     <p style="margin:18px 0"><a href="https://flow.seokorea.org/sites/new" style="background:#0075de;color:#fff;text-decoration:none;padding:11px 20px;border-radius:8px;font-weight:700;display:inline-block">첫 사이트 등록하기</a></p>
     <p style="font-size:13px;color:#615d59">설치가 어려우면 설치 화면의 &lsquo;설치 요청 메일&rsquo; 버튼으로 담당자에게 부탁할 수 있어요.</p>`
  );
}

export function trialReminderHtml(name: string, daysLeft: number): string {
  return WRAP(
    `<h2 style="font-size:20px;margin:0 0 10px">무료 체험이 ${daysLeft}일 남았어요</h2>
     <p>${escapeHtml(name)}님, 체험이 끝나면 새 데이터 수집이 멈춥니다. 요금제를 선택하면 끊김 없이 이어집니다.</p>
     <p style="margin:18px 0"><a href="https://flow.seokorea.org/billing" style="background:#0075de;color:#fff;text-decoration:none;padding:11px 20px;border-radius:8px;font-weight:700;display:inline-block">요금제 보기</a></p>
     <p style="font-size:13px;color:#615d59">그동안 쌓인 데이터는 보관 기간 동안 유지됩니다.</p>`
  );
}

function escapeHtml(s: string): string {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
}
