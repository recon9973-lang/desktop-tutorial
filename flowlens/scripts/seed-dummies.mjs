// 대시보드 검색·목록 테스트용 더미 고객사 10곳(각 사이트 1개 + 가벼운 이벤트) 추가.
// 기존 데모 대행사(그로스랩)에 붙인다. 실행: node scripts/seed-dummies.mjs
import { PrismaClient } from "@prisma/client";
import crypto from "crypto";

const prisma = new PrismaClient();
const rand = (a, b) => a + Math.random() * (b - a);
const randInt = (a, b) => Math.floor(rand(a, b + 1));
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const chance = (p) => Math.random() < p;
const clamp01 = (n) => Math.min(1, Math.max(0, n));
const around = (c, s) => clamp01(c + ((Math.random() + Math.random() + Math.random()) / 3 - 0.5) * s * 2);
const uuid = () => crypto.randomUUID();
const daysAgo = (d) => new Date(Date.now() - d * 24 * 60 * 60 * 1000);

const DUMMIES = [
  { name: "레브잉크 커머스", industry: "ECOMMERCE", domain: "levink.co.kr" },
  { name: "미소가정의학과", industry: "CLINIC", domain: "misoclinic.kr" },
  { name: "코드스테이 학원", industry: "EDU", domain: "codestay.kr" },
  { name: "노바테크 B2B", industry: "B2B", domain: "novatech.io" },
  { name: "그린리프 유기농몰", industry: "ECOMMERCE", domain: "greenleaf.co.kr" },
  { name: "서초바른치과", industry: "CLINIC", domain: "seochobareun.kr" },
  { name: "플로우 요가스튜디오", industry: "ETC", domain: "flowyoga.kr" },
  { name: "픽셀크래프트 에이전시", industry: "B2B", domain: "pixelcraft.kr" },
  { name: "데일리브루 커피", industry: "ECOMMERCE", domain: "dailybrew.co.kr" },
  { name: "한빛어학원", industry: "EDU", domain: "hanbit-lang.kr" },
];

async function main() {
  const agency = await prisma.agency.findFirst({ orderBy: { createdAt: "asc" } });
  if (!agency) throw new Error("대행사가 없습니다. 먼저 npm run db:seed 실행.");
  console.log(`대행사: ${agency.name} 에 더미 ${DUMMIES.length}곳 추가`);

  for (const d of DUMMIES) {
    const client = await prisma.client.create({ data: { name: d.name, industry: d.industry, agencyId: agency.id } });
    const site = await prisma.site.create({ data: { name: `${d.name} 사이트`, domain: d.domain, clientId: client.id } });

    const nSessions = randInt(40, 140);
    const sessionRows = [];
    const eventRows = [];
    const hotspots = [[0.5, 0.12], [0.5, 0.4], [0.82, 0.06], [0.5, 0.6]];

    for (let i = 0; i < nSessions; i++) {
      const sid = uuid();
      const isMobile = chance(0.6);
      const device = isMobile ? "MOBILE" : chance(0.15) ? "TABLET" : "DESKTOP";
      const maxScroll = randInt(15, 100);
      const bounced = chance(0.45);
      const start = daysAgo(rand(0, 30));
      let t = start.getTime();
      const nextTs = () => new Date((t += randInt(500, 6000)));
      const base = { siteId: site.id, sessionId: sid, url: `https://${d.domain}/`, path: "/" };

      eventRows.push({ id: uuid(), ...base, type: "page_view", meta: "{}", ts: nextTs() });
      if (chance(0.5)) eventRows.push({ id: uuid(), ...base, type: "cta_view", targetLabel: "문의하기", meta: "{}", ts: nextTs() });
      let engaged = false;
      const nClicks = bounced ? randInt(0, 2) : randInt(2, 6);
      for (let c = 0; c < nClicks; c++) {
        const h = pick(hotspots);
        const dead = chance(0.06);
        const type = dead ? "dead_click" : chance(0.03) ? "rage_click" : "click";
        if (type === "click") engaged = true;
        eventRows.push({ id: uuid(), ...base, type, xRel: around(h[0], 0.08), yRel: around(h[1], 0.08), scrollPct: randInt(0, maxScroll), targetLabel: pick(["문의하기", "구매하기", "더보기", "예약"]), meta: "{}", ts: nextTs() });
      }
      for (let s = 0; s < randInt(1, 3); s++) eventRows.push({ id: uuid(), ...base, type: "scroll", scrollPct: randInt(0, maxScroll), meta: "{}", ts: nextTs() });
      if (engaged && chance(0.08)) eventRows.push({ id: uuid(), ...base, type: "conversion", targetLabel: "전환", meta: "{}", ts: nextTs() });

      sessionRows.push({ id: sid, siteId: site.id, sessionKey: `dummy_${sid.slice(0, 10)}`, device, channel: pick(["direct", "search", "ad", "social"]), startedAt: start, lastEventAt: new Date(t), maxScrollPct: maxScroll, pageCount: bounced ? 1 : randInt(1, 4), isBounce: bounced && !engaged });
    }
    await prisma.session.createMany({ data: sessionRows });
    for (let i = 0; i < eventRows.length; i += 1000) await prisma.event.createMany({ data: eventRows.slice(i, i + 1000) });
    console.log(`  + ${d.name} (${d.industry}) · 세션 ${sessionRows.length}`);
  }
  console.log("✅ 더미 추가 완료");
}

main().catch((e) => { console.error(e); process.exit(1); }).finally(() => prisma.$disconnect());
