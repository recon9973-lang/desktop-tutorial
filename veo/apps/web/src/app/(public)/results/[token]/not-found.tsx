import Link from 'next/link';
import { EmptyState } from '@veo/ui';

import styles from '@/styles/page.module.css';

/**
 * 만료·부재 공유 링크의 404. 엔진은 "없던 토큰"과 "만료된 토큰"을 구분해 주지
 * 않으므로(존재 확인 창구가 되지 않기 위해), 화면도 두 경우를 한 문장으로 말한다.
 */
export default function SharedResultNotFound() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>공유 리포트</p>
        <h1 className={styles.title}>이 공유 링크는 만료되었거나 존재하지 않습니다</h1>
        <p className={styles.lede}>
          공유 링크는 발급 후 일정 기간이 지나면 만료됩니다. 결과가 필요하면 아래에서
          같은 주소를 다시 진단해 새 링크를 만들어 주세요.
        </p>
      </div>
      <EmptyState
        description="저장된 진단 결과를 찾을 수 없습니다."
        action={<Link href="/tools/seo">다시 진단하기</Link>}
      />
    </div>
  );
}
