import Link from "next/link";
import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import TopBar from "@/components/TopBar";
import SiteTabs from "@/components/SiteTabs";
import { IndustryBadge } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function SiteLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { user, site } = await loadSiteForUser(id);
  if (!user) redirect("/login");
  if (!site) redirect("/dashboard");

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container">
        <Link href="/dashboard" className="muted small">← 대시보드</Link>
        <div className="row" style={{ margin: "10px 0 2px" }}>
          <h1 style={{ fontSize: 22 }}>{site.name}</h1>
          <IndustryBadge industry={site.client.industry} />
        </div>
        <p className="muted small">{site.client.name} · {site.domain}</p>

        <SiteTabs siteId={site.id} />
        {children}
      </div>
    </>
  );
}
