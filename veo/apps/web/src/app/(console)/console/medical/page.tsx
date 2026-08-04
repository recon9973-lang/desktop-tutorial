import type { Metadata } from 'next';

import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { CopyReviewForm } from './CopyReviewForm';

export const metadata: Metadata = {
  title: '원고 표현 검수',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * 의료광고 원고 검수 (P2-11).
 *
 * 이 화면은 위반 판정기가 아니다 — 의료법 제56조의 금지 유형에 해당할 수 있는
 * 표현을 표시해, 사람이 반드시 읽어 봐야 할 자리를 놓치지 않게 한다. 점수는 없다.
 * 원고는 서버 어디에도 저장되지 않는다.
 */
export default async function MedicalReviewPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <div className={styles.page}>
        <div className={styles.header}>
          <p className={styles.eyebrow}>콘솔</p>
          <h1 className={styles.title}>원고 표현 검수</h1>
          <p className={styles.lede}>
            블로그 원고·페이지 문안을 붙여 넣으면 의료법 제56조의 금지 유형에 해당할 수
            있는 표현을 근거 조항과 함께 표시합니다. <strong>위반 판정이 아니라 검토
            신호입니다</strong> — 표시가 없다고 적법한 것도, 있다고 위법한 것도 아닙니다.
            원고는 저장되지 않습니다.
          </p>
        </div>
        <CopyReviewForm />
      </div>
    </PermissionGate>
  );
}
