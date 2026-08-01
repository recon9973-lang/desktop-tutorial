import type { Metadata } from 'next';

import styles from '@/styles/page.module.css';

import { SeoChecker } from './SeoChecker';

export const metadata: Metadata = {
  title: 'SEO·GEO 점수 체크',
  description:
    '주소 하나로 검색엔진과 AI 답변 엔진이 사이트를 읽을 수 있는지 확인합니다. 검색 순위 예측이 아닙니다.',
};

export default function SeoToolPage() {
  return (
    <div className={styles.page}>
      <SeoChecker />
    </div>
  );
}
