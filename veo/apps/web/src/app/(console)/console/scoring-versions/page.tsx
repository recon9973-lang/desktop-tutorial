import type { Metadata } from 'next';
import { Card, DataSourceBadge, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readLatestSpecDesigns, type SpecDesign } from '@/lib/scoring-specs';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { SpecLifecycle } from './SpecLifecycle';
import own from './scoring-versions.module.css';

export const metadata: Metadata = {
  title: '채점 기준 버전',
};

export const dynamic = 'force-dynamic';

/**
 * 채점 기준 버전 + 알고리즘 설계도.
 *
 * 이 화면은 한때 **하드코딩된 1.0.0 목록**을 그렸다 — 실제 발행본이 1.9.0 까지
 * 갔는데 화면은 계속 1.0.0 이라고 말했다(2026-08-02 사용자 발견). 이제 버전·
 * 가중치·상한·등급 전부 API(=발행 명세)에서 실시간으로 읽는다. 이 파일에는
 * 숫자가 한 개도 없다.
 */
export default async function ConsoleScoringVersionsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scoring_spec:read">
      <ConsoleScoringVersionsContent />
    </PermissionGate>
  );
}

async function ConsoleScoringVersionsContent() {
  const outcome = await readLatestSpecDesigns();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>채점 기준 버전</h1>
        <p className={styles.lede}>
          모든 점수는 버전이 붙은 채점 명세로 계산됩니다. 명세가 바뀌면 점수도 달라질 수 있으므로,
          리포트에는 계산에 사용한 버전이 항상 함께 기록됩니다.
        </p>
      </div>

      {/* 발행 이전의 단계까지 — 초안·검토·승인이 여기서 보이고 여기서 넘어간다.
          이 기능은 처음부터 완성돼 있었는데 부를 화면이 없어 "없는 기능" 이었다(0-E). */}
      <SpecLifecycle />

      {!outcome.ok ? (
        <ErrorState
          title="발행된 명세를 불러오지 못했습니다"
          description={outcome.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : (
        <>
          <section className={styles.section} aria-labelledby="specs-heading">
            <h2 id="specs-heading" className={styles.sectionTitle}>
              발행된 명세 (최신)
            </h2>
            <div className={styles.gridTwo}>
              {outcome.data.map((spec) => (
                <SpecCard key={spec.specId} spec={spec} />
              ))}
            </div>
          </section>

          {outcome.data.map((spec) => (
            <DesignSection key={spec.specId} spec={spec} />
          ))}
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
        </ul>
      </section>
    </div>
  );
}

function SpecCard({ spec }: { readonly spec: SpecDesign }) {
  return (
    <Card
      title={spec.specId === 'veo.seo.readiness' ? 'SEO 기술 준비도' : 'GEO 준비도'}
      headingLevel={3}
      description={spec.meaningKo}
      footer={<DataSourceBadge source="CALCULATED" collectedAt={spec.effectiveAt} />}
    >
      <dl className={styles.definitionList}>
        <div className={styles.definitionRow}>
          <dt>명세 ID</dt>
          <dd>
            <span className={styles.token}>{spec.specId}</span>
          </dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>버전</dt>
          <dd>
            <b>{spec.version}</b>
          </dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>상태</dt>
          <dd>{spec.status === 'PUBLISHED' ? '발행됨' : spec.status}</dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>방법론</dt>
          <dd>{spec.methodologyOwner}</dd>
        </div>
        <div className={styles.definitionRow}>
          <dt>구현</dt>
          <dd>{spec.implementationOwner}</dd>
        </div>
      </dl>
    </Card>
  );
}

/**
 * 알고리즘 설계도 — 이 명세가 점수를 만드는 방법 전부, 명세의 실제 값으로.
 *
 * 산식 요약(정적 문장)과 숫자(명세 값)를 구분한다: 문장은 설계 문서(SEO_SCORING_
 * ALGORITHM_V2.md · SEO_SCORING_V3_PAGES.md)의 요약이고, 숫자는 전부 위에서 읽은
 * 발행 명세의 것이다.
 */
function DesignSection({ spec }: { readonly spec: SpecDesign }) {
  const scoring = spec.stages.filter((stage) => stage.contributesToScore);
  const outside = spec.stages.filter((stage) => !stage.contributesToScore);
  const gates = scoring.filter((stage) => stage.isGate);
  const quality = scoring.filter((stage) => !stage.isGate);

  return (
    <section className={styles.section} aria-labelledby={`design-${spec.specId}`}>
      <h2 id={`design-${spec.specId}`} className={styles.sectionTitle}>
        알고리즘 설계도 — {spec.specId === 'veo.seo.readiness' ? 'SEO' : 'GEO'}{' '}
        {spec.version}
      </h2>

      <p className={own.formula}>
        점수 = <b>도달률</b>(관문 단계의 곱셈) x <b>품질</b>(단계 점수의 가중 평균)
      </p>
      <p className={own.formulaNote}>
        관문이 막히면 뒤 단계가 통째로 무의미해지므로 관문은 배점이 아니라 곱셈입니다.
        해당 없음은 분모에서 빠지고, 측정 불가는 분모에 남아 0점이며
        {spec.hasNotSampled
          ? ', 표본 밖(정책상 안 잰 것)은 감점 없이 따로 표기됩니다'
          : ''}
        .{' '}
        {spec.breadthExponent === 1 ? null : (
          <>
            결함이 퍼진 범위는 <b>{spec.breadthExponent}승</b>으로 감점에 반영됩니다 —
            템플릿 하나의 결함이 여러 장에 퍼지는 구조를 반영합니다.{' '}
          </>
        )}
        주의는 실패의 <b>{Math.round(spec.warningPenaltyMultiplier * 100)}%</b>만큼
        잃습니다.
      </p>

      <h3 className={own.subhead}>검색 여정 단계와 가중치</h3>
      <table className={own.stageTable}>
        <thead>
          <tr>
            <th scope="col">단계</th>
            <th scope="col">역할</th>
            <th scope="col">가중치</th>
            <th scope="col">검사 수</th>
          </tr>
        </thead>
        <tbody>
          {gates.map((stage) => (
            <tr key={stage.id}>
              <th scope="row">{stage.nameKo}</th>
              <td>관문 — 점수에 곱한다</td>
              <td>x</td>
              <td>{stage.checkCount}</td>
            </tr>
          ))}
          {quality.map((stage) => (
            <tr key={stage.id}>
              <th scope="row">{stage.nameKo}</th>
              <td>품질</td>
              <td>{stage.weight}</td>
              <td>{stage.checkCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {outside.length > 0 ? (
        <p className={own.outsideNote}>
          점수 밖 영역 {outside.map((stage) => stage.nameKo).join(' · ')} — 연동이
          있어야 잴 수 있어 판정만 하고 점수에 넣지 않습니다.
        </p>
      ) : null}

      {spec.measurementScope !== null ? (
        <>
          <h3 className={own.subhead}>측정 범위 (이 판부터 명세가 선언)</h3>
          <ul className={styles.list}>
            <li>
              한 진단은 최대 <b>{spec.measurementScope.maxPages}장</b>, 깊이{' '}
              <b>{spec.measurementScope.maxDepth}</b>까지 가져옵니다.
            </li>
            <li>
              게시판형(자동 생성) 페이지는 상한 초과가 예상될 때만 그룹당{' '}
              <b>{spec.measurementScope.templateGroupSample}장</b> 표본으로 줄입니다.
            </li>
            <li>
              잘린 크롤에서는 &ldquo;없다&rdquo;는 주장(중복 없음 등)을 측정 불가로
              판정합니다.
            </li>
          </ul>
          {spec.measurementScope.rationaleKo === null ? null : (
            <details className={own.rationale}>
              <summary>왜 이 값인가 — 명세의 근거 그대로</summary>
              <p>{spec.measurementScope.rationaleKo}</p>
            </details>
          )}
        </>
      ) : null}

      {spec.sampling !== null && spec.sampling.perfLabMaxUrls !== null ? (
        <>
          <h3 className={own.subhead}>성능 표본 정책</h3>
          <ul className={styles.list}>
            <li>
              실험실 성능은 중요도 상위 <b>{spec.sampling.perfLabMaxUrls}장</b>만
              실측합니다
              {spec.sampling.perfLabCheckCount > 0 ? (
                <>
                  {' '}
                  (대상 검사 <b>{spec.sampling.perfLabCheckCount}개</b> — 표본 밖
                  페이지는 감점 없이 &ldquo;표본 밖 — 요청 시 측정&rdquo;)
                </>
              ) : null}
              .
            </li>
            {spec.sampling.perfFieldCheckCount > 0 ? (
              <li>
                실사용자 성능 검사 <b>{spec.sampling.perfFieldCheckCount}개</b>는
                사이트 전체(origin) 값만 쓰므로 표본 문제가 없습니다.
              </li>
            ) : null}
          </ul>
          {spec.sampling.rationaleKo === null ? null : (
            <details className={own.rationale}>
              <summary>왜 표본인가 — 명세의 근거 그대로</summary>
              <p>{spec.sampling.rationaleKo}</p>
            </details>
          )}
        </>
      ) : null}

      {spec.caps.length > 0 ? (
        <>
          <h3 className={own.subhead}>점수 상한</h3>
          <ul className={styles.list}>
            {spec.caps.map((cap) => (
              <li key={cap.id}>
                <b>{cap.maxOverallScore}점 상한</b> — {cap.reasonKo}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {spec.bands.length > 0 ? (
        <>
          <h3 className={own.subhead}>등급 구간</h3>
          <ul className={own.bands}>
            {spec.bands.map((band) => (
              <li key={band.id}>
                <b>{band.labelKo}</b>
                <span>
                  {band.min} – {band.max}
                </span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {spec.changelog.length > 0 ? (
        <>
          <h3 className={own.subhead}>개정 이력 (최근 3판)</h3>
          {spec.changelog.slice(0, 3).map((entry) => (
            <details key={entry.version} className={own.rationale}>
              <summary>
                {entry.version} · {entry.date}
              </summary>
              <p className={own.changelogBody}>{entry.summary}</p>
            </details>
          ))}
        </>
      ) : null}

      <p className={own.designFootnote}>
        설계 근거 문서: docs/research/SEO_SCORING_ALGORITHM_V2.md ·
        SEO_SCORING_V3_PAGES.md · docs/scoring/methodology.md (저장소). 이 화면의
        숫자는 전부 발행 명세 {spec.version} 에서 읽은 값입니다.
      </p>
    </section>
  );
}
