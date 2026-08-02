import type { Metadata } from 'next';

import styles from '@/styles/page.module.css';

import { PublicChecker } from '../checker/PublicChecker';

export const metadata: Metadata = {
  title: 'GEO 점수 체크',
  description:
    '주소 하나로 AI 답변 엔진이 사이트를 읽고 인용할 수 있는지 확인합니다. 노출 차단 여부는 점수와 별개로 표시합니다.',
};

export default function GeoToolPage() {
  return (
    <div className={styles.page}>
      <PublicChecker kind="GEO" />
    </div>
  );
}
