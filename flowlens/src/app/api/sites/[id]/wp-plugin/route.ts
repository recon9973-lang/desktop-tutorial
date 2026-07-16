import { NextRequest, NextResponse } from "next/server";
import { loadSiteForUser } from "@/lib/site";

// siteKey가 박힌 워드프레스 단일 파일 플러그인을 생성해 내려준다.
// 고객은 이 .php를 wp-content/plugins/ 에 올리고 활성화하면 추적이 시작된다.
export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  const origin = new URL(req.url).origin;
  if (!site) return NextResponse.redirect(new URL("/dashboard", origin), { status: 303 });

  const src = `${origin}/t.js`;
  const php = `<?php
/**
 * Plugin Name: FlowLens Tracker (${site.name})
 * Description: FlowLens 행동 분석 추적 스크립트를 사이트 전체에 자동 삽입합니다.
 * Version: 1.0.0
 * Author: FlowLens
 */
if (!defined('ABSPATH')) { exit; }

// 모든 페이지 <head>에 추적 스크립트 삽입
add_action('wp_head', function () {
    $src  = '${src}';
    $site = '${site.siteKey}';
    echo '<script async src="' . esc_url($src) . '" data-site="' . esc_attr($site) . '"></script>' . "\\n";
}, 1);
`;

  return new NextResponse(php, {
    status: 200,
    headers: {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": `attachment; filename="flowlens-tracker.php"`,
    },
  });
}
