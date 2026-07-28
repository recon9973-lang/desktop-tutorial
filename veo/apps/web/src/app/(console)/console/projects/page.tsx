import type { Metadata } from 'next';
import { Button, EmptyState } from '@veo/ui';

import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '프로젝트',
};


export default async function ConsoleProjectsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="project:read">
      <ConsoleProjectsContent />
    </PermissionGate>
  );
}

function ConsoleProjectsContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>프로젝트</h1>
        <p className={styles.lede}>
          측정 대상 사이트를 프로젝트 단위로 관리합니다. 프로젝트마다 점검 범위, 대표 URL,
          경쟁사 목록을 따로 설정합니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="projects-list-heading">
        <h2 id="projects-list-heading" className={styles.sectionTitle}>
          프로젝트 목록
        </h2>
        <EmptyState
          description="등록된 프로젝트가 없습니다. 프로젝트를 등록하면 점검 대상과 실행 이력이 이곳에 표시됩니다."
          action={<Button disabled>프로젝트 등록</Button>}
        />
        <p className={styles.prose}>
          프로젝트 등록은 콘솔 API가 연결된 뒤 활성화됩니다.
        </p>
      </section>
    </div>
  );
}
