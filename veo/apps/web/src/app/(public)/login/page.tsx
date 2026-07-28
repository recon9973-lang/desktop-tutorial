import type { Metadata } from 'next';
import { Card } from '@veo/ui';

import { safeNextPath } from '@/lib/next-path';
import pageStyles from '@/styles/page.module.css';
import { LoginForm } from './LoginForm';

export const metadata: Metadata = {
  title: '콘솔 로그인',
  description: 'VEO 콘솔 로그인 화면입니다.',
  robots: { index: false, follow: false },
};

// The sign-in form must never be served from a cache.
export const dynamic = 'force-dynamic';

interface LoginPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  // Validated here, and again in the route handler before it is used.
  const nextPath = safeNextPath(params['next']);

  return (
    <div className={`${pageStyles.page} ${pageStyles.narrow}`}>
      <div className={pageStyles.header}>
        <p className={pageStyles.eyebrow}>콘솔</p>
        <h1 className={pageStyles.title}>로그인</h1>
        <p className={pageStyles.lede}>
          콘솔은 로그인한 사용자만 사용할 수 있습니다. 로그인하면 계정에 부여된 권한만큼의
          화면이 열립니다.
        </p>
      </div>

      <Card title="계정으로 로그인" headingLevel={2}>
        <LoginForm nextPath={nextPath} />
      </Card>

      <p className={pageStyles.callout}>
        비밀번호를 잊었거나 계정이 없다면 조직의 콘솔 관리자에게 문의하세요. 이 화면에서는
        계정을 새로 만들 수 없습니다.
      </p>
    </div>
  );
}
