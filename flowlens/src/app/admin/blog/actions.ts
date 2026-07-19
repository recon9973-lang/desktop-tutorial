"use server";

import { redirect } from "next/navigation";
import { prisma } from "@/lib/db";
import { getAdminUser } from "@/lib/admin";
import { generateFlowLensPost } from "@/lib/autoblog/generator";

async function assertAdmin() {
  const a = await getAdminUser();
  if (!a) throw new Error("forbidden");
  return a;
}

function slugify(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

// 새 글/수정 저장 (slug 기준 upsert). 운영자만.
export async function saveBlogPost(form: FormData) {
  await assertAdmin();
  const title = String(form.get("title") || "").trim();
  const slug = slugify(String(form.get("slug") || ""));
  if (!title || !slug) throw new Error("제목과 slug(영문 주소)는 필수입니다.");

  const data = {
    title,
    seoTitle: String(form.get("seoTitle") || "").trim(),
    description: String(form.get("description") || "").trim(),
    keywords: String(form.get("keywords") || "").trim(),
    category: String(form.get("category") || "").trim(),
    body: String(form.get("body") || ""),
    author: String(form.get("author") || "").trim() || "FlowLens (주식회사 베놈)",
    date: String(form.get("date") || "").trim() || new Date().toISOString().slice(0, 10),
    published: form.get("published") === "on" || form.get("published") === "1",
  };

  await prisma.blogPost.upsert({ where: { slug }, create: { slug, ...data }, update: data });
  redirect("/admin/blog");
}

// 발행 토글
export async function toggleBlogPublish(form: FormData) {
  await assertAdmin();
  const slug = String(form.get("slug") || "");
  const post = await prisma.blogPost.findUnique({ where: { slug } });
  if (post) await prisma.blogPost.update({ where: { slug }, data: { published: !post.published } });
  redirect("/admin/blog");
}

// 삭제
export async function deleteBlogPost(form: FormData) {
  await assertAdmin();
  const slug = String(form.get("slug") || "");
  await prisma.blogPost.deleteMany({ where: { slug } });
  redirect("/admin/blog");
}

// AI 초안 생성 → 임시저장(초안, 미발행)으로 저장 후 수정 화면으로 이동.
// 자동 발행하지 않고 반드시 사람이 검토 후 발행하도록 설계(안전).
export async function generateBlogDraft(form: FormData) {
  await assertAdmin();
  const category = String(form.get("category") || "heatmap").trim();
  const keyword = String(form.get("keyword") || "").trim();
  const region = String(form.get("region") || "").trim();
  const extra = String(form.get("extra") || "").trim();
  if (!keyword) redirect("/admin/blog?err=" + encodeURIComponent("키워드를 입력하세요."));

  let slug = "";
  let errMsg = "";
  try {
    const draft = await generateFlowLensPost({ category, keyword, region, extra });
    slug = "ai-" + Date.now().toString(36);
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
        published: false, // 항상 초안으로 — 사람이 검토 후 발행
      },
    });
  } catch (e) {
    errMsg = e instanceof Error ? e.message : "AI 생성 중 오류가 발생했습니다.";
  }

  // redirect는 try/catch 밖에서 (내부적으로 throw 하므로)
  if (errMsg) redirect("/admin/blog?err=" + encodeURIComponent(errMsg));
  redirect(`/admin/blog/${slug}?new=1`);
}
