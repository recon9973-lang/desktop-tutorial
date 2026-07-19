// 자동 초안 생성 실행기 — 크론과 수동("지금 생성")이 공유.
// 설정(AutoBlogSetting)을 읽어 N개 초안을 생성해 BlogPost(published=false)로 저장한다.
// ★ 절대 자동 발행하지 않는다. 항상 초안으로만 저장 → 사람이 검토 후 발행. ★

import { prisma } from "@/lib/db";
import { generateFlowLensPost } from "./generator";

export type DraftResult =
  | { ok: true; slug: string; title: string; publishableHint: boolean }
  | { ok: false; keyword: string; error: string };

function splitLines(s: string): string[] {
  return s
    .split(/[\n,]/)
    .map((x) => x.trim())
    .filter(Boolean);
}

// override로 한도를 강제할 수 있음(수동 실행 시 안전 상한)
export async function runDailyDrafts(overrideCount?: number): Promise<{
  ran: number;
  results: DraftResult[];
  skippedReason?: string;
}> {
  const s = await prisma.autoBlogSetting.findUnique({ where: { id: "default" } });
  if (!s || !s.enabled) return { ran: 0, results: [], skippedReason: "자동 생성이 꺼져 있습니다." };

  const keywords = splitLines(s.keywords);
  if (keywords.length === 0) return { ran: 0, results: [], skippedReason: "키워드가 비어 있습니다." };

  const regions = splitLines(s.regions);
  const category = s.category || "heatmap";
  // 안전 상한: 한 번에 최대 5개
  const count = Math.min(Math.max(1, overrideCount ?? s.dailyCount), 5);

  const results: DraftResult[] = [];
  for (let i = 0; i < count; i++) {
    const keyword = keywords[i % keywords.length];
    const region = regions.length ? regions[i % regions.length] : "";
    try {
      const draft = await generateFlowLensPost({ category, keyword, region, extra: s.extra });
      const slug = "ai-" + Date.now().toString(36) + "-" + i;
      await prisma.blogPost.create({
        data: {
          slug,
          title: draft.title,
          seoTitle: draft.seoTitle,
          description: draft.metaDesc,
          keywords: draft.keywords,
          category: draft.categoryLabel,
          body: draft.bodyHtml,
          author: "FlowLens (주식회사 베놈)",
          date: new Date().toISOString().slice(0, 10),
          published: false, // 항상 초안
        },
      });
      results.push({ ok: true, slug, title: draft.title, publishableHint: draft.publishable });
    } catch (e) {
      results.push({ ok: false, keyword, error: e instanceof Error ? e.message : "생성 오류" });
    }
  }
  return { ran: count, results };
}
