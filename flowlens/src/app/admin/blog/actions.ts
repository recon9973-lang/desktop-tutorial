"use server";

import { redirect } from "next/navigation";
import { prisma } from "@/lib/db";
import { getAdminUser } from "@/lib/admin";

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
