import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Card, EmptyState, ErrorState, formatCount, formatScore, NOT_MEASURED } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import {
  issuesHref,
  readClientBoard,
  reportsHref,
  type ClientBoard,
  type ObservationSlot,
  type ScaleTrack,
  type SiteBoard,
} from '@/lib/client-dashboard';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import own from './client.module.css';

export const metadata: Metadata = {
  title: '거래처 진단 현황',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * 거래처 한 곳 — **그동안 무슨 일이 있었나.**
 *
 * 자료를 모으는 규칙과 이 화면이 생긴 이유는 `lib/client-dashboard.ts` 머리말에 있다.
 * 여기서는 배치만 정한다.
 *
 * 순서는 **거래처와 마주 앉아 말하는 순서**다 — 지금 몇 점인가, 지난번과 비교해 어떤가,
 * 그래서 무엇이 밀려 있나, 아직 안 켠 것은 무엇인가, 그것을 어떻게 내보내나.
 */
export default async function CustomerBoardPage({
  params,
}: {
  params: Promise<{ customerId: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { customerId } = await params;

  return (
    <PermissionGate identity={identity} permission="customer:read">
      <BoardContent customerId={customerId} />
    </PermissionGate>
  );
}

async function BoardContent({ customerId }: { readonly customerId: string }) {
  const board = await readClientBoard(customerId);
  if (board === null) notFound();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>
          <Link href="/console/customers" className={own.crumb}>
            업체 관리
          </Link>
          {' · 거래처 현황'}
        </p>
        <h1 className={styles.title}>{board.company.name}</h1>
        <p className={styles.lede}>
          {board.company.address ?? '소재지 미등록'}
          {' · 측정 주소 '}
          {formatCount(board.sites.length)}곳
          {board.company.isRegistered ? '' : ' · 아직 거래처로 등록되지 않았습니다'}
        </p>
      </div>

      <SitesSection sites={board.sites} />
      <IssuesSection board={board} />
      <ObservationSection slot={board.observation} />
      <OutputSection board={board} />
    </div>
  );
}

/* ------------------------------------------------------------------ 진단 */

function SitesSection({ sites }: { readonly sites: readonly SiteBoard[] }) {
  return (
    <section className={styles.section} aria-labelledby="sites">
      <h2 id="sites" className={styles.sectionTitle}>
        진단
      </h2>
      {sites.length === 0 ? (
        <EmptyState
          title="측정 주소가 없습니다"
          description="업체 관리 화면에서 주소를 등록하면 이 자리에 점수가 쌓입니다."
        />
      ) : (
        <div className={own.siteGrid}>
          {sites.map((site) => (
            <SiteCard key={site.siteId} site={site} />
          ))}
        </div>
      )}
    </section>
  );
}

function SiteCard({ site }: { readonly site: SiteBoard }) {
  return (
    <Card
      title={site.displayName || site.origin}
      headingLevel={3}
      footer={
        <div className={own.actions}>
          <Link href={`/console/seo?site=${encodeURIComponent(site.siteId)}`}>
            진단 이력
          </Link>
          <Link href={`/console/reports?project=${encodeURIComponent(site.projectId)}`}>
            리포트 만들기
          </Link>
        </div>
      }
    >
      <p className={own.origin}>
        {site.origin}
        {site.isPrimary ? <span className={own.badge}>주 사이트</span> : null}
      </p>
      <ScaleRow track={site.seo} label="SEO" />
      <ScaleRow track={site.geo} label="GEO" />
    </Card>
  );
}

/**
 * 눈금 하나 — 지금 점수, 지난번 대비, 그리고 지난 진단들.
 *
 * **증감은 조건이 같을 때만 그린다.** 명세 판이 바뀌거나 훑은 장수가 달라지면 두 값은
 * 같은 자로 잰 것이 아니고, 그 화살표는 우리가 자를 바꾼 일을 거래처의 개선/악화로
 * 보이게 만든다(ADR 0010). 그때는 화살표 대신 **왜 못 비교하는지**를 적는다.
 */
function ScaleRow({ track, label }: { readonly track: ScaleTrack; readonly label: string }) {
  const latest = track.latest;

  if (latest === null || latest.score === null) {
    return (
      <div className={own.scale}>
        <span className={own.scaleLabel}>{label}</span>
        <span className={own.scaleValue}>{NOT_MEASURED}</span>
        <span className={own.scaleNote}>아직 재지 않았습니다</span>
      </div>
    );
  }

  const previous = track.previous;
  const delta =
    previous !== null && previous.score !== null ? latest.score - previous.score : null;

  return (
    <div className={own.scale}>
      <span className={own.scaleLabel}>{label}</span>
      <span className={own.scaleValue}>{formatScore(latest.score)}</span>
      {delta === null ? (
        <span className={own.scaleNote}>{track.incomparableReasonKo}</span>
      ) : (
        <span className={delta < 0 ? own.deltaDown : own.deltaUp}>
          {/* 부호는 붙이되 값은 자른 그대로. `+0.00` 은 "안 움직였다" 는 사실이다. */}
          {delta < 0 ? '▾ ' : '▴ '}
          {formatScore(Math.abs(delta))}
          <span className={own.deltaFrom}>
            {' '}
            (지난 {formatScore(previous?.score ?? null)})
          </span>
        </span>
      )}
      <Trend history={track.history} />
    </div>
  );
}

/**
 * 지난 진단들 — **막대만 찍고 선을 잇지 않는다.**
 *
 * 이력에는 서로 다른 명세 판·다른 장수로 잰 값이 섞여 있다. 선으로 이으면 그 사이가
 * 연속된 변화처럼 보이는데, 실제로는 자가 바뀐 자리일 수 있다. 막대는 그런 주장을
 * 하지 않는다.
 */
function Trend({ history }: { readonly history: ScaleTrack['history'] }) {
  const points = history.filter((entry) => entry.score !== null).slice(0, 8);
  if (points.length < 2) return null;

  return (
    <ol className={own.trend} aria-label="지난 진단">
      {/* 최신이 오른쪽에 오도록 뒤집는다 — 시간이 왼쪽에서 오른쪽으로 흐르는 것이
          그래프의 관습이고, 목록 순서(최신 먼저)와는 반대다. */}
      {[...points].reverse().map((entry) => (
        <li key={entry.scanRunId} className={own.trendItem}>
          <span
            className={own.trendBar}
            style={{ height: `${entry.score ?? 0}%` }}
            title={`${new Date(entry.startedAt).toLocaleDateString('ko-KR')} · ${formatScore(entry.score)}점 · 명세 ${entry.specVersion}`}
          />
        </li>
      ))}
    </ol>
  );
}

/* ------------------------------------------------------------------ 이슈 */

function IssuesSection({ board }: { readonly board: ClientBoard }) {
  const tally = board.issues;

  return (
    <section className={styles.section} aria-labelledby="issues">
      <h2 id="issues" className={styles.sectionTitle}>
        이슈
      </h2>
      <Card
        title="조치가 필요한 항목"
        headingLevel={3}
        footer={
          <div className={own.actions}>
            {/*
              **이 거래처로 걸러서 보낸다.** 그냥 `/console/issues` 로 보내면 맡은 곳
              전부의 이슈가 나오고, 방금 "열림 12건" 을 읽은 사람이 165건짜리 목록을
              마주한다 — 어느 12건인지 다시 찾아야 한다.

              프로젝트가 여럿인 업체는 거르지 않고 보낸다. 하나만 골라 보내면 나머지가
              조용히 빠지고, 그것이 이 화면의 합계와 어긋난다.
            */}
            <Link href={issuesHref(board)}>이슈 보기</Link>
          </div>
        }
      >
        {tally === null ? (
          <ErrorState
            title="이슈를 불러오지 못했습니다"
            description="일부만 세어 전체인 척 내놓지 않기 위해 합계를 비웠습니다. 새로 고침해 주십시오."
          />
        ) : (
          <dl className={styles.definitionList}>
            <div className={styles.definitionRow}>
              <dt>열린 것</dt>
              <dd>
                {formatCount(tally.open)}건
                {tally.recurring > 0 ? (
                  <span className={own.warn}> · 재발 {formatCount(tally.recurring)}건 포함</span>
                ) : null}
              </dd>
            </div>
            <div className={styles.definitionRow}>
              <dt>닫은 것</dt>
              <dd>
                {formatCount(tally.closed)}건
                {tally.closed === 0 && tally.open > 0 ? (
                  // 이슈는 사람이 "완료" 를 눌러서 닫히지 않는다. 재측정이 통과해야
                  // 닫힌다(`issues/lifecycle.py`). 0 건일 때 그 사실을 적어 두지
                  // 않으면 "아무도 일을 안 했다" 로 읽힌다.
                  <span className={own.hint}>
                    {' '}
                    · 이슈는 재검사가 통과해야 닫힙니다
                  </span>
                ) : null}
              </dd>
            </div>
          </dl>
        )}
      </Card>
    </section>
  );
}

/* -------------------------------------------------------------- AI 답변 */

const SLOT_TITLES: Record<ObservationSlot['state'], string> = {
  NO_ENGINE: '아직 켜지 않았습니다',
  NO_PROMPT_SET: '아직 켜지 않았습니다',
  NEVER_RUN: '아직 한 번도 재지 않았습니다',
  MEASURED: '최근 관측',
};

/**
 * AI 답변 — **비어 있으면 비었다고 쓴다.**
 *
 * 경쟁사 화면은 이 자리가 본체다(언급률·모델별·인용 출처). 우리는 관측을 한 번도 돌린
 * 적이 없다. `0%` 로 채우면 "쟀는데 아무도 언급하지 않았다" 로 읽히는데, 그것은 우리가
 * 재지 않은 것과 전혀 다른 말이다(ADR 0002).
 *
 * 그래서 이 칸은 값 대신 **왜 비었고 무엇을 하면 채워지는지**를 들고 있다. 칸을 아예
 * 감추지 않는 이유는 하나 더 있다 — 빈 자리가 화면에 남아 있어야 이 축을 켤 이유가
 * 매주 눈에 보인다.
 */
function ObservationSection({ slot }: { readonly slot: ObservationSlot }) {
  return (
    <section className={styles.section} aria-labelledby="observation">
      <h2 id="observation" className={styles.sectionTitle}>
        AI 답변
      </h2>
      <Card
        title={SLOT_TITLES[slot.state]}
        headingLevel={3}
        tone={slot.state === 'MEASURED' ? 'default' : 'flat'}
        footer={
          <div className={own.actions}>
            <Link href="/console/geo">GEO · AI 가시성 화면</Link>
          </div>
        }
      >
        {slot.state === 'MEASURED' ? (
          <dl className={styles.definitionList}>
            <div className={styles.definitionRow}>
              <dt>요약</dt>
              <dd>{slot.summaryKo}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt>표본</dt>
              <dd>
                질문 {formatCount(slot.promptCount)}개 × 반복{' '}
                {formatCount(slot.repetitionsPerPrompt)}회
              </dd>
            </div>
            <div className={styles.definitionRow}>
              <dt>끝난 때</dt>
              <dd>
                {slot.finishedAt === null
                  ? '아직 도는 중'
                  : new Date(slot.finishedAt).toLocaleString('ko-KR')}
              </dd>
            </div>
          </dl>
        ) : (
          <>
            <p className={own.why}>{slot.whyKo}</p>
            <p className={own.next}>{slot.nextKo}</p>
            <p className={own.hint}>
              언급률·인용 출처·모델별 비교는 이 축이 돌기 시작하면 이 자리에 채워집니다.
              값이 없는 동안 0%로 적지 않습니다 — 재지 않은 것과 언급이 없는 것은 다른
              말입니다.
            </p>
          </>
        )}
      </Card>
    </section>
  );
}

/* ------------------------------------------------------------------ 출력 */

function OutputSection({ board }: { readonly board: ClientBoard }) {
  const reports = board.reports;
  const reportable = board.reportableRuns;

  return (
    <section className={styles.section} aria-labelledby="output">
      <h2 id="output" className={styles.sectionTitle}>
        출력
      </h2>
      <Card
        title="거래처에 나가는 것"
        headingLevel={3}
        footer={
          <div className={own.actions}>
            <Link href={reportsHref(board)}>리포트 화면</Link>
          </div>
        }
      >
        <dl className={styles.definitionList}>
          <div className={styles.definitionRow}>
            <dt>만든 리포트</dt>
            <dd>
              {reports === null
                ? NOT_MEASURED
                : `${formatCount(reports.total)}건`}
              {reports !== null && reports.unpublished > 0 ? (
                <span className={own.warn}>
                  {' '}
                  · 미발행 {formatCount(reports.unpublished)}건
                </span>
              ) : null}
            </dd>
          </div>
          <div className={styles.definitionRow}>
            <dt>리포트로 만들 수 있는 진단</dt>
            <dd>
              {reportable === null ? NOT_MEASURED : `${formatCount(reportable)}회`}
              {reportable !== null && reportable > 0 && (reports?.total ?? 0) === 0 ? (
                <span className={own.hint}>
                  {' '}
                  · 첫 리포트는 사람이 만들어야 합니다
                </span>
              ) : null}
            </dd>
          </div>
        </dl>
      </Card>
    </section>
  );
}
