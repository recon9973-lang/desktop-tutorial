// 보관기간 초과 원본 이벤트를 "집계 스냅샷으로 롤업 후 삭제" (법무 검토 4.10 / 5 반영).
// 운영 cron: 예) 매일 새벽 → `node scripts/cleanup.mjs`
// 클릭·무브 이벤트는 격자 스냅샷(HeatmapSnapshot)으로 압축 저장 → 히트맵 재생성 유지, 용량 급감.
// 그 외 이벤트(page_view/scroll 등)는 삭제.

import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

const COLS = 64;
const ROWS = 100;
const CLICK_TYPES = ["click", "rage_click", "dead_click", "cta_click"];
const bin = (v, n) => Math.max(0, Math.min(n - 1, Math.floor(v * n)));

const parseClick = (json) => {
  const m = new Map();
  if (!json) return m;
  try { for (const [i, j, c, r, d] of JSON.parse(json).cells) m.set(`${i},${j}`, { c, r, d }); } catch {}
  return m;
};
const serClick = (m) => JSON.stringify({ cols: COLS, rows: ROWS, cells: [...m.entries()].map(([k, v]) => { const [i, j] = k.split(",").map(Number); return [i, j, v.c, v.r, v.d]; }) });
const parseMove = (json) => {
  const m = new Map();
  if (!json) return m;
  try { for (const [i, j, n] of JSON.parse(json).cells) m.set(`${i},${j}`, n); } catch {}
  return m;
};
const serMove = (m) => JSON.stringify({ cols: COLS, rows: ROWS, cells: [...m.entries()].map(([k, n]) => { const [i, j] = k.split(",").map(Number); return [i, j, n]; }) });

async function rollup(siteId, olderThan) {
  // 클릭
  const clicks = await prisma.event.findMany({
    where: { siteId, type: { in: CLICK_TYPES }, ts: { lt: olderThan }, xRel: { not: null }, yRel: { not: null } },
    select: { xRel: true, yRel: true, type: true, path: true, session: { select: { device: true } } },
    take: 200000,
  });
  const cg = new Map();
  for (const e of clicks) {
    const gk = `${e.path || "/"}|${e.session?.device ?? "DESKTOP"}`;
    let g = cg.get(gk); if (!g) { g = new Map(); cg.set(gk, g); }
    const key = `${bin(e.xRel, COLS)},${bin(e.yRel, ROWS)}`;
    let c = g.get(key); if (!c) { c = { c: 0, r: 0, d: 0 }; g.set(key, c); }
    if (e.type === "rage_click") c.r++; else if (e.type === "dead_click") c.d++; else c.c++;
  }
  for (const [gk, g] of cg) {
    const [path, device] = gk.split("|");
    const ex = await prisma.heatmapSnapshot.findUnique({ where: { siteId_path_kind_device: { siteId, path, kind: "click", device } } });
    const m = parseClick(ex?.grid);
    for (const [k, v] of g) { const e0 = m.get(k) || { c: 0, r: 0, d: 0 }; e0.c += v.c; e0.r += v.r; e0.d += v.d; m.set(k, e0); }
    const samples = [...m.values()].reduce((a, c) => a + c.c + c.r + c.d, 0);
    const grid = serClick(m);
    await prisma.heatmapSnapshot.upsert({ where: { siteId_path_kind_device: { siteId, path, kind: "click", device } }, create: { siteId, path, kind: "click", device, grid, samples, periodTo: olderThan }, update: { grid, samples, periodTo: olderThan } });
  }
  // 무브
  const mg = new Map();
  const addMove = (path, device, x, y) => {
    const gk = `${path || "/"}|${device}`;
    let g = mg.get(gk); if (!g) { g = new Map(); mg.set(gk, g); }
    const key = `${bin(x, COLS)},${bin(y, ROWS)}`;
    g.set(key, (g.get(key) || 0) + 1);
  };
  // 새 구조: 경로 1줄 펼쳐 집계
  const movePaths = await prisma.movePath.findMany({
    where: { siteId, ts: { lt: olderThan } },
    select: { path: true, device: true, points: true },
    take: 50000,
  });
  for (const r of movePaths) {
    for (const pair of r.points.split("|")) {
      const c = pair.split(",");
      const x = Number(c[0]) / 1000, y = Number(c[1]) / 1000;
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      addMove(r.path, r.device, x, y);
    }
  }
  // 레거시 낱개 이벤트도 집계
  const moves = await prisma.event.findMany({
    where: { siteId, type: "pointer_sample", ts: { lt: olderThan }, xRel: { not: null }, yRel: { not: null } },
    select: { xRel: true, yRel: true, path: true, session: { select: { device: true } } },
    take: 300000,
  });
  for (const e of moves) addMove(e.path || "/", e.session?.device ?? "DESKTOP", e.xRel, e.yRel);
  for (const [gk, g] of mg) {
    const [path, device] = gk.split("|");
    const ex = await prisma.heatmapSnapshot.findUnique({ where: { siteId_path_kind_device: { siteId, path, kind: "move", device } } });
    const m = parseMove(ex?.grid);
    for (const [k, n] of g) m.set(k, (m.get(k) || 0) + n);
    const samples = [...m.values()].reduce((a, n) => a + n, 0);
    const grid = serMove(m);
    await prisma.heatmapSnapshot.upsert({ where: { siteId_path_kind_device: { siteId, path, kind: "move", device } }, create: { siteId, path, kind: "move", device, grid, samples, periodTo: olderThan }, update: { grid, samples, periodTo: olderThan } });
  }
  return { clickGroups: cg.size, moveGroups: mg.size };
}

async function main() {
  const sites = await prisma.site.findMany({ select: { id: true, name: true, retentionDays: true } });
  let totalDeleted = 0;

  for (const site of sites) {
    const cutoff = new Date(Date.now() - site.retentionDays * 24 * 60 * 60 * 1000);
    // 1) 클릭·무브 롤업(스냅샷) 후
    const r = await rollup(site.id, cutoff);
    if (r.clickGroups || r.moveGroups) console.log(`  ${site.name}: 스냅샷 롤업 (click ${r.clickGroups} · move ${r.moveGroups} 그룹)`);
    // 2) 보관기간 초과 원시 데이터 삭제 (이벤트 + 이동 경로)
    const res = await prisma.event.deleteMany({ where: { siteId: site.id, ts: { lt: cutoff } } });
    const resPath = await prisma.movePath.deleteMany({ where: { siteId: site.id, ts: { lt: cutoff } } });
    const n = res.count + resPath.count;
    if (n > 0) { console.log(`  ${site.name}: 보관 ${site.retentionDays}일 초과 데이터 ${n}건 삭제`); totalDeleted += n; }
    // 3) 빈 세션 정리
    const emptySessions = await prisma.session.deleteMany({ where: { siteId: site.id, lastEventAt: { lt: cutoff }, events: { none: {} } } });
    if (emptySessions.count > 0) console.log(`  ${site.name}: 빈 세션 ${emptySessions.count}건 삭제`);
  }

  console.log(`✅ cleanup 완료 — 롤업 후 총 이벤트 ${totalDeleted}건 삭제`);
}

main()
  .catch((e) => { console.error("cleanup 실패:", e); process.exit(1); })
  .finally(() => prisma.$disconnect());
