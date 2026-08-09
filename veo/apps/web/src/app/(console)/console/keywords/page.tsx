import type { Metadata } from 'next';
import {
  Card,
  DATA_SOURCES,
  DATA_SOURCE_DESCRIPTIONS_KO,
  DATA_SOURCE_LABELS_KO,
  EmptyState,
} from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readRecentKeywords } from '@/lib/keywords';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { LookupForm } from './LookupForm';
import own from './keywords.module.css';

export const metadata: Metadata = {
  title: '키워드',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleKeywordsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="keyword:read">
      <ConsoleKeywordsContent />
    </PermissionGate>
  );
}

async function ConsoleKeywordsContent() {
  const recent = await readRecentKeywords();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>네이버 키워드</h1>
        <p className={styles.lede}>
          네이버 검색 수요와 경쟁 상황을 확인합니다. 값마다 어느 출처에서 언제 수집했는지를
          함께 표시하며, 서로 다른 출처의 값을 하나로 합쳐 표시하지 않습니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="keywords-lookup-heading">
        <h2 id="keywords-lookup-heading" className={styles.sectionTitle}>
          키워드 조회
        </h2>
        <LookupForm />
      </section>

      <MindmapLink />

      {recent.ok && recent.data.entries.length > 0 ? (
        <section className={styles.section} aria-labelledby="keywords-recent-heading">
          <h2 id="keywords-recent-heading" className={styles.sectionTitle}>
            {recent.data.title_ko}
          </h2>
          {/*
            네이버가 발표하는 인기검색어 순위가 아니다. 우리 사용자가 최근 무엇을
            조회했는지일 뿐이고, 그렇게 적지 않으면 없는 권위를 빌려 쓰게 된다.
          */}
          <p className={styles.callout}>
            VEO 사용자가 최근 {recent.data.window_hours}시간 동안 조회한 키워드입니다.{' '}
            <strong>네이버가 발표하는 인기 순위가 아닙니다.</strong>
          </p>
          <ul className={own.recentList}>
            {recent.data.entries.map((entry) => (
              <li key={entry.normalized_keyword} className={own.recentItem}>
                {entry.normalized_keyword} · {entry.lookup_count}회
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={styles.section} aria-labelledby="keywords-source-heading">
        <h2 id="keywords-source-heading" className={styles.sectionTitle}>
          출처 표기 규칙
        </h2>
        <Card title="출처 구분" headingLevel={3}>
          <dl className={styles.definitionList}>
            {DATA_SOURCES.map((source) => (
              <div key={source} className={styles.definitionRow}>
                <dt>{DATA_SOURCE_LABELS_KO[source]}</dt>
                <dd>{DATA_SOURCE_DESCRIPTIONS_KO[source]}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <p className={styles.callout}>
          데이터랩 지수는 조건에 따라 정규화된 상대값입니다. 검색광고 API의 조회수와 같은 축에
          놓고 비교하지 않으며, 두 값을 곱하거나 더해 새로운 지표를 만들지 않습니다.
        </p>
      </section>

      {recent.ok ? null : (
        <EmptyState description="최근 조회 이력을 불러오지 못했습니다. 조회 자체는 위에서 바로 하실 수 있습니다." />
      )}
    </div>
  );
}

/**
 * 키워드 마인드맵 — **여기서 만들지 않고 ERP 로 보낸다.**
 *
 * ## 왜 링크인가
 *
 * 사장님이 그린 사슬에 마인드맵이 있다(2026-08-09) — *"키워드에서 관련 질문이 나오고
 * 키워드 마인드맵이 나오고…"*. 그런데 **베놈 ERP 의 journeymap 이 이미 그것을 한다.**
 * 시드 확장 · 네이버·구글 자동완성 재귀 수집 · 여정 4단계 분류 · 의료광고법 리스크 ·
 * ReactFlow 지도 · PNG/SVG/CSV 내보내기가 다 있고 배포까지 되어 있다.
 *
 * 지침서 0-D — **있는 것을 다시 만들지 않는다.** 여기에 두 번째 마인드맵을 지으면
 * 두 지도가 서로 다른 답을 내는 날이 온다(사장님 결정 2026-08-10: *"이 부분 이미
 * erp에 있어 일단 A로 하고"*).
 *
 * ## 왜 새 창인가 · 왜 키워드를 안 실어 보내나
 *
 * **다른 시스템이다.** ERP 로그인이 따로 필요하고, 이 창을 그쪽으로 바꿔 버리면 여기서
 * 보던 조회 결과가 사라진다.
 *
 * 키워드를 주소에 실어 보내지 않는다 — [실측] 그쪽 화면이 주소로 키워드를 받는 자리를
 * 갖고 있지 않다. 받지도 않는 값을 붙여 보내면 링크만 지저분해지고, 나중에 그쪽이
 * 그 이름으로 다른 것을 받게 되면 엉뚱하게 동작한다.
 */
function MindmapLink() {
  return (
    <section className={styles.section} aria-labelledby="keywords-mindmap-heading">
      <h2 id="keywords-mindmap-heading" className={styles.sectionTitle}>
        키워드 마인드맵
      </h2>
      <Card title="검색여정 마인드맵은 ERP 에 있습니다" headingLevel={3} tone="flat">
        <p className={own.mindmapNote}>
          메인 키워드를 넣으면 환자의 검색여정(탐색 → 비교 → 결정 → 유지)을 지도로
          그려 줍니다. 자동완성으로 연관 검색어를 모으고, 의료광고법에 걸릴 표현도 함께
          표시합니다. VEO 에 같은 것을 다시 만들지 않습니다.
        </p>
        <p className={own.mindmapNote}>
          <a
            className={own.mindmapLink}
            href="https://erp.seokorea.org/journeymap"
            target="_blank"
            rel="noreferrer"
          >
            JourneyMap 열기
          </a>
          {' — 새 창으로 열리며 ERP 로그인이 따로 필요합니다.'}
        </p>
      </Card>
    </section>
  );
}
