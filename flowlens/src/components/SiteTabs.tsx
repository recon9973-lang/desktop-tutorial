"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { key: "", label: "개요" },
  { key: "heatmap", label: "히트맵" },
  { key: "funnel", label: "퍼널" },
  { key: "sessions", label: "세션" },
  { key: "compare", label: "전후 비교" },
  { key: "suggestions", label: "개선 제안" },
  { key: "install", label: "설치 · 공유" },
  { key: "data", label: "데이터 관리" },
];

export default function SiteTabs({ siteId }: { siteId: string }) {
  const pathname = usePathname();
  const base = `/sites/${siteId}`;
  return (
    <div className="tabs">
      {TABS.map((t) => {
        const href = t.key ? `${base}/${t.key}` : base;
        const active = t.key ? pathname === href : pathname === base;
        return (
          <Link key={t.key} href={href} className={`tab ${active ? "active" : ""}`}>
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
