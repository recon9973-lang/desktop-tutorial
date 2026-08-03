import type { Metadata } from 'next';
import Link from 'next/link';
import { EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readDashboard, type DashboardData, type SiteStatus } from '@/lib/dashboard';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import own from './dashboard.module.css';

/**
 * 로그인 직후의 화면 — **오늘 어디부터 볼까**.
 *
 * 여기는 일을 시작하는 곳이다. 한때 아직 아무것도 재지 않은 상태의 빈 점수 카드가 놓여
 * 있었고("측정 불가 · 측정 범위 0%"), 고장난 도구처럼 읽혔다. 그래서 없는 숫자를 지어내
 * 채우지 않기로 하고 목록만 남겼는데 — 이번에는 **업체 이름과 주소만** 남았다. 그것은
 * 업체 관리 화면이 이미 하는 일이라, 아침에 열어서 할 일을 정할 수는 없었다(사용자 지적).
 *
 * 그래서 **다른 탭이 이미 갖고 있는 값**을 모은다. 새로 재지 않는다 — 대시보드가 자기만의
 * 측정을 하면 진단 화면의 숫자와 어긋나는 날이 오고, 그때 어느 쪽을 믿을지 알 수 없다(0-D).
 *
 * 없는 숫자를 지어내지 않는다는 원래 규칙은 그대로다: 재지 않은 사이트는 0점이 아니라
 * "측정 없음" 이고, 평균의 분모에도 들어가지 않는다.
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
          맡고 있는 거래처의 지금 상태입니다. 점수가 낮은 곳과 아직 재지 않은 곳이 위로
          옵니다 — 오늘 어디부터 볼지 정하는 화면입니다.
        </p>
      </div>

      {data === null ? (
        <ErrorState
          title="현황을 불러오지 못했습니다"
          description="서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오."
        />
      ) : data.sites.length === 0 ? (
        <EmptyState description="아직 등록된 측정 주소가 없습니다. 업체 관리에서 주소를 추가하면 여기에 나타납니다." />
      ) : (
        <>
          <Figures data={data} />
          <Spread sites={data.sites} />
          <SiteTable sites={data.sites} />
        </>
      )}
    </div>
  );
}

/** 숫자 넷. 각각이 다른 질문에 답한다 — 겹치는 것을 나란히 두면 세 번 읽어야 한다. */
function Figures({ data }: { readonly data: DashboardData }) {
  return (
    <section className={own.figures} aria-label="현황 요약">
      <div className={own.figure}>
        <span className={own.figureLabel}>맡은 곳</span>
        <b className={own.figureValue}>{data.sites.length}</b>
        <span className={own.figureNote}>업체 {data.companyCount}곳</span>
      </div>

      <div className={own.figure}>
        <span className={own.figureLabel}>평균 점수</span>
        <b className={own.figureValue}>
          {data.averageScore === null ? '—' : data.averageScore.toFixed(1)}
        </b>
        {/* 분모를 함께 적는다. 재지 않은 곳을 0으로 넣으면 평균이 조용히 내려간다. */}
        <span className={own.figureNote}>
          잰 {data.measuredCount}곳 기준
          {data.unmeasuredCount > 0 ? ` · 미측정 ${data.unmeasuredCount}곳 제외` : ''}
        </span>
      </div>

      <div className={data.staleCount > 0 ? own.figureWarn : own.figure}>
        <span className={own.figureLabel}>14일 넘게 방치</span>
        <b className={own.figureValue}>{data.staleCount}</b>
        <span className={own.figureNote}>다시 잴 때가 지났습니다</span>
      </div>

      <div className={data.droppedCount > 0 ? own.figureFail : own.figure}>
        <span className={own.figureLabel}>직전보다 하락</span>
        <b className={own.figureValue}>{data.droppedCount}</b>
        <span className={own.figureNote}>
          {data.improvedCount > 0
            ? `상승 ${data.improvedCount}곳 · 같은 명세끼리만 비교`
            : '같은 명세끼리만 비교'}
        </span>
      </div>
    </section>
  );
}

/** 점수 구간별로 몇 곳인가. 평균 하나로는 "고르게 낮은지, 몇 곳만 나쁜지" 를 못 읽는다. */
const BANDS = [
  { id: 'low', label: '50점 미만', min: 0, max: 50, className: 'bandLow' },
  { id: 'mid', label: '50–70', min: 50, max: 70, className: 'bandMid' },
  { id: 'good', label: '70–90', min: 70, max: 90, className: 'bandGood' },
  { id: 'high', label: '90 이상', min: 90, max: 101, className: 'bandHigh' },
] as const;

function Spread({ sites }: { readonly sites: readonly SiteStatus[] }) {
  const measured = sites.filter((site) => site.score !== null);
  if (measured.length === 0) return null;

  const counts = BANDS.map((band) => ({
    ...band,
    count: measured.filter(
      (site) => (site.score ?? 0) >= band.min && (site.score ?? 0) < band.max,
    ).length,
  }));

  return (
    <section className={own.spread} aria-label="점수 분포">
      <h2 className={own.sectionTitle}>점수 분포</h2>
      <ul className={own.spreadList}>
        {counts.map((band) => (
          <li key={band.id} className={own.spreadRow}>
            <span className={own.spreadLabel}>{band.label}</span>
            <span className={own.spreadTrack}>
              <span
                className={own[band.className]}
                style={{ width: `${(band.count / measured.length) * 100}%` }}
              />
            </span>
            {/* 색만으로 알리지 않는다 — 개수가 함께 있다(기획서 §12.1). */}
            <b className={own.spreadCount}>{band.count}</b>
          </li>
        ))}
      </ul>
      <p className={own.spreadNote}>
        잰 {measured.length}곳 기준입니다. 평균 하나로는 고르게 낮은지, 몇 곳만 나쁜지를
        구분할 수 없습니다.
      </p>
    </section>
  );
}

function SiteTable({ sites }: { readonly sites: readonly SiteStatus[] }) {
  return (
    <section className={own.tableSection} aria-label="거래처별 현황">
      <h2 className={own.sectionTitle}>거래처별 — 볼 순서대로</h2>
      <ul className={own.rows}>
        {sites.map((site) => (
          <li key={site.siteId}>
            <Link href={`/console/seo?site=${site.siteId}`} className={own.row}>
              <span className={own.rowScore}>
                {site.score === null ? '—' : site.score.toFixed(1)}
              </span>
              <span className={own.rowWho}>
                <span className={own.rowName}>{site.label}</span>
                <span className={own.rowCompany}>{site.company}</span>
              </span>
              <span className={own.rowMarks}>
                {site.delta === null ? null : site.delta <= -0.1 ? (
                  <span className={own.markDrop}>▼{Math.abs(site.delta).toFixed(1)}</span>
                ) : site.delta >= 0.1 ? (
                  <span className={own.markRise}>▲{site.delta.toFixed(1)}</span>
                ) : null}
                {/* 잰 적 없는 것과 오래된 것은 다른 말이다. 둘을 같은 배지로 접지 않는다. */}
                {site.daysSince === null ? (
                  <span className={own.markNever}>측정 없음</span>
                ) : site.daysSince >= 14 ? (
                  <span className={own.markStale}>{site.daysSince}일 경과</span>
                ) : null}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
