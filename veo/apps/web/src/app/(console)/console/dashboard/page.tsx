import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { listCompanies, type Company } from '@/lib/companies';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

/**
 * 로그인 직후의 화면.
 *
 * 여기는 **일을 시작하는 곳**이다. 한때 아직 아무것도 재지 않은 상태의 빈 점수 카드가
 * 놓여 있었는데, 화면에는 "측정 불가 · 측정 범위 0%" 로 나타나 고장난 도구처럼 읽혔다.
 * 시작하는 방법이 화면 어디에도 없었기 때문이다.
 *
 * 그래서 없는 숫자를 지어내 채우지 않는다. 등록된 것이 없으면 등록하러 가는 길을,
 * 있으면 그 목록을 보여 준다. 요약 지표는 실행 기록이 쌓인 뒤에 의미가 생긴다.
 */

export const metadata: Metadata = {
  title: '대시보드',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleDashboardPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <DashboardContent />
    </PermissionGate>
  );
}

async function DashboardContent() {
  const companies = await listCompanies();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>대시보드</h1>
        <p className={styles.lede}>
          진단할 업체와 측정 URL을 등록하고, 결과를 확인합니다. 한 번 잰 결과는 저장되므로
          다시 열어도 그대로 보이고, 다시 재는 것은 변경을 확인할 때만 하시면 됩니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="dashboard-sites">
        <h2 id="dashboard-sites" className={styles.sectionTitle}>
          측정 대상
        </h2>
        {companies.ok ? (
          <SiteSummary companies={companies.data} />
        ) : (
          <ErrorState
            title="목록을 불러오지 못했습니다"
            description={companies.message ?? '서버에 연결하지 못했습니다.'}
          />
        )}
      </section>
    </div>
  );
}

function SiteSummary({ companies }: { readonly companies: readonly Company[] }) {
  const sites = companies.flatMap((company) =>
    company.sites.map((site) => ({ company: company.name, ...site })),
  );

  if (sites.length === 0) {
    return (
      <EmptyState
        description="등록된 측정 URL이 없습니다. 업체와 주소를 등록하면 여기에서 바로 진단할 수 있습니다."
        action={<Link href="/console/customers">업체 등록하러 가기</Link>}
      />
    );
  }

  return (
    <Card title={`업체 ${companies.length}곳 · 주소 ${sites.length}개`} headingLevel={3}>
      <ul className={styles.prose}>
        {sites.map((site) => (
          <li key={site.siteId}>
            <Link href={`/console/seo?site=${site.siteId}`}>
              {site.company} — {site.origin}
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
