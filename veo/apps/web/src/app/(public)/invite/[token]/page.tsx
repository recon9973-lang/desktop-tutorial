import type { Metadata } from 'next';
import { Card } from '@veo/ui';

import pageStyles from '@/styles/page.module.css';
import { InviteForm } from './InviteForm';

export const metadata: Metadata = {
  title: '비밀번호 설정',
  description: 'VEO 콘솔 초대 링크로 비밀번호를 설정합니다.',
  // Never indexed. An invitation URL in a search result is an invitation given away.
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

interface InvitePageProps {
  params: Promise<{ token: string }>;
}

export default async function InvitePage({ params }: InvitePageProps) {
  const { token } = await params;

  return (
    <div className={`${pageStyles.page} ${pageStyles.narrow}`}>
      <div className={pageStyles.header}>
        <p className={pageStyles.eyebrow}>콘솔 초대</p>
        <h1 className={pageStyles.title}>비밀번호 설정</h1>
        <p className={pageStyles.lede}>
          관리자가 계정을 만들었습니다. 사용할 비밀번호는 본인이 직접 정합니다 — 관리자도
          알 수 없습니다.
        </p>
      </div>

      <Card title="새 비밀번호 정하기" headingLevel={2}>
        <InviteForm token={token} />
      </Card>

      <p className={pageStyles.callout}>
        이 링크는 한 번만 사용할 수 있고 기간이 지나면 만료됩니다. 사용할 수 없다면 관리자에게
        새 링크를 요청해 주세요.
      </p>
    </div>
  );
}
