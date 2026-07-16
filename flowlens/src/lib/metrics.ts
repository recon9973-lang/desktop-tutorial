import { prisma } from "./db";

export type SiteMetrics = {
  sessions: number;
  bounceRate: number; // %
  avgScroll: number; // %
  scrollReach: { p25: number; p50: number; p75: number; p90: number }; // 각 지점 도달 세션 비율 %
  device: { MOBILE: number; DESKTOP: number; TABLET: number; mobilePct: number };
  channel: Record<string, number>;
  clicks: number;
  rageClicks: number;
  deadClicks: number;
  deadClickRate: number; // %
  ctaViewRate: number; // %
  formStarts: number;
  formSubmits: number;
  formCompletionRate: number; // %
  conversions: number;
};

export type DateRange = { from?: Date; to?: Date };

// 사이트 핵심 지표 집계. range를 주면 해당 기간(세션 startedAt / 이벤트 ts 기준)만 집계.
export async function getSiteMetrics(siteId: string, range?: DateRange): Promise<SiteMetrics> {
  const tsFilter = range ? { gte: range.from, lt: range.to } : undefined;
  const sWhere = { siteId, ...(tsFilter ? { startedAt: tsFilter } : {}) };
  const eWhere = { siteId, ...(tsFilter ? { ts: tsFilter } : {}) };

  const [sessions, bounces, sessAgg, deviceGroups, channelGroups, typeGroups] = await Promise.all([
    prisma.session.count({ where: sWhere }),
    prisma.session.count({ where: { ...sWhere, isBounce: true } }),
    prisma.session.aggregate({ where: sWhere, _avg: { maxScrollPct: true } }),
    prisma.session.groupBy({ by: ["device"], where: sWhere, _count: true }),
    prisma.session.groupBy({ by: ["channel"], where: sWhere, _count: true }),
    prisma.event.groupBy({ by: ["type"], where: eWhere, _count: true }),
  ]);

  const [r25, r50, r75, r90] = await Promise.all([
    prisma.session.count({ where: { ...sWhere, maxScrollPct: { gte: 25 } } }),
    prisma.session.count({ where: { ...sWhere, maxScrollPct: { gte: 50 } } }),
    prisma.session.count({ where: { ...sWhere, maxScrollPct: { gte: 75 } } }),
    prisma.session.count({ where: { ...sWhere, maxScrollPct: { gte: 90 } } }),
  ]);

  const typeCount = (t: string) => typeGroups.find((g) => g.type === t)?._count ?? 0;
  const clicks = typeCount("click");
  const rageClicks = typeCount("rage_click");
  const deadClicks = typeCount("dead_click");
  const pageViews = typeCount("page_view") || 1;
  const ctaViews = typeCount("cta_view");
  const conversions = typeCount("conversion");

  // 폼 시작/제출 (세션 단위 근사)
  const [formFocusSessions, formSubmitSessions] = await Promise.all([
    prisma.event.findMany({ where: { ...eWhere, type: "form_focus" }, distinct: ["sessionId"], select: { sessionId: true } }),
    prisma.event.findMany({ where: { ...eWhere, type: "form_submit" }, distinct: ["sessionId"], select: { sessionId: true } }),
  ]);
  const formStarts = formFocusSessions.length;
  const formSubmits = formSubmitSessions.length;

  const dev = { MOBILE: 0, DESKTOP: 0, TABLET: 0 };
  deviceGroups.forEach((g) => {
    if (g.device in dev) (dev as Record<string, number>)[g.device] = g._count;
  });
  const channel: Record<string, number> = {};
  channelGroups.forEach((g) => (channel[g.channel] = g._count));

  const totalClicks = clicks + rageClicks + deadClicks;
  const pct = (n: number, d: number) => (d > 0 ? Math.round((n / d) * 100) : 0);

  return {
    sessions,
    bounceRate: pct(bounces, sessions),
    avgScroll: Math.round(sessAgg._avg.maxScrollPct ?? 0),
    scrollReach: { p25: pct(r25, sessions), p50: pct(r50, sessions), p75: pct(r75, sessions), p90: pct(r90, sessions) },
    device: { ...dev, mobilePct: pct(dev.MOBILE, sessions) },
    channel,
    clicks,
    rageClicks,
    deadClicks,
    deadClickRate: pct(deadClicks, totalClicks),
    ctaViewRate: Math.min(100, pct(ctaViews, pageViews)),
    formStarts,
    formSubmits,
    formCompletionRate: pct(formSubmits, formStarts),
    conversions,
  };
}

export type HeatPoint = { x: number; y: number; type: string; device: string; label: string | null; dir?: string };

