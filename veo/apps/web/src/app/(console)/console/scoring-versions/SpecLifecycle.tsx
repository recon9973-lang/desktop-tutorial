import { Card, EmptyState, ErrorState } from '@veo/ui';

import { listSpecVersions, readSpecVersion, type SpecVersion } from '@/lib/scoring-lab';

import { LifecycleActions } from './LifecycleActions';
import styles from './lab.module.css';

/**
 * 채점 명세의 수명주기 — 초안에서 발행까지.
 *
 * 위쪽 "발행된 명세" 는 **지금 채점에 쓰이는 것**을 보여준다. 이 구역은 그 앞 단계다:
 * 초안이 검토를 거쳐 승인되고 발행되기까지. 두 구역을 나란히 두는 이유는 둘이 다른
 * 질문에 답하기 때문이다 — "지금 무엇으로 채점하나" 와 "다음은 무엇이 오나".
 *
 * 골든 검증 결과를 목록에 함께 보여준다. **아직 안 돌린 것과 통과한 것을 구분한다** —
 * 둘을 같게 그리면 검증 없이 발행하는 길이 열린다.
 */
export async function SpecLifecycle() {
  const outcome = await listSpecVersions();

  if (!outcome.ok) {
    return (
      <ErrorState
        title="명세 버전 목록을 불러오지 못했습니다"
        description={outcome.message ?? '서버에 연결하지 못했습니다.'}
      />
    );
  }

  // 발행된 것은 위 구역이 이미 말한다. 여기서는 아직 가는 중인 것들이 먼저다.
  const inFlight = outcome.data.filter((one) => one.status !== 'RETIRED');

  return (
    <section className={styles.section} aria-labelledby="spec-lifecycle-heading">
      <h2 id="spec-lifecycle-heading" className={styles.sectionTitle}>
        명세 수명주기
      </h2>
      <p className={styles.sectionNote}>
        초안을 검증하고 승인해 발행합니다. 발행된 명세의 숫자는 바뀌지 않습니다 — 고치려면
        새 버전을 냅니다.
      </p>

      {inFlight.length === 0 ? (
        <EmptyState description="아직 등록된 명세 버전이 없습니다." />
      ) : (
        <ul className={styles.versionList}>
          {inFlight.map((version) => (
            <li key={version.id}>
              <VersionCard version={version} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

async function VersionCard({ version }: { readonly version: SpecVersion }) {
  const detail = await readSpecVersion(version.id);

  return (
    <Card title={`${version.specId} ${version.version}`} headingLevel={3} tone="flat">
      <p className={styles.versionMeta}>
        <span className={styles.statusChip}>{version.statusLabel}</span>
        <code className={styles.checksum}>{version.checksum.slice(0, 12)}</code>
      </p>

      {version.changelog === null ? null : (
        <p className={styles.changelog}>{version.changelog}</p>
      )}

      {/* 안 돌린 것과 통과한 것을 구분한다 — 둘을 같게 그리면 검증 없이 발행하게 된다. */}
      <p className={styles.golden}>
        {version.goldenPassed === null
          ? '골든 검증: 아직 실행하지 않았습니다'
          : version.goldenPassed
            ? `골든 검증 통과 — ${version.goldenSummary ?? '차이 없음'}`
            : `골든 검증 실패 — ${version.goldenSummary ?? '차이 있음'}`}
      </p>

      {!detail.ok ? (
        <p className={styles.detailError}>
          이 버전의 상세를 불러오지 못해 할 수 있는 일을 표시할 수 없습니다.
        </p>
      ) : (
        <>
          {detail.data.validationSummary === null ? null : (
            <p className={styles.validation}>{detail.data.validationSummary}</p>
          )}
          <LifecycleActions
            versionId={version.id}
            allowed={detail.data.allowedTransitions}
          />
        </>
      )}
    </Card>
  );
}
