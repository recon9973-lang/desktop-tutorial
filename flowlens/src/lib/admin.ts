import { getCurrentUser } from "./session";

// 운영자(전체 관리자) 판정 — 반드시 fail-closed.
// ADMIN_EMAILS(쉼표 구분 이메일 화이트리스트)에 든 이메일 + 유효 세션이 둘 다 있어야 관리자다.
// 이 앱은 대행사 격리(멀티테넌시)가 원칙이라 "전체를 보는 권한"은 오직 이 경로로만 생긴다.
// ADMIN_EMAILS 미설정 시 관리자 기능은 통째로 비활성(아무도 접근 못 함).

function adminEmails(): Set<string> {
  const raw = process.env.ADMIN_EMAILS || "";
  return new Set(
    raw
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
}

export function isAdminEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const set = adminEmails();
  if (set.size === 0) return false; // 화이트리스트 미설정 → 전면 비활성
  return set.has(email.toLowerCase());
}

// 현재 요청자가 운영자면 user를 반환, 아니면 null. 서버에서만 호출.
export async function getAdminUser() {
  const user = await getCurrentUser();
  if (!user) return null;
  if (!isAdminEmail(user.email)) return null;
  return user;
}