// 히트맵용 클릭 좌표 (디바이스·라벨 포함). path 지정 시 해당 페이지만. range 지정 시 기간 필터.
export async function getHeatmapPoints(siteId: string, path?: string, limit = 4000, range?: DateRange): Promise<HeatPoint[]> {
  const events = await prisma.event.findMany({
    where: {
      siteId,
      type: { in: ["click", "rage_click", "dead_click", "cta_click"] },
      xRel: { not: null },
      yRel: { not: null },
      ...(path ? { path } : {}),
      ...(range ? { ts: { gte: range.from, lt: range.to } } : {}),
    },
    select: { xRel: true, yRel: true, type: true, targetLabel: true, session: { select: { device: true } } },
    take: limit,
    orderBy: { ts: "desc" },
  });
  return events.map((e) => ({
    x: e.xRel as number,
    y: e.yRel as number,
    type: e.type,
    device: e.session?.device ?? "DESKTOP",
    label: e.targetLabel,
  }));
}

// 무브맵 포인터 샘플. 궤적(선)을 그리려면 세션별·시간순 정렬이 필요.
export type MovePoint = { x: number; y: number; device: string; session: string };
export async function getMovePoints(siteId: string, path?: string, limit = 8000, range?: DateRange): Promise<MovePoint[]> {
  const out: MovePoint[] = [];

  // 새 방식: 세션·페이지별 "경로 1줄"을 펼친다 (저장 최적화 구조)
  const rows = await prisma.movePath.findMany({
    where: {
      siteId,
      ...(path ? { path } : {}),
      ...(range ? { ts: { gte: range.from, lt: range.to } } : {}),
    },
    select: { sessionId: true, device: true, points: true },
    take: 3000,
    orderBy: [{ sessionId: "asc" }, { ts: "asc" }], // 세션별 시간순 → 궤적 연결용
  });
  for (const r of rows) {
    for (const pair of r.points.split("|")) {
      const c = pair.split(",");
      const x = Number(c[0]) / 1000;
      const y = Number(c[1]) / 1000;
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      out.push({ x, y, device: r.device, session: r.sessionId });
      if (out.length >= limit) return out;
    }
  }

  // 레거시 호환: 예전에 낱개로 저장된 pointer_sample 이벤트도 함께 표시
  const legacy = await prisma.event.findMany({
    where: {
      siteId,
      type: "pointer_sample",
      xRel: { not: null },
      yRel: { not: null },
      ...(path ? { path } : {}),
      ...(range ? { ts: { gte: range.from, lt: range.to } } : {}),
    },
    select: { xRel: true, yRel: true, sessionId: true, session: { select: { device: true } } },
    take: Math.max(0, limit - out.length),
    orderBy: [{ sessionId: "asc" }, { ts: "asc" }],
  });
  for (const e of legacy) {
    out.push({ x: e.xRel as number, y: e.yRel as number, device: e.session?.device ?? "DESKTOP", session: e.sessionId });
  }
  return out;
}

// 모바일 제스처 좌표 (double_tap / zoom / swipe). meta에서 방향(dir) 파싱.
export async function getGesturePoints(siteId: string, path?: string, limit = 4000): Promise<HeatPoint[]> {
  const events = await prisma.event.findMany({
    where: {
      siteId,
      type: { in: ["double_tap", "zoom", "swipe"] },
      xRel: { not: null },
      yRel: { not: null },
      ...(path ? { path } : {}),
    },
    select: { xRel: true, yRel: true, type: true, meta: true, session: { select: { device: true } } },
    take: limit,
    orderBy: { ts: "desc" },
  });
  return events.map((e) => {
    let dir: string | undefined;
    try {
      dir = JSON.parse(e.meta || "{}").dir;
    } catch {
      /* 무시 */
    }
    return { x: e.xRel as number, y: e.yRel as number, type: e.type, device: e.session?.device ?? "MOBILE", label: null, dir };
  });
}

// 스크롤 도달 밴드(0~100%, 10% 단위)와 평균 폴드. 확장 오버레이용. range로 기간 필터.
export async function getScrollBands(siteId: string, range?: DateRange): Promise<{ bands: { from: number; to: number; pct: number }[]; avgFold: number }> {
  const tsFilter = range ? { gte: range.from, lt: range.to } : undefined;
  const [sessions, foldAgg] = await Promise.all([
    prisma.session.findMany({ where: { siteId, ...(tsFilter ? { startedAt: tsFilter } : {}) }, select: { maxScrollPct: true }, take: 8000 }),
    prisma.event.aggregate({ where: { siteId, vh: { not: null }, ...(tsFilter ? { ts: tsFilter } : {}) }, _avg: { vh: true } }),
  ]);
  const total = sessions.length || 1;
  const bands = [];
  for (let d = 0; d < 100; d += 10) {
    const reached = sessions.filter((s) => s.maxScrollPct >= d).length;
    bands.push({ from: d, to: d + 10, pct: Math.round((reached / total) * 100) });
  }
  return { bands, avgFold: Math.round(foldAgg._avg.vh ?? 800) };
}

