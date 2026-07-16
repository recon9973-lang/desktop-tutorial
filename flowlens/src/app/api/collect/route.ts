import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { hostAllowed, hostFromHeaders, sanitizeUrl, sanitizePath, sanitizeReferrer, sanitizeLabel, sanitizeMeta } from "@/lib/sanitize";
import { getPlan } from "@/lib/plans";

// 외부 고객 사이트에서 호출되므로 CORS 허용.
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS });
}

type IncomingEvent = {
  type: string;
  url?: string;
  path?: string;
  vw?: number;
  vh?: number;
  xRel?: number;
  yRel?: number;
  scrollPct?: number;
  targetLabel?: string;
  meta?: string;
  pts?: string; // move_path 전용: "x,y|x,y|..." 압축 좌표
  ts?: number;
};

// 이동 경로 좌표 검증: 0~1000 정수쌍만 허용(숫자·쉼표·파이프 외 문자 거부). 개인정보 없음.
function sanitizePoints(raw: unknown): { points: string; count: number } | null {
  if (typeof raw !== "string" || !raw) return null;
  const s = raw.slice(0, 8000); // 최대 약 800점
  if (!/^[0-9,|]+$/.test(s)) return null;
  const out: string[] = [];
  for (const pair of s.split("|")) {
    const [a, b] = pair.split(",");
    const x = parseInt(a, 10);
    const y = parseInt(b, 10);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    out.push(`${Math.min(1000, Math.max(0, x))},${Math.min(1000, Math.max(0, y))}`);
  }
  if (!out.length) return null;
  return { points: out.join("|"), count: out.length };
}

