import type { Metadata } from 'next';
import Link from 'next/link';
import { EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readBrands } from '@/lib/brands';
import { listCompanies } from '@/lib/companies';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { BrandCard } from './BrandCard';
import { BrandForm } from './BrandForm';
import own from './competitors.module.css';

export const metadata: Metadata = {
  title: '브랜드 식별',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleCompetitorsPage({
  searchParams,
}: {
  readonly searchParams: Promise<{ readonly project?: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { project } = await searchParams;

  return (
    <PermissionGate identity={identity} permission="competitor:read">
      <ConsoleCompetitorsContent projectId={project ?? null} />
    </PermissionGate>
  );
}

async function ConsoleCompetitorsContent({ projectId }: { readonly projectId: string | null }) {
  const companies = await listCompanies();
  const projects = companies.ok
    ? companies.data.flatMap((company) =>
        company.projects.map((one) => ({ ...one, company: company.name })),
      )
    : [];
  const selected = projectId ?? projects[0]?.id ?? null;
  const brands = selected === null ? null : await readBrands(selected);

  // 이 프로젝트에 등록된 홈페이지. **자사 브랜드 폼의 "홈페이지에서 불러오기" 칸에
  // 미리 넣는다** — 거래처 등록 때 이미 받은 주소를, 브랜드 식별에서 또 손으로 치게
  // 두지 않는다. 여러 개면 대표 사이트를 쓴다.
  const projectSites =
    selected === null || !companies.ok
      ? []
      : companies.data.flatMap((company) =>
          company.sites.filter((site) => site.projectId === selected),
        );
  const ownSiteOrigin =
    projectSites.find((site) => site.isPrimary)?.origin ?? projectSites[0]?.origin ?? '';

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>브랜드 식별</h1>
        <p className={styles.lede}>
          AI 답변에서 <strong>어느 상호가 이 고객인지</strong> 가리는 데 쓰는 정보입니다. 한국
          병원 상호는 겹칩니다 — <code>서울치과</code>는 수십 곳이고, 고유한 이름조차 더 긴
          상호에 통째로 들어갑니다. 이름만 등록하면 언급이 전부 검수 대기로 넘어갑니다.
        </p>
      </div>

      {/*
        비교 대상을 우리와 같은 화면에 둔다. 따로 두면 우리 쪽만 꼼꼼히 채우고 경쟁사는
        이름만 적는 일이 자연스럽게 벌어지고, 그 비대칭은 점유율에 그대로 나타난다.
      */}
      {projects.length > 1 ? (
        <nav className={own.projectTabs} aria-label="프로젝트 선택">
          {projects.map((one) => (
            <Link
              key={one.id}
              href={`/console/competitors?project=${encodeURIComponent(one.id)}`}
              className={one.id === selected ? own.projectTabActive : own.projectTab}
            >
              {one.company} · {one.name}
            </Link>
          ))}
        </nav>
      ) : null}

      {selected === null ? (
        <EmptyState description="프로젝트가 없습니다. 업체와 프로젝트를 먼저 만들어 주십시오." />
      ) : brands !== null && !brands.ok ? (
        <ErrorState
          title="브랜드 정보를 불러오지 못했습니다"
          description={brands.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : brands !== null && brands.ok ? (
        <>
          {!brands.data.can_observe ? (
            <p className={own.blocked}>
              <strong>자사 브랜드가 등록되어 있지 않아 GEO 관측을 실행할 수 없습니다.</strong>{' '}
              무엇을 찾아야 하는지 모르는 채로 돌리면 모든 답변이 &lsquo;언급 없음&rsquo;으로
              기록되는데, 그것은 측정이 아닙니다.
            </p>
          ) : null}

          {brands.data.asymmetry_ko.length > 0 ? (
            <section className={own.asymmetry} aria-label="등록 정보 비대칭 경고">
              <h2 className={own.asymmetryTitle}>점유율이 조용히 틀어질 수 있습니다</h2>
              <ul className={own.asymmetryList}>
                {brands.data.asymmetry_ko.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className={styles.section} aria-labelledby="brands-own-heading">
            <h2 id="brands-own-heading" className={styles.sectionTitle}>
              자사 브랜드
            </h2>
            {brands.data.ours === null ? (
              <>
                <EmptyState description="자사 브랜드가 아직 등록되지 않았습니다." />
                <BrandForm projectId={selected} isOwnBrand siteOrigin={ownSiteOrigin} />
              </>
            ) : (
              <ul className={own.brandList}>
                <BrandCard brand={brands.data.ours} />
              </ul>
            )}
            {brands.data.ours === null ? null : (
              /* 한 번 저장하면 오타 하나도 못 고치던 자리. 서버에는 처음부터 고치는
                 길이 있었고 화면에 단추가 없었을 뿐이다(0-E). */
              <BrandForm
                projectId={selected}
                isOwnBrand
                siteOrigin={ownSiteOrigin}
                brand={brands.data.ours}
              />
            )}
          </section>

          <section className={styles.section} aria-labelledby="brands-rivals-heading">
            <h2 id="brands-rivals-heading" className={styles.sectionTitle}>
              비교 대상 {brands.data.competitors.length}곳
            </h2>
            <p className={styles.callout}>
              점유율은 비교 대상이 있어야 정의됩니다. 하나도 없으면 모든 점유율이 100%로
              나오는데, 그 값은 측정이 아니라 <strong>비교 대상이 없다는 사실</strong>입니다.
            </p>
            {brands.data.competitors.length > 0 ? (
              <ul className={own.brandList}>
                {brands.data.competitors.map((brand) => (
                  <li key={brand.id} className={own.brandRow}>
                    <ul className={own.brandList}>
                      <BrandCard brand={brand} />
                    </ul>
                    <BrandForm projectId={selected} isOwnBrand={false} brand={brand} />
                  </li>
                ))}
              </ul>
            ) : null}
            <BrandForm projectId={selected} isOwnBrand={false} />
          </section>
        </>
      ) : null}
    </div>
  );
}
