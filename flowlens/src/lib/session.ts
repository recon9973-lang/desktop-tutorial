import { cookies } from "next/headers";
import crypto from "crypto";
import { prisma } from "./db";

// MVP용 단순 쿠키 세션.
// 운영에서는 NextAuth/OAuth + 안전한 세션 스토어로 교체할 것.
const COOKIE = "fl_session";
const DEV_SECRET = "dev-only-secret";
const SECRET = process.env.FLOWLENS_SECRET || DEV_SECRET;

// 운영에서는 안전한 시크릿을 강제 (법무 5.5).
// 모듈 로드(빌드) 시점이 아니라 세션 발급(요청) 시점에 검증 → 빌드는 통과, 런타임 보안은 유지.
function assertSecret() {
  if (process.env.NODE_ENV === "production" && (!process.env.FLOWLENS_SECRET || process.env.FLOWLENS_SECRET.includes(DEV_SECRET) || SECRET.length < 16)) {
    throw new Error("[FlowLens] 운영 환경에서는 FLOWLENS_SECRET을 안전한 랜덤 값(16자+)으로 설정해야 합니다.");
  }
}

const SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000;

// 서명 payload에 만료시각을 포함한다.
// (이전에는 userId만 서명해, 쿠키가 한 번 유출되면 영구히 유효했다)
function sign(userId: string) {
  const exp = Date.now() + SESSION_TTL_MS;
  const payload = `${userId}.${exp}`;
  const mac = crypto.createHmac("sha256", SECRET).update(payload).digest("hex").slice(0, 32);
  return `${payload}.${mac}`;
}

function verify(value: string): string | null {
  const parts = value.split(".");
  if (parts.length !== 3) return null;
  const [userId, expStr, mac] = parts;
  const exp = Number(expStr);
  if (!userId || !Number.isFinite(exp)) return null;
  if (Date.now() > exp) return null; // 만료

  const expected = crypto.createHmac("sha256", SECRET).update(`${userId}.${expStr}`).digest("hex").slice(0, 32);
  // 타이밍 공격 방어를 위해 상수시간 비교
  const a = Buffer.from(mac, "utf8");
  const b = Buffer.from(expected, "utf8");
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  return userId;
}

export async function createSession(userId: string) {
  assertSecret();
  const jar = await cookies();
  jar.set(COOKIE, sign(userId), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production", // 운영은 HTTPS 전용 쿠키
    path: "/",
    maxAge: Math.floor(SESSION_TTL_MS / 1000),
  });
}

export async function destroySession() {
  const jar = await cookies();
  jar.delete(COOKIE);
}

// 현재 로그인 유저(+소속 대행사) 반환. 없으면 null.
export async function getCurrentUser() {
  const jar = await cookies();
  const raw = jar.get(COOKIE)?.value;
  if (!raw) return null;
  const userId = verify(raw);
  if (!userId) return null;
  return prisma.user.findUnique({ where: { id: userId }, include: { agency: true } });
}

// 비밀번호 해싱 (scrypt)
export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

export function checkPassword(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(":");
  if (!salt || !hash) return false;
  const test = crypto.scryptSync(password, salt, 64).toString("hex");
  return crypto.timingSafeEqual(Buffer.from(hash, "hex"), Buffer.from(test, "hex"));
}
