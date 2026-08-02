import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { EmptyState } from '@veo/ui';

import { readSharedResult } from '@/lib/scan-api';
import styles from '@/styles/page.module.css';

import { SharedReport } from './SharedReport';

/**
 * 공유 리포트 — `/results/{token}` 로 저장된 진단 결과를 다시 보여준다.
 *
 * 서버에서 결과를 읽어 진단 화면의 Report 를 그대로 그린다. 엔진이 404 를 돌려주면
 * (없거나 만료 — 엔진은 둘을 구분해 주지 않는다) 이 페이지도 404 다. 만료를 빈
 * 성공 화면처럼 그리면 링크를 받은 사람이 "점수가 없는 사이트"로 오해한다.
 */

export const metadata: Metadata = {
  title: '공유 리포트',
  description: '공유 링크로 열람하는 VEO 점검 리포트입니다.',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

interface ResultsPageProps {
  params: Promise<{ token: string }>;
}

/** 만료일 표기 — ShareLink 의 것과 같은 모양. 클라이언트 모듈이라 서버에서 못 부른다. */
function expiryDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return `${date.getFullYear()}.${date.getMonth() + 1}.${date.getDate()}`;
}

export default async function ResultsPage({ params }: ResultsPageProps) {
  const { token } = await params;
  const outcome = await readSharedResult(token);

  if (!outcome.ok) {
    if (outcome.reason === 'NOT_FOUND') {
      notFound();
    }
    // 만료가 아니라 조회 실패다 — 링크가 죽었다고 말하면 안 된다.
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <p className={styles.eyebrow}>공유 리포트</p>
          <h1 className={styles.title}>리포트를 불러오지 못했습니다</h1>
        </div>
        <EmptyState
          description={
            outcome.reason === 'NOT_CONFIGURED'
              ? '측정 엔진 주소가 설정되지 않았습니다. 운영자에게 문의해 주세요.'
              : '측정 엔진에 연결하지 못했습니다. 링크가 만료된 것은 아니니 잠시 후 새로고침해 주세요.'
          }
        />
      </div>
    );
  }

  const { result } = outcome;
  const expiry = expiryDate(result.resultExpiresAt);
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>공유 리포트 · {result.kind}</p>
        <h1 className={styles.title}>{result.targetUrl}</h1>
        <p className={styles.lede}>
          공유 링크로 열람하는 읽기 전용 리포트입니다. 진단 시점의 결과를 그대로
          보여줍니다{expiry !== '' ? ` — ${expiry}까지 열람할 수 있습니다` : ''}.
        </p>
      </div>
      <SharedReport result={result} />
    </div>
  );
}
