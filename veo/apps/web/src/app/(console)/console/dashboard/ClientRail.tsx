import Link from 'next/link';
import { formatCount, formatScore } from '@veo/ui';

import type { ClientRow } from '@/lib/dashboard';
import styles from '@/styles/page.module.css';

import own from './dashboard.module.css';

/**
 * 거래처 레일 — **평균에 가려진 이름을 되살린다.**
 *
 * 위쪽 영역 줄은 "진단 67.78점" 처럼 맡은 곳 전부를 숫자 하나로 뭉갠다. 그것은 "뭐가
 * 밀렸나" 에는 답하지만 **"어느 거래처가"** 에는 답하지 못하고, 대행사 화면에서는 그
 * 물음이 먼저다.
 *
 * 사이드바를 한 벌 더 만드는 것이 아니다 — 줄마다 사이드바가 말할 수 없는 **점수와
 * 방치 일수**를 들고 있다(0-D). 누르면 그 거래처의 현황 화면으로 간다.
 *
 * 순서를 정하는 규칙은 자료 층에 있다(`lib/dashboard.ts` 의 `clientRows`). 화면은
 * 받은 순서대로 그린다 — 두 곳에서 정렬하면 반드시 어긋난다.
 */

/** 며칠이면 오래된 것으로 보나 — `lib/dashboard.ts` 의 `STALE_DAYS` 와 같은 값이다. */
const STALE_DAYS = 14;

type Tone = 'plain' | 'warn' | 'fail';

const TONE_CLASS = { plain: 'rowPlain', warn: 'rowWarn', fail: 'rowFail' } as const;

export function clientTone(row: ClientRow): Tone {
  // 한 번도 안 잰 곳은 "오래됨" 보다 무겁다. 시작조차 안 한 자리다.
  if (row.unmeasuredSites > 0 || row.ageDays === null) return 'fail';
  return row.ageDays >= STALE_DAYS ? 'warn' : 'plain';
}

export function clientNote(row: ClientRow): string {
  // 밀린 것을 먼저 말한다. 둘 다 아니면 마지막으로 잰 날을 말한다 — 아무 말도 없으면
  // "확인했다" 와 "빈 줄" 이 같아 보인다.
  if (row.unmeasuredSites > 0) return `아직 안 잰 주소 ${formatCount(row.unmeasuredSites)}곳`;
  if (row.ageDays === null) return '한 번도 진단하지 않았습니다';
  if (row.ageDays >= STALE_DAYS) return `${formatCount(row.ageDays)}일 지났습니다`;
  return row.ageDays === 0 ? '오늘 진단했습니다' : `${formatCount(row.ageDays)}일 전 진단`;
}

export function ClientRail({ rows }: { readonly rows: readonly ClientRow[] }) {
  if (rows.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="clients">
      <h2 id="clients" className={styles.sectionTitle}>
        거래처
      </h2>
      <ul className={own.areas}>
        {rows.map((row) => (
          <li key={row.customerId}>
            <Link
              href={`/console/customers/${row.customerId}`}
              className={`${own.row} ${own[TONE_CLASS[clientTone(row)]]}`}
            >
              <span className={own.who}>
                <span className={own.label}>{row.name}</span>
                <span className={own.hint}>측정 주소 {formatCount(row.siteCount)}곳</span>
              </span>

              <span className={own.figure}>
                {/* 못 잰 곳은 `formatScore` 가 "—" 를 낸다. 0.00 으로 그리면 "쟀는데
                    0 점" 과 구별되지 않는다. */}
                <b className={own.value}>{formatScore(row.score)}</b>
                {row.score === null ? null : <span className={own.unit}>점</span>}
              </span>

              <span className={own.note}>{clientNote(row)}</span>
              <span className={own.chevron} aria-hidden="true">
                ›
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
