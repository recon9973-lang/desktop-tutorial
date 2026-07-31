import type { Metadata } from 'next';
import { EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readReviewQueue } from '@/lib/observations';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { ReviewCard } from './ReviewCard';
import own from './review.module.css';

export const metadata: Metadata = {
  title: '위험 검수',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleReviewPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="observation:review">
      <ConsoleReviewContent />
    </PermissionGate>
  );
}

async function ConsoleReviewContent() {
  const queue = await readReviewQueue();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>위험 검수</h1>
        <p className={styles.lede}>
          AI 답변에 대한 자동 지적 가운데 <strong>사람이 확인해야 하는 것</strong>들입니다.
          심각한 것부터 나옵니다. 여기서 확정되기 전에는 고객 문서에 문장이 실리지 않습니다.
        </p>
      </div>

      {/*
        검수가 왜 필요한지를 목록보다 먼저 적는다. 이 화면을 처음 여는 사람은 "왜 내가
        이걸 다시 봐야 하나" 를 먼저 묻고, 답이 없으면 전부 확정을 눌러 버린다.
      */}
      <p className={styles.callout}>
        <strong>자동 판정은 제안이지 결론이 아닙니다.</strong> 사람의 결론은 별도로 기록되며
        자동 판정을 덮어쓰지 않습니다 — 둘이 어긋난 자리가 곧 자동 판정을 고쳐야 하는
        자리이기 때문입니다.
      </p>

      {!queue.ok ? (
        <ErrorState
          title="검수 목록을 불러오지 못했습니다"
          description={queue.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : queue.data.items.length === 0 ? (
        <EmptyState description="지금 사람이 확인해야 하는 지적은 없습니다." />
      ) : (
        <section className={styles.section} aria-labelledby="review-queue-heading">
          <h2 id="review-queue-heading" className={styles.sectionTitle}>
            확인이 필요한 지적 {queue.data.total}건
          </h2>
          <ul className={own.list}>
            {queue.data.items.map((item) => (
              <ReviewCard
                key={item.assessment_id}
                item={item}
                reasons={queue.data.rejection_reasons}
              />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
