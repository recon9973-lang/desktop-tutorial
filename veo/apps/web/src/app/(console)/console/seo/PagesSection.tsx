import Link from 'next/link';
import { ErrorState, formatScore } from '@veo/ui';

import {
  readCheckTitles,
  readPageDetail,
  readScanPages,
  type PageDetail,
  type ScanPages,
} from '@/lib/scan-pages';

import own from './seo.module.css';

/**
 * 페이지별 보기 — "어느 페이지를 고칠까" 에 답하는 화면 (⑥, 2026-08-02).
 *
 * 지키는 규칙 셋 (methodology §2.9 · API 문서와 같다):
 *
 * 1. **사이트 점수를 이 화면에 그리지 않는다.** 분모가 다른 두 숫자를 나란히 두면
 *    같은 눈금처럼 읽힌다 — 타사 진단에서 잡아낸 바로 그 결함이다.
 * 2. SITE 판정은 측정 날짜와 함께 따로 — "이 페이지의 문제" 로 읽히면 안 된다.
 * 3. 표본 밖은 감점이 아니다 — 서버 문구를 그대로 단다.
 */
export async function PagesSection({
  scanRunId,
  siteId,
  pageUrl,
}: {
  readonly scanRunId: string;
  readonly siteId: string;
  readonly pageUrl: string | null;
}) {
  const [outcome, titles] = await Promise.all([readScanPages(scanRunId), readCheckTitles()]);
  if (!outcome.ok) {
    return (
      <ErrorState
        title="페이지별 판정을 불러오지 못했습니다"
        description={outcome.message ?? '서버에 연결하지 못했습니다.'}
      />
    );
  }
  const data = outcome.data;
  const base = `/console/seo?site=${siteId}&run=${scanRunId}&view=pages`;

  if (pageUrl !== null) {
    const detail = await readPageDetail(scanRunId, pageUrl);
    if (!detail.ok) {
      return (
        <ErrorState
          title="이 페이지의 판정을 불러오지 못했습니다"
          description={detail.message ?? '서버에 연결하지 못했습니다.'}
        />
      );
    }
    return (
      <PageDetailView
        detail={detail.data}
        data={data}
        titles={titles}
        backHref={base}
      />
    );
  }

  return <PageListView data={data} titles={titles} base={base} />;
}

