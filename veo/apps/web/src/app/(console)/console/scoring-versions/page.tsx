import type { Metadata } from 'next';
import { Card, DataSourceBadge, EmptyState, ErrorState } from '@veo/ui';

import { bySpecFamily, specLabel, type ScoringSpecFamily } from '@/lib/scoring';
import { readScoringSpecs } from '@/lib/scoring-api';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '채점 기준 버전',
};

/** 목록은 엔진의 명세 등록부에서 온다. 빌드 시점에 굳으면 그 순간부터 옛말이 된다. */
export const dynamic = 'force-dynamic';

export default async function ConsoleScoringVersionsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scoring_spec:read">
      <ConsoleScoringVersionsContent />
    </PermissionGate>
  );
}

async function ConsoleScoringVersionsContent() {
  const found = await readScoringSpecs();
  const families = found.ok ? bySpecFamily(found.data) : [];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>채점 기준 버전</h1>
        <p className={styles.lede}>
          모든 점수는 버전이 붙은 채점 명세로 계산됩니다. 명세가 바뀌면 점수도 달라질 수 있으므로,
          리포트에는 계산에 사용한 버전이 항상 함께 기록됩니다. 아래 목록은 점수를 내는 엔진이
          지금 들고 있는 명세 등록부를 그대로 읽은 것입니다.
        </p>
      </div>

      {!found.ok ? (
        <ErrorState
          title="채점 명세를 불러오지 못했습니다"
          description={
            found.message ??
            '엔진의 명세 등록부에 연결하지 못했습니다. 어떤 버전이 적용 중인지 확인되지 않았으므로 이 화면은 값을 표시하지 않습니다.'
          }
        />
      ) : families.length === 0 ? (
        <EmptyState description="엔진에 발행된 채점 명세가 없습니다." />
      ) : (
        <>
          <section className={styles.section} aria-labelledby="specs-heading">
            <h2 id="specs-heading" className={styles.sectionTitle}>
              지금 적용 중인 명세
            </h2>
            <div className={styles.gridTwo}>
              {families.map((family) => (
                <CurrentSpecCard key={family.specId} family={family} />
              ))}
            </div>
          </section>

          <SupersededSection families={families} />
        </>
      )}

      <section className={styles.section} aria-labelledby="specs-policy-heading">
        <h2 id="specs-policy-heading" className={styles.sectionTitle}>
          버전 취급 규칙
        </h2>
        <ul className={styles.list}>
          <li>서로 다른 명세 버전으로 계산한 점수는 직접 비교하지 않습니다.</li>
          <li>가중치·심각도·상한 값은 명세에만 존재하며 화면이나 코드에 복제하지 않습니다.</li>
          <li>발행된 명세는 수정하지 않고 새 버전으로 발행합니다.</li>
          <li>
            어느 버전이 적용 중인지는 화면이 판단하지 않습니다. 점수를 내는 엔진이 지목한 것을
            그대로 표시합니다.
          </li>
        </ul>
      </section>
    </div>
  );
}

function CurrentSpecCard({ family }: { readonly family: ScoringSpecFamily }) {
  const current = family.current;

  if (current === null) {
    return (
      <Card
        title={family.domain}
        headingLevel={3}
        description="이 명세 ID 에는 지금 적용 중인 발행본이 없습니다. 지나간 버전만 남아 있습니다."
      >
        <dl className={styles.definitionList}>
          <div className={styles.definitionRow}>
            <dt>명세 ID</dt>
            <dd>
              <span className={styles.token}>{family.specId}</span>
            </dd>
          </div>
        </dl>
      </Card>
    );
  }

  return (
    <Card
      title={family.domain}
      headingLevel={3}
      description={current.score_meaning_ko}
      footer={<DataSourceBadge source="CALCULATED" collectedAt={current.effective_at} />}
    >
      <dl className={styles.definitionList}>
        <div className={styles.definitionRow}>
          <dt>명세 ID</dt>
          <dd>
            <span className={styles.token}>{current.spec_id}</span>
          </dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>버전</dt>
          <dd>{current.version}</dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>상태</dt>
          <dd>{current.status}</dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>방법론</dt>
          <dd>{current.methodology_owner}</dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>구현</dt>
          <dd>{current.implementation_owner}</dd>
        </div>
        {/*
          검사합계를 적어 두는 이유: 같은 버전 번호로 서로 다른 문서가 돌아다니는 일을
          숫자 하나로 잡아낼 수 있다. 리포트에도 같은 값이 기록된다.
        */}
        <div className={styles.definitionRow}>
          <dt>검사합계</dt>
          <dd>
            <span className={styles.token}>{current.checksum.slice(0, 12)}</span>
          </dd>
        </div>
      </dl>
    </Card>
  );
}

function SupersededSection({
  families,
}: {
  readonly families: readonly ScoringSpecFamily[];
}) {
  const past = families.filter((family) => family.superseded.length > 0);
  if (past.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="specs-history-heading">
      <h2 id="specs-history-heading" className={styles.sectionTitle}>
        지나간 버전
      </h2>
      <p className={styles.callout}>
        이 버전으로 계산된 리포트가 남아 있습니다. 그때의 점수는 그때의 기준으로 읽어야 하므로
        목록에서 지우지 않습니다.
      </p>
      <div className={styles.gridTwo}>
        {past.map((family) => (
          <Card key={family.specId} title={family.domain} headingLevel={3}>
            <ul className={styles.list}>
              {family.superseded.map((spec) => (
                <li key={spec.version}>
                  <span className={styles.token}>{specLabel(spec)}</span> · {spec.status} ·{' '}
                  {spec.effective_at}
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </section>
  );
}
