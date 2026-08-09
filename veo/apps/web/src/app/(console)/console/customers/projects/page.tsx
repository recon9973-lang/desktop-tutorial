import type { Metadata } from 'next';
import Link from 'next/link';
import { EmptyState, ErrorState } from '@veo/ui';

import { listProjects } from '@/lib/projects';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import { ProjectNameForm } from './ProjectNameForm';
import own from './projects.module.css';

export const metadata: Metadata = {
  title: '프로젝트',
};

export const dynamic = 'force-dynamic';

export default async function ConsoleProjectsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="project:read">
      <ConsoleProjectsContent />
    </PermissionGate>
  );
}

async function ConsoleProjectsContent() {
  const found = await listProjects();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>프로젝트</h1>
        <p className={styles.lede}>
          측정이 실제로 매달리는 단위입니다. <strong>브랜드 식별과 GEO 관측은 업체가 아니라
          프로젝트에 달립니다</strong> — 어느 프로젝트가 잴 준비가 되었는지는 업체 화면으로는
          알 수 없습니다.
        </p>
      </div>

      {!found.ok ? (
        <ErrorState
          title="프로젝트를 불러오지 못했습니다"
          description={found.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : found.data.length === 0 ? (
        <EmptyState description="등록된 프로젝트가 없습니다. 업체 화면에서 측정할 주소를 등록하면 프로젝트가 함께 만들어집니다." />
      ) : (
        <section className={styles.section} aria-labelledby="projects-list-heading">
          <h2 id="projects-list-heading" className={styles.sectionTitle}>
            프로젝트 {found.data.length}개
          </h2>
          <ul className={own.projectList}>
            {found.data.map((project) => (
              <li key={project.id} className={own.project}>
                <p className={own.projectHead}>
                  <span className={own.projectName}>{project.name}</span>
                  {project.customerName !== null ? (
                    <span className={own.customer}>{project.customerName}</span>
                  ) : null}
                  <span className={own.slug}>{project.slug}</span>
                </p>

                <dl className={own.fields}>
                  <div className={own.field}>
                    <dt>측정 주소</dt>
                    <dd className={project.sites.length === 0 ? own.empty : undefined}>
                      {project.sites.length === 0
                        ? '없음'
                        : project.sites
                            .map((site) => (site.isPrimary ? `${site.origin} (대표)` : site.origin))
                            .join(' · ')}
                    </dd>
                  </div>
                  <div className={own.field}>
                    <dt>진단 기준 지역</dt>
                    <dd>{project.locale}</dd>
                  </div>
                  {/*
                    비워 두면 서버 기본값이 적용된다. '기본값'이라고 적고 어떤 버전인지는
                    적지 않는다 — 여기서 지어내면 실제로 채점에 쓰인 버전과 어긋난다.
                    실제로 쓰인 버전은 리포트에 고정되어 남는다.
                  */}
                  <div className={own.field}>
                    <dt>SEO 명세</dt>
                    <dd>{project.seoSpecVersion ?? '서버 기본값'}</dd>
                  </div>
                  <div className={own.field}>
                    <dt>GEO 명세</dt>
                    <dd>{project.geoSpecVersion ?? '서버 기본값'}</dd>
                  </div>
                </dl>

                <p className={own.links}>
                  <Link href={`/console/competitors?project=${encodeURIComponent(project.id)}`}>
                    브랜드 식별
                  </Link>
                  <Link href={`/console/issues?project=${encodeURIComponent(project.id)}`}>
                    이슈
                  </Link>
                  {/*
                    이름을 고치는 길. 서버에는 처음부터 있었는데 화면이 없어 오타 하나도
                    못 고쳤다 — 브랜드에서 두 번 나온 같은 구멍이다(v0.3.69).
                  */}
                  <ProjectNameForm projectId={project.id} projectName={project.name} />
                </p>
              </li>
            ))}
          </ul>
          <p className={styles.callout}>
            프로젝트는 업체 화면에서 주소를 등록할 때 함께 만들어집니다. 단계 수는 구현
            사정이지 직원이 밟아야 할 절차가 아닙니다.
          </p>
        </section>
      )}
    </div>
  );
}