function PageListView({
  data,
  titles,
  base,
}: {
  readonly data: ScanPages;
  readonly titles: ReadonlyMap<string, string>;
  readonly base: string;
}) {
  return (
    <section aria-label="페이지별 판정 목록">
      <Notes notes={data.notesKo} />
      {data.pages.length === 0 ? (
        <p className={own.pagesEmpty}>
          {data.recordedBeforePageLists
            ? '이 실행에는 페이지별 기록이 없습니다.'
            : '페이지별 판정이 없습니다.'}
        </p>
      ) : (
        <ul className={own.pageList}>
          {data.pages.map((page) => (
            <li key={page.url}>
              <Link
                className={own.pageRow}
                href={`${base}&page=${encodeURIComponent(page.url)}`}
              >
                <span className={own.pageScore}>
                  {formatScore(page.score)}
                </span>
                <span className={own.pageUrl}>{page.url}</span>
                <span className={own.pageCounts}>
                  {page.failed.length > 0 ? (
                    <em className={own.pageFail}>실패 {page.failed.length}</em>
                  ) : null}
                  {page.warned.length > 0 ? (
                    <em className={own.pageWarn}>주의 {page.warned.length}</em>
                  ) : null}
                  <em className={own.pagePass}>통과 {page.passedCount}</em>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <SiteChecks data={data} titles={titles} />
      <p className={own.pagesFootnote}>
        페이지 점수는 그 페이지에서 잰 URL 범위 검사만으로 계산됩니다. 사이트 점수에는
        여러 장을 봐야 아는 검사와 도달률이 더 들어가므로, 두 숫자는 눈금이 다릅니다 —
        나란히 비교하지 마십시오.
      </p>
    </section>
  );
}

function PageDetailView({
  detail,
  data,
  titles,
  backHref,
}: {
  readonly detail: PageDetail;
  readonly data: ScanPages;
  readonly titles: ReadonlyMap<string, string>;
  readonly backHref: string;
}) {
  const name = (id: string) => titles.get(id) ?? id;
  const score = detail.score;
  return (
    <section aria-label="페이지 상세 판정">
      <p>
        <Link href={backHref} className={own.pageBack}>
          ← 페이지 목록
        </Link>
      </p>
      <h2 className={own.pageDetailUrl}>{detail.url}</h2>

      {score === null ? (
        <Notes notes={data.notesKo} />
      ) : (
        <div className={own.pageScoreCard}>
          <div className={own.pageScoreBig}>
            <b>{formatScore(score.score)}</b>
            <span>페이지 점수 · 채점 규칙 {score.specVersion}</span>
          </div>
          {score.score !== null && score.quality !== null ? (
            <p className={own.pageFormula}>
              도달률 <b>{formatScore(score.reach)}</b> x 품질{' '}
              <b>{formatScore(score.quality)}</b> — 손실 합계를 빼면 그대로 검산됩니다
            </p>
          ) : null}
          {score.gateUnverified.length > 0 ? (
            <p className={own.pageGateNote}>
              차단 여부 미확인: {score.gateUnverified.map(name).join(', ')} — 확인하지
              못한 관문은 점수에 곱하지 않았습니다.
            </p>
          ) : null}
          <ul className={own.pageStages}>
            {score.stages.map((stage) => (
              <li key={stage.categoryId}>
                <span>
                  {stage.nameKo}
                  {stage.isGate ? ' · 관문' : ''}
                </span>
                <b>{stage.score === null ? '판정 없음' : formatScore(stage.score)}</b>
              </li>
            ))}
          </ul>
          {score.losses.length > 0 ? (
            <>
              <h3 className={own.pageSubhead}>이 페이지가 잃은 점수</h3>
              <ul className={own.pageLosses}>
                {score.losses.map((loss) => (
                  <li key={loss.checkId}>
                    <span>{name(loss.checkId)}</span>
                    <b>-{formatScore(loss.lost)}점</b>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {score.notSampled.length > 0 ? (
            <p className={own.pageNotSampled}>
              <b>표본 밖 {score.notSampled.length}건</b> —{' '}
              {score.notSampled.map(name).join(', ')}. {score.notSampledNoteKo}
            </p>
          ) : null}
          {score.unmeasured.length > 0 ? (
            <p className={own.pageUnmeasured}>
              측정 불가 {score.unmeasured.length}건 —{' '}
              {score.unmeasured.map(name).join(', ')}. 배점은 분모에 남아 있습니다.
            </p>
          ) : null}
        </div>
      )}

      <CheckList label="실패" ids={detail.failed} titles={titles} tone="fail" />
      <CheckList label="주의" ids={detail.warned} titles={titles} tone="warn" />
      <CheckList label="통과" ids={detail.passed} titles={titles} tone="pass" />

      <SiteChecks data={data} titles={titles} />
    </section>
  );
}

function CheckList({
  label,
  ids,
  titles,
  tone,
}: {
  readonly label: string;
  readonly ids: readonly string[];
  readonly titles: ReadonlyMap<string, string>;
  readonly tone: 'fail' | 'warn' | 'pass';
}) {
  if (ids.length === 0) return null;
  const toneClass =
    tone === 'fail' ? own.pageFail : tone === 'warn' ? own.pageWarn : own.pagePass;
  return (
    <details className={own.pageCheckGroup} open={tone !== 'pass'}>
      <summary>
        <em className={toneClass}>
          {label} {ids.length}
        </em>
      </summary>
      <ul>
        {ids.map((id) => (
          <li key={id}>{titles.get(id) ?? id}</li>
        ))}
      </ul>
    </details>
  );
}

function SiteChecks({
  data,
  titles,
}: {
  readonly data: ScanPages;
  readonly titles: ReadonlyMap<string, string>;
}) {
  if (data.siteChecks.length === 0) return null;
  return (
    <section className={own.siteChecks} aria-label="사이트 전체 단위의 판정">
      <h3 className={own.pageSubhead}>
        사이트 전체 단위의 판정
        {data.measuredAt === null ? null : (
          <span className={own.siteChecksWhen}>
            {' '}
            — {formatDate(data.measuredAt)} 전체 진단 기준
          </span>
        )}
      </h3>
      <p className={own.siteChecksNote}>
        아래는 여러 장을 봐야 아는 판정이라 특정 페이지에 귀속되지 않습니다. 페이지를
        고친 뒤 그 페이지만 다시 재도 이 값은 위 날짜의 전체 진단 값 그대로입니다.
      </p>
      <ul className={own.siteCheckList}>
        {data.siteChecks.map((check) => (
          <li key={check.checkId}>
            <span>{titles.get(check.checkId) ?? check.checkId}</span>
            <em>{check.status}</em>
            {check.reasonKo === null ? null : <small>{check.reasonKo}</small>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Notes({ notes }: { readonly notes: readonly string[] }) {
  if (notes.length === 0) return null;
  return (
    <div>
      {notes.map((note) => (
        <p key={note} className={own.pagesNote}>
          {note}
        </p>
      ))}
    </div>
  );
}

/** SITE 값 날짜는 "YYYY-MM-DD 전체 진단 기준" 표기 — 한국 시각으로 고정한다. */
function formatDate(iso: string): string {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeZone: 'Asia/Seoul',
  }).format(when);
}
