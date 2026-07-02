// 목표: prisma/seed.ts 에 병합하거나 별도 `tsx prisma/seed-masters.ts` 로 실행.
// 업종/업무카테고리/채널 마스터 초기 시드 (이후 관리자가 설정에서 편집).
import { PrismaClient } from "@prisma/client";

const db = new PrismaClient();

// 업종 대분류 → 하위(진료과). "기타"는 수기입력(industryCustom)로 처리하므로 항목 생략 가능.
const INDUSTRIES: { name: string; color: string; children?: string[] }[] = [
  {
    name: "의료",
    color: "#e11d48",
    children: [
      "피부과", "성형외과", "정형외과", "치과", "한의원", "안과",
      "비뇨의학과", "산부인과", "이비인후과", "내과",
      "정신건강의학과", "재활의학과", "가정의학과", "통증의학과"
    ]
  },
  { name: "뷰티", color: "#db2777" },
  { name: "요식", color: "#f59e0b" },
  { name: "법률", color: "#334155" },
  { name: "교육", color: "#2563eb" },
  { name: "부동산", color: "#0d9488" },
  { name: "쇼핑몰·커머스", color: "#7c3aed" }
];

// 업무 카테고리: 그룹별
const WORK_CATEGORIES: { name: string; group: string; color: string }[] = [
  { name: "브랜드블로그 작성", group: "블로그", color: "#22c55e" },
  { name: "블로그 배포", group: "블로그", color: "#16a34a" },
  { name: "블로그 상위노출", group: "블로그", color: "#15803d" },
  { name: "파워링크", group: "검색광고", color: "#3b82f6" },
  { name: "플레이스 순위관리", group: "지도", color: "#06b6d4" },
  { name: "SNS 관리/배포", group: "SNS", color: "#ec4899" },
  { name: "SEO(웹사이트)", group: "웹", color: "#8b5cf6" },
  { name: "GEO(생성형엔진)", group: "웹", color: "#a855f7" },
  { name: "홈페이지 관리", group: "웹", color: "#6366f1" },
  { name: "계정관리", group: "운영", color: "#64748b" },
  { name: "영수증 리뷰", group: "운영", color: "#f97316" },
  { name: "월간 보고서 작성", group: "운영", color: "#0ea5e9" },
  { name: "방문자수/성과 집계", group: "운영", color: "#14b8a6" }
];

const CHANNELS: string[] = [
  "네이버 블로그", "인스타그램", "페이스북", "유튜브", "스레드",
  "네이버 플레이스", "홈페이지", "네이버 검색광고(파워링크)",
  "네이버 애널리틱스/GA", "카카오채널"
];

async function main() {
  // 업종
  for (let i = 0; i < INDUSTRIES.length; i++) {
    const cat = INDUSTRIES[i];
    const parent = await db.industryCategory.create({
      data: { name: cat.name, colorTag: cat.color, sortOrder: i, isLocked: cat.name === "의료" }
    });
    if (cat.children) {
      for (let j = 0; j < cat.children.length; j++) {
        await db.industryCategory.create({
          data: { name: cat.children[j], parentId: parent.id, colorTag: cat.color, sortOrder: j }
        });
      }
    }
  }

  // 업무 카테고리 (핵심 3종 잠금 예시)
  const locked = new Set(["브랜드블로그 작성", "플레이스 순위관리", "월간 보고서 작성"]);
  for (let i = 0; i < WORK_CATEGORIES.length; i++) {
    const w = WORK_CATEGORIES[i];
    await db.workCategoryMaster.create({
      data: { name: w.name, group: w.group, colorTag: w.color, sortOrder: i, isLocked: locked.has(w.name) }
    });
  }

  // 채널
  for (let i = 0; i < CHANNELS.length; i++) {
    await db.channelType.create({ data: { name: CHANNELS[i], sortOrder: i } });
  }

  // 회사 정책 싱글턴
  const existing = await db.companySetting.findFirst();
  if (!existing) {
    await db.companySetting.create({ data: {} });
  }

  console.log("Masters seeded: industries, work categories, channels, company setting.");
}

main().finally(() => db.$disconnect());