// 스크롤맵: 세션별 최대 스크롤 도달(%)과 디바이스 + 평균 폴드(첫 화면 높이 px).
export async function getScrollData(siteId: string): Promise<{ sessions: { device: string; maxScrollPct: number }[]; avgFold: number }> {
  const [sessions, foldAgg] = await Promise.all([
    prisma.session.findMany({ where: { siteId }, select: { device: true, maxScrollPct: true }, take: 5000 }),
    prisma.event.aggregate({ where: { siteId, vh: { not: null } }, _avg: { vh: true } }),
  ]);
  return { sessions, avgFold: Math.round(foldAgg._avg.vh ?? 800) };
}

// 사이트에서 수집된 페이지 경로 목록 (히트맵 페이지 선택용)
export async function getSitePaths(siteId: string): Promise<{ path: string; count: number }[]> {
  const groups = await prisma.event.groupBy({
    by: ["path"],
    where: { siteId, type: "page_view" },
    _count: true,
    orderBy: { _count: { path: "desc" } },
    take: 20,
  });
  return groups.map((g) => ({ path: g.path, count: g._count }));
}

// ---- 퍼널 분석 ----
export type FunnelStep = { key: string; label: string; sessions: number; pctOfTop: number; dropFromPrev: number };

// 이상적 전환 경로 퍼널. 각 단계는 "이전 단계를 모두 통과한(누적 AND) 세션 수"로
// 정의하므로 항상 단조 감소한다.
export async function getFunnel(siteId: string): Promise<FunnelStep[]> {
  const [sessions, events] = await Promise.all([
    prisma.session.findMany({ where: { siteId }, select: { id: true, maxScrollPct: true } }),
    prisma.event.findMany({ where: { siteId }, select: { sessionId: true, type: true } }),
  ]);

  const typesBySession = new Map<string, Set<string>>();
  for (const e of events) {
    let s = typesBySession.get(e.sessionId);
    if (!s) typesBySession.set(e.sessionId, (s = new Set()));
    s.add(e.type);
  }

  const has = (id: string, types: string[]) => {
    const set = typesBySession.get(id);
    return !!set && types.some((t) => set.has(t));
  };

  // 누적 조건 (뒤로 갈수록 조건이 추가되어 세션 집합이 좁아짐)
  const steps: { key: string; label: string; pred: (s: { id: string; maxScrollPct: number }) => boolean }[] = [
    { key: "visit", label: "방문 (세션)", pred: () => true },
    { key: "scroll25", label: "콘텐츠 확인 (스크롤 25%+)", pred: (s) => s.maxScrollPct >= 25 },
    { key: "scroll50", label: "몰입 (스크롤 50%+)", pred: (s) => s.maxScrollPct >= 50 },
    { key: "engage", label: "클릭/행동", pred: (s) => has(s.id, ["click", "cta_click", "rage_click"]) },
    { key: "conversion", label: "전환", pred: (s) => has(s.id, ["conversion", "form_submit"]) },
  ];

  const counts: number[] = [];
  for (let i = 0; i < steps.length; i++) {
    const preds = steps.slice(0, i + 1).map((s) => s.pred);
    counts.push(sessions.filter((s) => preds.every((p) => p(s))).length);
  }

  const top = counts[0] || 1;
  return steps.map((s, i) => ({
    key: s.key,
    label: s.label,
    sessions: counts[i],
    pctOfTop: Math.round((counts[i] / top) * 100),
    dropFromPrev: i === 0 ? 0 : Math.max(0, Math.round((1 - counts[i] / (counts[i - 1] || 1)) * 100)),
  }));
}

// ---- 개선 전/후 비교 ----
export type Comparison = {
  prev: SiteMetrics;
  curr: SiteMetrics;
  prevLabel: string;
  currLabel: string;
};

// 최근 N일 vs 그 이전 N일 비교. 기본 14일.
export async function getComparison(siteId: string, days = 14): Promise<Comparison> {
  const now = new Date();
  const mid = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  const start = new Date(now.getTime() - days * 2 * 24 * 60 * 60 * 1000);

  const [prev, curr] = await Promise.all([
    getSiteMetrics(siteId, { from: start, to: mid }),
    getSiteMetrics(siteId, { from: mid, to: now }),
  ]);
  return { prev, curr, prevLabel: `이전 ${days}일`, currLabel: `최근 ${days}일` };
}