export async function POST(req: NextRequest) {
  let body: {
    site?: string;
    session?: string;
    device?: string;
    referrer?: string;
    channel?: string;
    events?: IncomingEvent[];
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "bad json" }, { status: 400, headers: CORS });
  }

  const { site: siteKey, session: sessionKey, events } = body;
  if (!siteKey || !sessionKey || !Array.isArray(events) || events.length === 0) {
    return NextResponse.json({ ok: false, error: "missing fields" }, { status: 400, headers: CORS });
  }

  const site = await prisma.site.findUnique({
    where: { siteKey },
    include: { client: { select: { agencyId: true, agency: { select: { plan: true, trialEndsAt: true, overageStop: true } } } } },
  });
  // 등록되지 않은 siteKey는 조용히 무시 (정보 노출 방지)
  if (!site) return NextResponse.json({ ok: true }, { status: 202, headers: CORS });

  // 체험 만료 시 수집 중단 (읽기는 계속 가능)
  const agency = site.client.agency;
  if (agency.trialEndsAt && Date.now() > agency.trialEndsAt.getTime()) {
    return NextResponse.json({ ok: true, stopped: "trial" }, { status: 202, headers: CORS });
  }

  // 도메인 검증 (법무 5.1): Origin/Referer 호스트가 등록 도메인과 일치해야 수집.
  const reqHost = hostFromHeaders(req.headers.get("origin"), req.headers.get("referer"));
  if (!hostAllowed(reqHost, site.domain)) {
    return NextResponse.json({ ok: true }, { status: 202, headers: CORS }); // 조용히 무시
  }

  const device = ["MOBILE", "DESKTOP", "TABLET"].includes(body.device || "") ? (body.device as string) : "DESKTOP";
  const channel = (body.channel || "direct").slice(0, 20);
  const referrer = sanitizeReferrer(body.referrer || "");

  // 세션 upsert
  let session = await prisma.session.findFirst({ where: { siteId: site.id, sessionKey } });
  const maxScrollInBatch = events.reduce((mx, e) => Math.max(mx, e.scrollPct ?? 0), 0);
  const pageViewsInBatch = events.filter((e) => e.type === "page_view").length;
  const hasEngagement = events.some((e) => ["click", "cta_click", "conversion", "form_submit"].includes(e.type));

  if (!session) {
    // 새 세션 = 사용량 1 증가. 한도 초과 시 요금제에 따라 정지하거나 종량으로 계속.
    const plan = getPlan(agency.plan);
    const ym = new Date().toISOString().slice(0, 7); // "2026-07"
    const usage = await prisma.usageMonth.findUnique({
      where: { agencyId_ym: { agencyId: site.client.agencyId, ym } },
    });
    const used = usage?.sessions ?? 0;
    if (used >= plan.sessionsPerMonth && (plan.overagePer10k === 0 || agency.overageStop)) {
      // 무료(종량 없음)거나 "초과 시 정지"를 선택한 경우 → 새 세션 수집 중단
      return NextResponse.json({ ok: true, stopped: "quota" }, { status: 202, headers: CORS });
    }

    session = await prisma.session.create({
      data: {
        siteId: site.id,
        sessionKey,
        device,
        channel,
        referrer,
        maxScrollPct: Math.min(100, maxScrollInBatch),
        pageCount: Math.max(1, pageViewsInBatch),
        isBounce: !(pageViewsInBatch > 1 || hasEngagement),
      },
    });
    await prisma.usageMonth.upsert({
      where: { agencyId_ym: { agencyId: site.client.agencyId, ym } },
      create: { agencyId: site.client.agencyId, ym, sessions: 1 },
      update: { sessions: { increment: 1 } },
    });
  } else {
    const newPageCount = session.pageCount + pageViewsInBatch;
    session = await prisma.session.update({
      where: { id: session.id },
      data: {
        lastEventAt: new Date(),
        maxScrollPct: Math.max(session.maxScrollPct, Math.min(100, maxScrollInBatch)),
        pageCount: newPageCount,
        isBounce: session.isBounce && !(newPageCount > 1 || hasEngagement),
      },
    });
  }

  // 마우스 이동 경로는 낱개 이벤트가 아니라 "경로 1줄"로 별도 저장 (저장량 대폭 절감)
  const moveEvents = events.filter((e) => e.type === "move_path");
  const normalEvents = events.filter((e) => e.type !== "move_path");
  if (moveEvents.length) {
    const rows = moveEvents
      .slice(0, 20)
      .map((e) => {
        const p = sanitizePoints(e.pts);
        if (!p) return null;
        return {
          siteId: site.id,
          sessionId: session!.id,
          device,
          path: sanitizePath(e.path || "/"),
          points: p.points,
          count: p.count,
          ts: e.ts ? new Date(e.ts) : new Date(),
        };
      })
      .filter(Boolean) as { siteId: string; sessionId: string; device: string; path: string; points: string; count: number; ts: Date }[];
    if (rows.length) await prisma.movePath.createMany({ data: rows });
  }

  // 이벤트 저장 (좌표 클램프, 라벨 길이 제한 — 방어적)
  const clamp01 = (n?: number) => (typeof n === "number" ? Math.min(1, Math.max(0, n)) : null);
  await prisma.event.createMany({
    data: normalEvents.slice(0, 200).map((e) => ({
      siteId: site.id,
      sessionId: session!.id,
      type: String(e.type || "unknown").slice(0, 24),
      url: sanitizeUrl(e.url || ""), // query/hash 제거
      path: sanitizePath(e.path || "/"),
      xRel: clamp01(e.xRel),
      yRel: clamp01(e.yRel),
      vw: typeof e.vw === "number" ? e.vw : null,
      vh: typeof e.vh === "number" ? e.vh : null,
      scrollPct: typeof e.scrollPct === "number" ? Math.min(100, Math.max(0, Math.round(e.scrollPct))) : null,
      targetLabel: sanitizeLabel(e.targetLabel), // 서버 2차 마스킹
      meta: sanitizeMeta(e.meta), // 민감 키 차단 + 값 마스킹 + allowlist
      ts: e.ts ? new Date(e.ts) : new Date(),
    })),
  });

  return NextResponse.json({ ok: true, stored: events.length }, { status: 200, headers: CORS });
}
