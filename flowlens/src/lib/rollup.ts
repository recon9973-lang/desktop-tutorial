import { prisma } from "./db";
import type { HeatPoint } from "./metrics";
import type { MovePoint } from "./metrics";

// 격자 해상도 (상대좌표 0~1 → 칸 인덱스)
const COLS = 64;
const ROWS = 100;
const CLICK_TYPES = ["click", "rage_click", "dead_click", "cta_click"];

function bin(v: number, n: number): number {
  let i = Math.floor(v * n);
  if (i < 0) i = 0;
  if (i >= n) i = n - 1;
  return i;
}

type ClickCell = { c: number; r: number; d: number };

function parseClick(json?: string | null): Map<string, ClickCell> {
  const m = new Map<string, ClickCell>();
  if (!json) return m;
  try {
    const g = JSON.parse(json);
    for (const [i, j, c, r, d] of g.cells) m.set(`${i},${j}`, { c, r, d });
  } catch {
    /* 무시 */
  }
  return m;
}
function serializeClick(m: Map<string, ClickCell>): string {
  const cells = [...m.entries()].map(([k, v]) => {
    const [i, j] = k.split(",").map(Number);
    return [i, j, v.c, v.r, v.d];
  });
  return JSON.stringify({ cols: COLS, rows: ROWS, cells });
}
function parseMove(json?: string | null): Map<string, number> {
  const m = new Map<string, number>();
  if (!json) return m;
  try {
    const g = JSON.parse(json);
    for (const [i, j, n] of g.cells) m.set(`${i},${j}`, n);
  } catch {
    /* 무시 */
  }
  return m;
}
function serializeMove(m: Map<string, number>): string {
  const cells = [...m.entries()].map(([k, n]) => {
    const [i, j] = k.split(",").map(Number);
    return [i, j, n];
  });
  return JSON.stringify({ cols: COLS, rows: ROWS, cells });
}

