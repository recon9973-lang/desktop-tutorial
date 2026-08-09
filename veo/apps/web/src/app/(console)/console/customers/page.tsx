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
  // **등록된 거래처만.** 주소만 넣고 한 번 재 본 자리는 여기 오지 않는다 — 영업 중에
  // 넣어 본 주소가 섞이면 이 목록이 "우리가 맡은 곳"을 말하지 못한다(사용자 지적).
  // 재 본 자리를 거래처로 올리는 길은 아래 등록 폼이다: 같은 주소를 넣으면 새로 만들지
  // 않고 그 자리가 올라간다.
  const outcome = await listCompanies({ registered: true });

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>업체 관리</h1>
        <p className={styles.lede}>
          진단할 업체와 측정 URL을 등록합니다. 한 업체에 주소를 여러 개 둘 수 있고, 진단
          결과는 주소마다 따로 쌓입니다.{' '}
          {/* 프로젝트는 별도 메뉴였다가 이 화면의 하위로 들어왔다 — 두 메뉴가 같은 일
              (측정 대상 등록)로 읽혀 서로를 가렸다(사용자 감사). */}
          측정 단위(브랜드 식별·GEO 관측)의 세부 설정은{' '}
          <Link href="/console/customers/projects" className={own.projectsLink}>
            프로젝트 설정
          </Link>
          에서 합니다.
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
            {/*
              업체명이 곧 현황 화면으로 가는 문이다. 이 목록은 **관리**(등록·수정)를
              하는 자리이고, 진단 결과를 거래처 단위로 모아 보는 자리는 따로 있다.
              두 일을 한 화면에 겹치면 등록 폼 사이에 점수가 끼어 어느 쪽도 읽히지
              않는다.
            */}
            <h3 className={own.companyName}>
              <Link href={`/console/customers/${company.customerId}`}>{company.name}</Link>
            </h3>
            <span className={own.siteCount}>
              측정 URL {company.sites.length}개
            </span>
          </div>

          {/*
            소재지를 이름 바로 아래 둔다. **상호는 식별자가 아니다** — `서울치과` 는
            수십 곳이고, 이름만 늘어놓은 목록에서는 어느 곳을 맡고 있는지 가려지지
            않는다. 비어 있으면 비어 있다고 말한다. 조용히 빼면 "적을 것이 없는
            업체" 로 읽히고, 그러면 아무도 채우지 않는다.
          */}
          {company.address === null || company.address === '' ? (
            <p className={own.noAddress}>소재지가 비어 있습니다 — 이름이 겹치면 가려낼 수 없습니다.</p>
          ) : (
            <p className={own.address}>{company.address}</p>
          )}

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
