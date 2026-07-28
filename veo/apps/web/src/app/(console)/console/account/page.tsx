import type { Metadata } from 'next';
import { Card } from '@veo/ui';

import styles from '@/styles/page.module.css';
import { requireConsoleIdentity } from '@/lib/session';
import { PasswordForm } from './PasswordForm';

export const metadata: Metadata = {
  title: '내 계정',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function AccountPage() {
  // No PermissionGate: every signed-in person may change their own password, and
  // gating it behind a permission would lock out exactly the accounts that have none.
  const identity = await requireConsoleIdentity();

  return (
    <div className={`${styles.page} ${styles.narrow}`}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>내 계정</p>
        <h1 className={styles.title}>비밀번호 변경</h1>
        <p className={styles.lede}>
          {identity.displayName ? `${identity.displayName} 님의 계정입니다. ` : ''}
          비밀번호를 바꾸면 다른 기기에서는 모두 로그아웃됩니다. 지금 사용 중인 이 화면은
          그대로 유지됩니다.
        </p>
      </div>

      <Card title="비밀번호 변경" headingLevel={2}>
        <PasswordForm />
      </Card>
    </div>
  );
}
