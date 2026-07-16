// FlowLens 시드 데이터 생성기
// 대행사 1곳 → 고객사 2곳 → 사이트 3개 + 사이트별 수백 세션/수천 이벤트를 생성한다.
// 각 사이트는 서로 다른 "문제 프로파일"을 갖게 하여 룰 엔진 제안이 다르게 나오도록 한다.

import { PrismaClient } from "@prisma/client";
import crypto from "crypto";

const prisma = new PrismaClient();

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

const rand = (a, b) => a + Math.random() * (b - a);
const randInt = (a, b) => Math.floor(rand(a, b + 1));
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const chance = (p) => Math.random() < p;
const clamp01 = (n) => Math.min(1, Math.max(0, n));
// 중심 주변 정규분포 근사
function around(center, spread) {
  const g = (Math.random() + Math.random() + Math.random()) / 3 - 0.5;
  return clamp01(center + g * spread * 2);
}
const uuid = () => crypto.randomUUID();
const daysAgo = (d) => new Date(Date.now() - d * 24 * 60 * 60 * 1000);

async function main() {
  console.log("기존 데이터 삭제…");
  await prisma.event.deleteMany();
  await prisma.session.deleteMany();
  await prisma.shareLink.deleteMany();
  await prisma.site.deleteMany();
  await prisma.client.deleteMany();
  await prisma.user.deleteMany();
  await prisma.agency.deleteMany();

  console.log("대행사/유저 생성…");
  const agency = await prisma.agency.create({
    data: { name: "그로스랩", logoText: "GrowthLab", plan: "AGENCY" },
  });
  await prisma.user.createMany({
    data: [
      { email: "owner@growthlab.kr", name: "김대표", role: "OWNER", agencyId: agency.id, passwordHash: hashPassword("demo1234") },
      { email: "member@growthlab.kr", name: "이매니저", role: "MEMBER", agencyId: agency.id, passwordHash: hashPassword("demo1234") },
    ],
  });

  console.log("고객사/사이트 생성…");
  const mood = await prisma.client.create({ data: { name: "무드컬렉션", industry: "ECOMMERCE", agencyId: agency.id } });
  const clinic = await prisma.client.create({ data: { name: "서울스마일치과", industry: "CLINIC", agencyId: agency.id } });

  // 사이트별 문제 프로파일
  const siteDefs = [
    {
      name: "무드컬렉션 자사몰",
      domain: "moodcollection.co.kr",
      clientId: mood.id,
      sessions: 560,
      profile: {
        mobilePct: 0.72, // 모바일 편중
        ctaViewRate: 0.28, // CTA 잘 안 보임 → mobile-cta 규칙
        deadClickRate: 0.09, // 상세페이지 이미지 반복 클릭 → dead-click 규칙
        rage: 0.03,
        scrollProfile: "mid",
        bounce: 0.52,
        form: false,
        paths: ["/", "/product/summer-linen", "/product/knit-vest", "/cart"],
        hotspots: [
          [0.5, 0.12], [0.5, 0.34], [0.5, 0.58], [0.82, 0.06],
        ],
        deadHotspot: [0.5, 0.46], // 상세 이미지 영역
      },
    },
    {
      name: "여름세일 랜딩",
      domain: "moodcollection.co.kr",
      clientId: mood.id,
      sessions: 430,
      profile: {
        mobilePct: 0.64,
        ctaViewRate: 0.55,
        deadClickRate: 0.03,
        rage: 0.02,
        scrollProfile: "low", // 중반 이전 이탈 → scroll-drop 규칙
        bounce: 0.74, // 높은 이탈 → bounce 규칙
        form: false,
        paths: ["/event/summer"],
        hotspots: [[0.5, 0.1], [0.5, 0.2], [0.3, 0.15]],
        deadHotspot: [0.5, 0.3],
      },
    },
    {
      name: "서울스마일치과 예약",
      domain: "seoulsmile.kr",
      clientId: clinic.id,
      sessions: 320,
      profile: {
        mobilePct: 0.58,
        ctaViewRate: 0.62,
        deadClickRate: 0.02,
        rage: 0.02,
        scrollProfile: "high",
        bounce: 0.48,
        form: true, // 예약 폼 이탈 → form-drop 규칙
        formStartRate: 0.55,
        formSubmitRate: 0.22, // 폼 완료율 낮음
        paths: ["/", "/reserve", "/doctors", "/location"],
        hotspots: [[0.5, 0.08], [0.85, 0.05], [0.5, 0.4], [0.3, 0.6]],
        deadHotspot: [0.5, 0.5],
      },
    },
  ];

  for (const def of siteDefs) {
    const site = await prisma.site.create({
      data: { name: def.name, domain: def.domain, clientId: def.clientId, retentionDays: 90 },
    });
    console.log(`  → ${def.name} (siteKey: ${site.siteKey}) 이벤트 생성…`);

    const p = def.profile;
    const sessionRows = [];
    const eventRows = [];

    for (let i = 0; i < def.sessions; i++) {
      const sid = uuid();
      const isMobile = chance(p.mobilePct);
      const device = isMobile ? "MOBILE" : chance(0.15) ? "TABLET" : "DESKTOP";
      const channel = pick(["direct", "search", "search", "ad", "ad", "social", "referral"]);
      const referrer = channel === "search" ? "https://search.naver.com/search" : channel === "ad" ? "https://googlesyndication.com" : channel === "social" ? "https://instagram.com" : "";

      // 스크롤 도달 프로파일
      let maxScroll;
      if (p.scrollProfile === "low") maxScroll = randInt(5, 45);
      else if (p.scrollProfile === "mid") maxScroll = randInt(20, 80);
      else maxScroll = randInt(40, 100);

      const bounced = chance(p.bounce);
      const start = new Date(daysAgo(rand(0, 30)).getTime());
      const path = pick(p.paths);
      const vw = isMobile ? randInt(360, 430) : randInt(1200, 1680);
      const vh = isMobile ? randInt(720, 900) : randInt(720, 950);

      const evBase = { siteId: site.id, sessionId: sid, url: `https://${def.domain}${path}`, path, vw, vh };
      let t = start.getTime();
      const nextTs = () => new Date((t += randInt(500, 8000)));

      // page_view
      eventRows.push({ id: uuid(), ...evBase, type: "page_view", scrollPct: 0, meta: "{}", ts: nextTs() });

      // CTA 노출 (ctaViewRate 확률)
      if (chance(p.ctaViewRate)) {
        eventRows.push({ id: uuid(), ...evBase, type: "cta_view", targetLabel: "구매하기", meta: "{}", ts: nextTs() });
      }

      // 클릭들
      const nClicks = bounced ? randInt(0, 2) : randInt(2, 8);
      let engaged = false;
      for (let c = 0; c < nClicks; c++) {
        const isDead = chance(p.deadClickRate);
        const isRage = !isDead && chance(p.rage);
        let x, y, type, label;
        if (isDead) {
          x = around(p.deadHotspot[0], 0.08);
          y = around(p.deadHotspot[1], 0.08);
          type = "dead_click";
          label = "상품 이미지";
        } else if (isRage) {
          const h = pick(p.hotspots);
          x = around(h[0], 0.02);
          y = around(h[1], 0.02);
          type = "rage_click";
          label = "버튼";
          engaged = true;
        } else {
          const h = pick(p.hotspots);
          x = around(h[0], 0.06);
          y = around(h[1], 0.06);
          type = "click";
          label = pick(["구매하기", "장바구니", "옵션 선택", "더보기", "메뉴", "예약하기"]);
          engaged = true;
        }
        eventRows.push({ id: uuid(), ...evBase, type, xRel: x, yRel: y, scrollPct: randInt(0, maxScroll), targetLabel: label, meta: "{}", ts: nextTs() });
      }

      // 스크롤 이벤트 몇 개
      const nScroll = randInt(1, 4);
      for (let s = 0; s < nScroll; s++) {
        eventRows.push({ id: uuid(), ...evBase, type: "scroll", scrollPct: randInt(0, maxScroll), meta: "{}", ts: nextTs() });
      }

      // 모바일/태블릿 제스처 (더블탭 / 줌 / 스와이프)
      if (device === "MOBILE" || device === "TABLET") {
        // 스와이프: 콘텐츠 탐색용으로 흔함 (상하 위주, 캐러셀 좌우 일부)
        const nSwipe = randInt(1, 4);
        for (let s = 0; s < nSwipe; s++) {
          const dir = pick(["up", "down", "down", "left", "right"]);
          const h = pick(p.hotspots);
          eventRows.push({ id: uuid(), ...evBase, type: "swipe", xRel: around(h[0], 0.1), yRel: around(h[1], 0.12), meta: `{"dir":"${dir}"}`, ts: nextTs() });
        }
        // 줌: 상품 이미지 확대가 많음 (in 위주)
        if (chance(0.4)) {
          const dir = chance(0.75) ? "in" : "out";
          eventRows.push({ id: uuid(), ...evBase, type: "zoom", xRel: around(p.deadHotspot[0], 0.06), yRel: around(p.deadHotspot[1], 0.06), meta: `{"dir":"${dir}"}`, ts: nextTs() });
        }
        // 더블탭: 이미지 확대 목적 가끔
        if (chance(0.25)) {
          eventRows.push({ id: uuid(), ...evBase, type: "double_tap", xRel: around(p.deadHotspot[0], 0.05), yRel: around(p.deadHotspot[1], 0.05), meta: "{}", ts: nextTs() });
        }
      }

      // 폼 (병원 예약)
      if (p.form && chance(p.formStartRate)) {
        eventRows.push({ id: uuid(), ...evBase, type: "form_focus", targetLabel: "[text]", meta: "{}", ts: nextTs() });
        if (chance(p.formSubmitRate)) {
          eventRows.push({ id: uuid(), ...evBase, type: "form_submit", meta: "{}", ts: nextTs() });
          eventRows.push({ id: uuid(), ...evBase, type: "conversion", targetLabel: "예약 완료", meta: "{}", ts: nextTs() });
          engaged = true;
        }
      }

      // 쇼핑몰 전환 (가끔)
      if (!p.form && engaged && chance(0.06)) {
        eventRows.push({ id: uuid(), ...evBase, type: "conversion", targetLabel: "구매 완료", meta: "{}", ts: nextTs() });
      }

      const pageCount = bounced ? 1 : randInt(1, 5);
      sessionRows.push({
        id: sid,
        siteId: site.id,
        sessionKey: `seed_${sid.slice(0, 12)}`,
        device,
        channel,
        referrer,
        startedAt: start,
        lastEventAt: new Date(t),
        maxScrollPct: maxScroll,
        pageCount,
        isBounce: bounced && !engaged,
      });
    }

    // 저장 (청크)
    await prisma.session.createMany({ data: sessionRows });
    for (let i = 0; i < eventRows.length; i += 1000) {
      await prisma.event.createMany({ data: eventRows.slice(i, i + 1000) });
    }
    console.log(`     세션 ${sessionRows.length}, 이벤트 ${eventRows.length}`);

    // 공유 링크 하나 미리 생성
    await prisma.shareLink.create({ data: { siteId: site.id } });
  }

  console.log("\n✅ 시드 완료");
  console.log("로그인: owner@growthlab.kr / demo1234");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