// 보관기간이 지난(olderThan 이전) 클릭·무브 원시 이벤트를 격자 스냅샷으로 롤업하고 원시를 삭제.
export async function rollupExpiredEvents(siteId: string, olderThan: Date): Promise<{ clickGroups: number; moveGroups: number; deleted: number }> {
  // ---- 클릭 계열 집계 ----
  const clickEvents = await prisma.event.findMany({
    where: { siteId, type: { in: CLICK_TYPES }, ts: { lt: olderThan }, xRel: { not: null }, yRel: { not: null } },
    select: { xRel: true, yRel: true, type: true, path: true, session: { select: { device: true } } },
    take: 200000,
  });
  const clickGroups = new Map<string, Map<string, ClickCell>>(); // "path|device" -> grid
  for (const e of clickEvents) {
    const device = e.session?.device ?? "DESKTOP";
    const gk = `${e.path || "/"}|${device}`;
    let g = clickGroups.get(gk);
    if (!g) { g = new Map(); clickGroups.set(gk, g); }
    const key = `${bin(e.xRel as number, COLS)},${bin(e.yRel as number, ROWS)}`;
    let cell = g.get(key);
    if (!cell) { cell = { c: 0, r: 0, d: 0 }; g.set(key, cell); }
    if (e.type === "rage_click") cell.r++;
    else if (e.type === "dead_click") cell.d++;
    else cell.c++;
  }
  for (const [gk, g] of clickGroups) {
    const [path, device] = gk.split("|");
    const existing = await prisma.heatmapSnapshot.findUnique({ where: { siteId_path_kind_device: { siteId, path, kind: "click", device } } });
    const merged = parseClick(existing?.grid);
    for (const [k, v] of g) {
      const e0 = merged.get(k) || { c: 0, r: 0, d: 0 };
      e0.c += v.c; e0.r += v.r; e0.d += v.d;
      merged.set(k, e0);
    }
    const samples = [...merged.values()].reduce((a, c) => a + c.c + c.r + c.d, 0);
    const grid = serializeClick(merged);
    await prisma.heatmapSnapshot.upsert({
      where: { siteId_path_kind_device: { siteId, path, kind: "click", device } },
      create: { siteId, path, kind: "click", device, grid, samples, periodTo: olderThan },
      update: { grid, samples, periodTo: olderThan },
    });
  }

  // ---- 무브 계열 집계 (밀도) ----
  const moveGroups = new Map<string, Map<string, number>>();
  const addMove = (path: string, device: string, x: number, y: number) => {
    const gk = `${path || "/"}|${device}`;
    let g = moveGroups.get(gk);
    if (!g) { g = new Map(); moveGroups.set(gk, g); }
    const key = `${bin(x, COLS)},${bin(y, ROWS)}`;
    g.set(key, (g.get(key) || 0) + 1);
  };

  // 새 구조: 경로 1줄(MovePath)을 펼쳐 집계
  const movePaths = await prisma.movePath.findMany({
    where: { siteId, ts: { lt: olderThan } },
    select: { path: true, device: true, points: true },
    take: 50000,
  });
  for (const r of movePaths) {
    for (const pair of r.points.split("|")) {
      const c = pair.split(",");
      const x = Number(c[0]) / 1000;
      const y = Number(c[1]) / 1000;
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      addMove(r.path, r.device, x, y);
    }
  }

  // 레거시: 낱개 pointer_sample 이벤트도 함께 집계
  const moveEvents = await prisma.event.findMany({
    where: { siteId, type: "pointer_sample", ts: { lt: olderThan }, xRel: { not: null }, yRel: { not: null } },
    select: { xRel: true, yRel: true, path: true, session: { select: { device: true } } },
    take: 300000,
  });
  for (const e of moveEvents) {
    addMove(e.path || "/", e.session?.device ?? "DESKTOP", e.xRel as number, e.yRel as number);
  }
  for (const [gk, g] of moveGroups) {
    const [path, device] = gk.split("|");
    const existing = await prisma.heatmapSnapshot.findUnique({ where: { siteId_path_kind_device: { siteId, path, kind: "move", device } } });
    const merged = parseMove(existing?.grid);
    for (const [k, n] of g) merged.set(k, (merged.get(k) || 0) + n);
    const samples = [...merged.values()].reduce((a, n) => a + n, 0);
    const grid = serializeMove(merged);
    await prisma.heatmapSnapshot.upsert({
      where: { siteId_path_kind_device: { siteId, path, kind: "move", device } },
      create: { siteId, path, kind: "move", device, grid, samples, periodTo: olderThan },
      update: { grid, samples, periodTo: olderThan },
    });
  }

  // ---- 원시 삭제 (집계 끝난 것만) ----
  const del = await prisma.event.deleteMany({
    where: { siteId, type: { in: [...CLICK_TYPES, "pointer_sample"] }, ts: { lt: olderThan } },
  });
  const delPaths = await prisma.movePath.deleteMany({ where: { siteId, ts: { lt: olderThan } } });

  return { clickGroups: clickGroups.size, moveGroups: moveGroups.size, deleted: del.count + delPaths.count };
}

// 스냅샷 격자를 다시 포인트로 펼친다 (히트맵 재생성용). 셀당 최대 CAP개 포인트.
const CAP = 40;
export async function getSnapshotPoints(siteId: string, path?: string): Promise<{ clicks: HeatPoint[]; moves: MovePoint[] }> {
  const snaps = await prisma.heatmapSnapshot.findMany({ where: { siteId, ...(path ? { path } : {}) } });
  const clicks: HeatPoint[] = [];
  const moves: MovePoint[] = [];
  let moveSeq = 0;
  for (const s of snaps) {
    if (s.kind === "click") {
      const m = parseClick(s.grid);
      for (const [k, v] of m) {
        const [i, j] = k.split(",").map(Number);
        const x = (i + 0.5) / COLS;
        const y = (j + 0.5) / ROWS;
        const emit = (type: string, count: number) => {
          const n = Math.min(count, CAP);
          for (let t = 0; t < n; t++) clicks.push({ x, y, type, device: s.device, label: null });
        };
        emit("click", v.c);
        emit("rage_click", v.r);
        emit("dead_click", v.d);
      }
    } else {
      const m = parseMove(s.grid);
      for (const [k, n0] of m) {
        const [i, j] = k.split(",").map(Number);
        const x = (i + 0.5) / COLS;
        const y = (j + 0.5) / ROWS;
        const n = Math.min(n0, CAP);
        // 각 포인트에 고유 세션 → 무브맵에서 선 없이 점(밀도)만 표시
        for (let t = 0; t < n; t++) moves.push({ x, y, device: s.device, session: `snap-${moveSeq++}` });
      }
    }
  }
  return { clicks, moves };
}
