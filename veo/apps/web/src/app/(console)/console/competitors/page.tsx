import type { Metadata } from 'next';
import { Button, EmptyState } from '@veo/ui';

import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '경쟁사',
};


export default async function ConsoleCompetitorsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="competitor:read">
      <ConsoleCompetitorsContent />
    </PermissionGate>
  );
}

function ConsoleCompetitorsContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>경쟁사</h1>
        <p className={styles.lede}>
          비교 대상 사이트를 등록하면 같은 채점 기준으로 준비도를 나란히 볼 수 있습니다. 비교는
          동일한 채점 명세 버전으로 측정한 결과끼리만 이루어집니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="competitors-list-heading">
        <h2 id="competitors-list-heading" className={styles.sectionTitle}>
          비교 대상
        </h2>
        <EmptyState
          description="등록된 경쟁사가 없습니다. 비교 대상을 등록하면 동일한 기준으로 측정한 결과가 이곳에 표시됩니다."
          action={<Button disabled>경쟁사 등록</Button>}
        />
        <p className={styles.prose}>
          경쟁사 등록은 콘솔 API가 연결된 뒤 활성화됩니다.
        </p>
      </section>
    </div>
  );
}
