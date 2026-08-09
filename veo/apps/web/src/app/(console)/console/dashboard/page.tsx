import type { Metadata } from 'next';
import Link from 'next/link';
import { ErrorState, formatScore } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readDashboard, type AreaRow } from '@/lib/dashboard';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import own from './dashboard.module.css';

/**
 * 로그인 직후의 화면 — **뭐가 밀려 있나**.
 *
 * 이 자리는 두 번 방향을 틀었다. 처음에는 업체 이름과 주소만 있어 업체 관리와 같은 일을
 * 했고, 다음에는 SEO 점수만 모아서 나머지 영역이 눌러 보기 전에는 보이지 않았다. 지금은
 * **영역마다 자기 숫자를 하나씩** 들고 있고, 누르면 그 탭으로 바로 들어간다(사용자 결정).
 *
 * 왼쪽 사이드바를 한 벌 더 만들지 않는다 — 이름만 나열하면 두 벌이 되고 반드시 어긋난다.
 * 각 줄은 사이드바가 말할 수 없는 숫자를 들고 있어야 자리값을 한다(0-D).
 *
 * 없는 숫자는 지어내지 않는다. 못 읽었거나 아직 없으면 "—" 다 — 0 으로 적으면 "다
 * 처리했다" 로 읽힌다.
 */

export const metadata: Metadata = {
  title: '대시보드',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleDashboardPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <DashboardContent />
    </PermissionGate>
  );
}

async function DashboardContent() {
  const data = await readDashboard();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>대시보드</h1>
        <p className={styles.lede}>
          {data === null
            ? '각 영역에 무엇이 밀려 있는지 모아 보는 화면입니다.'
            : `맡은 측정 주소 ${data.siteCount}곳. 각 줄을 누르면 그 화면으로 바로 갑니다.`}
        </p>
      </div>

      {data === null ? (
        <ErrorState
          title="현황을 불러오지 못했습니다"
          description="서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오."
        />
      ) : (
        <ul className={own.areas}>
          {data.areas.map((area) => (
            <li key={area.key}>
              <Area row={area} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const TONE_CLASS = { plain: 'rowPlain', warn: 'rowWarn', fail: 'rowFail' } as const;

function Area({ row }: { readonly row: AreaRow }) {
  return (
    <Link href={row.href} className={`${own.row} ${own[TONE_CLASS[row.tone]]}`}>
      <span className={own.who}>
        <span className={own.label}>{row.label}</span>
        <span className={own.hint}>{row.hint}</span>
      </span>

      <span className={own.figure}>
        {/* 못 읽었거나 아직 없으면 "—". 0 과 모름을 같은 칸에 두지 않는다. */}
        {/* 점수는 자릿수를 `formatScore` 가 정한다 — 자르고, 반올림하지 않는다.
            건수·백분율은 세는 값이라 천 단위만 끊어 그대로 보인다. */}
        <b className={own.value}>
          {row.value === null
            ? '—'
            : row.unit === '점'
              ? formatScore(row.value)
              : row.value.toLocaleString('ko-KR')}
        </b>
        {row.value === null ? null : <span className={own.unit}>{row.unit}</span>}
      </span>

      <span className={own.note}>{row.note}</span>
      <span className={own.chevron} aria-hidden="true">
        ›
      </span>
    </Link>
  );
}
