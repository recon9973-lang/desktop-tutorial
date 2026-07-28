import type { Metadata } from 'next';
import { Button, Card, EmptyState } from '@veo/ui';

import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '리포트',
};


export default async function ConsoleReportsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="report:read">
      <ConsoleReportsContent />
    </PermissionGate>
  );
}

function ConsoleReportsContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>리포트</h1>
        <p className={styles.lede}>
          점검 결과를 공유용 링크로 내보냅니다. 공유 링크는 읽기 전용이며
          <span className={styles.token}> /results/&lt;토큰&gt; </span>
          주소로 열립니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="reports-list-heading">
        <h2 id="reports-list-heading" className={styles.sectionTitle}>
          생성된 리포트
        </h2>
        <EmptyState
          description="생성된 리포트가 없습니다. 점검을 실행한 뒤 리포트를 만들면 공유 링크와 생성 시각이 이곳에 표시됩니다."
          action={<Button disabled>리포트 생성</Button>}
        />
      </section>

      <section className={styles.section} aria-labelledby="reports-policy-heading">
        <h2 id="reports-policy-heading" className={styles.sectionTitle}>
          공유 링크 취급 방침
        </h2>
        <Card title="리포트에 항상 포함되는 정보" headingLevel={3}>
          <ul className={styles.list}>
            <li>계산에 사용한 채점 명세와 버전</li>
            <li>측정 범위와 신뢰도</li>
            <li>각 값의 출처와 수집 시각</li>
            <li>측정하지 못한 항목과 그 이유</li>
          </ul>
        </Card>
        <p className={styles.prose}>
          공유 링크를 아는 사람은 로그인 없이 리포트를 볼 수 있으므로 배포 범위를 직접 관리해야
          합니다. 검색엔진 색인은 기본적으로 차단됩니다.
        </p>
      </section>
    </div>
  );
}
