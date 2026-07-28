'use client';

import { Button, ErrorState } from '@veo/ui';

import styles from '@/styles/page.module.css';

/**
 * Error boundary for console pages.
 *
 * A failure to resolve the session is handled one level up, in the console
 * layout, which renders the outage screen instead of this. What lands here is an
 * unexpected fault inside a page — reported as exactly that, with the digest so
 * it can be matched against a server log. No session claim is made either way.
 */
export default function ConsoleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className={`${styles.page} ${styles.narrow}`}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>화면을 표시하지 못했습니다</h1>
      </div>

      <ErrorState
        title="예상하지 못한 오류가 발생했습니다"
        description="이 화면을 구성하는 중 오류가 생겼습니다. 로그인 상태에는 영향이 없습니다. 다시 시도해도 같은 문제가 반복되면 아래 오류 코드와 함께 운영자에게 알려 주세요."
        {...(error.digest === undefined ? {} : { code: error.digest })}
        action={
          <Button type="button" onClick={reset}>
            다시 시도
          </Button>
        }
      />
    </div>
  );
}
