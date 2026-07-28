import Link from 'next/link';
import { ErrorState } from '@veo/ui';

import { MAIN_LANDMARK_ID } from '@/components/SkipLink';
import styles from '@/styles/page.module.css';

export interface ConsoleOutageProps {
  reason: 'UNAVAILABLE' | 'NOT_CONFIGURED';
}

const COPY: Record<ConsoleOutageProps['reason'], { title: string; description: string }> = {
  UNAVAILABLE: {
    title: '인증 서버에 연결하지 못했습니다',
    description:
      '로그인 상태를 확인할 수 없어 콘솔을 열지 못했습니다. 로그아웃된 것은 아니므로 비밀번호를 다시 입력할 필요는 없습니다. 잠시 후 새로고침해 주세요.',
  },
  NOT_CONFIGURED: {
    title: '인증 서버가 연결되지 않았습니다',
    description:
      '이 배포에는 인증 서버 주소가 설정되어 있지 않아 로그인 상태를 확인할 수 없습니다. 운영자에게 문의해 주세요.',
  },
};

/**
 * What the console shows when it cannot find out who is calling.
 *
 * Rendered instead of the console — not instead of the data inside it, and not
 * as a redirect to the sign-in form. Sending someone to `/login` here would
 * present an outage as a credentials problem and invite them to retype a
 * password that was never wrong. Nothing is guessed about the session: the
 * console simply does not open.
 */
export function ConsoleOutage({ reason }: ConsoleOutageProps) {
  const copy = COPY[reason];

  return (
    <main
      id={MAIN_LANDMARK_ID}
      tabIndex={-1}
      className={`${styles.page} ${styles.narrow}`}
    >
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>지금은 콘솔을 열 수 없습니다</h1>
      </div>

      <ErrorState
        title={copy.title}
        description={copy.description}
        action={<Link href="/">공개 점검 도구로 돌아가기</Link>}
      />
    </main>
  );
}
