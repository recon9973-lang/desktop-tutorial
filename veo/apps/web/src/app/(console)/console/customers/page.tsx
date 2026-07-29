import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { listCompanies, type Company } from '@/lib/companies';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { CompanyForm } from './CompanyForm';
import own from './companies.module.css';

export const metadata: Metadata = {
  title: '업체 관리',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * 업체와 측정 URL.
 *
 * 업체에게 로그인 계정을 발급하지 않는다 — 직원이 URL 을 저장·관리하고 결과를 전달한다.
 * 엔진의 고객 → 프로젝트 → 사이트 세 단계는 여기서 보이지 않는다. 사람이 넣는 것은
 * 업체명과 주소 둘뿐이다.
 */
export default async function CustomersPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="customer:read">
      <CustomersContent />
    </PermissionGate>
  );
}

async function CustomersContent() {
  const outcome = await listCompanies();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>업체 관리</h1>
        <p className={styles.lede}>
          진단할 업체와 측정 URL을 등록합니다. 한 업체에 주소를 여러 개 둘 수 있고, 진단
          결과는 주소마다 따로 쌓입니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="add-company">
        <h2 id="add-company" className={styles.sectionTitle}>
          업체 등록
        </h2>
        <Card title="새 업체" headingLevel={3}>
          <CompanyForm />
        </Card>
      </section>

      <section className={styles.section} aria-labelledby="company-list">
        <h2 id="company-list" className={styles.sectionTitle}>
          등록된 업체
        </h2>
        {outcome.ok ? (
          <CompanyList companies={outcome.data} />
        ) : (
          <ErrorState
            title="목록을 불러오지 못했습니다"
            description={
              outcome.message ??
              '서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.'
            }
          />
        )}
      </section>
    </div>
  );
}

function CompanyList({ companies }: { companies: readonly Company[] }) {
  if (companies.length === 0) {
    return (
      <EmptyState description="등록된 업체가 없습니다. 위에서 업체명과 측정 URL을 넣어 시작하십시오." />
    );
  }

  return (
    <ul className={own.list}>
      {companies.map((company) => (
        <li key={company.customerId} className={own.company}>
          <div className={own.companyHead}>
            <h3 className={own.companyName}>{company.name}</h3>
            <span className={own.siteCount}>
              측정 URL {company.sites.length}개
            </span>
          </div>

          {company.sites.length === 0 ? (
            <p className={own.noSites}>
              측정 URL이 없습니다. 아래에서 추가하면 진단할 수 있습니다.
            </p>
          ) : (
            <ul className={own.sites}>
              {company.sites.map((site) => (
                <li key={site.siteId} className={own.site}>
                  <span className={own.origin}>{site.origin}</span>
                  {/* 진단 실행과 결과 보기는 사이트 화면에서. 여기서는 관리만 한다. */}
                  <Link href={`/console/seo?site=${site.siteId}`}>진단 보기</Link>
                </li>
              ))}
            </ul>
          )}

          <CompanyForm customerId={company.customerId} companyName={company.name} />
        </li>
      ))}
    </ul>
  );
}
