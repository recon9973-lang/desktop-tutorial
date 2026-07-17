import crypto from "crypto";
import { prisma } from "./db";
import type { NextRequest } from "next/server";

// 고정 윈도우 rate limit. 서버리스는 인스턴스 간 메모리를 공유하지 않으므로 DB 카운터를 쓴다.
// key 예: "collect:<siteId>:<ipHash>" / "shot:<userId>". 원문 IP는 저장하지 않는다(해시만).

// x-forwarded-for 는 클라이언트가 조작 가능하지만, Vercel은 신뢰 프록시가 맨 앞에 실제 IP를 붙인다.
// 완벽한 신원은 아니어도 무차별 공격의 비용을 크게 올린다.
export function ipHashOf(req: NextRequest): string {
  const ip = (req.headers.get("x-forwarded-for") || "").split(",")[0].trim() || req.headers.get("x-real-ip") || "unknown";
  return crypto
    .createHash("sha256")
    .update(ip + "|" + (process.env.FLOWLENS_SECRET || "dev"))
    .digest("hex")
    .slice(0, 40);
}

export type RateResult = { ok: boolean; remaining: number; retryAfterSec: number };

/**
 * key 에 대해 windowMs 동안 max 회까지 허용. 초과하면 ok:false.
 * 원자적 증가를 위해 upsert 를 쓰되, 윈도우가 지났으면 리셋한다.
 */
export async function rateLimit(key: string, max: number, windowMs: number): Promise<RateResult> {
  const id = crypto.createHash("sha256").update(key).digest("hex").slice(0, 48);
  const now = Date.now();
  try {
    const row = await prisma.rateLimit.findUnique({ where: { id } });
    if (!row || now - row.windowAt.getTime() >= windowMs) {
      // 윈도우 시작(또는 만료 후 리셋)
      await prisma.rateLimit.upsert({
        where: { id },
        create: { id, count: 1, windowAt: new Date(now) },
        update: { count: 1, windowAt: new Date(now) },
      });
      return { ok: true, remaining: max - 1, retryAfterSec: 0 };
    }
    if (row.count >= max) {
      const retryAfterSec = Math.ceil((windowMs - (now - row.windowAt.getTime())) / 1000);
      return { ok: false, remaining: 0, retryAfterSec };
    }
    await prisma.rateLimit.update({ where: { id }, data: { count: { increment: 1 } } });
    return { ok: true, remaining: max - row.count - 1, retryAfterSec: 0 };
  } catch {
    // DB 오류로 rate limit 을 판단할 수 없을 때는 요청을 막지 않는다(가용성 우선).
    // 단, 이 경로가 자주 실패하면 별도 알림이 필요하다.
    return { ok: true, remaining: max, retryAfterSec: 0 };
  }
}
