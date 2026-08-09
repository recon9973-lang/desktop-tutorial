import { Card, formatPercent, formatScoreWithUnit } from '@veo/ui';

import type { GeoCategory, GeoLookup, GeoReadiness } from '@/lib/observations';

import { ReadinessChecks } from './ReadinessChecks';
import { ReadinessQueue } from './ReadinessQueue';

import styles from './geo.module.css';

/**
 * GEO 준비도 결과.
 *
 * 이 화면이 반드시 지키는 것: **점수와 노출 차단은 나란히 있되 섞이지 않는다.**
 * 95점이면서 동시에 노출 차단일 수 있다 — 구조는 훌륭한데 robots 로 막아 둔 사이트가
 * 정확히 그 모습이다. 차단을 점수에 반영해 깎아 버리면 "무엇을 고쳐야 하는가" 가
 * 사라진다. 하나는 설정 한 줄이고 다른 하나는 몇 주짜리 작업이다.
 */
export function ReadinessReport({
  report,
  severities,
}: {
  readonly report: GeoReadiness;
  /** 검사별 심각도 — 발행 명세에서 읽어 온 것. 없으면 배지를 그리지 않는다. */
  readonly severities?: ReadonlyMap<string, string>;
}) {
  const { readiness, exposure } = report;
  const hasScore = readiness.score !== null;

  // 점수 영역과 참고 영역을 갈라 놓는다. 한 목록에 섞으면 참고 항목이 감점처럼 읽히거나,
  // 반대로 우리가 못 잰 것이 "원래 안 재는 항목" 처럼 읽힌다. 뒤쪽이 더 나쁘다.
  const scored = readiness.categories.filter((one) => one.contributes_to_score);
  const reference = readiness.categories.filter((one) => !one.contributes_to_score);

  return (
    <div className={styles.report}>
      <p className={styles.scopeNotice}>{report.scope_notice_ko}</p>

      {exposure.blocked ? (
        <section className={styles.blocked} aria-label="노출 차단">
          <h3 className={styles.caveatTitle}>AI 엔진이 이 사이트에 접근할 수 없습니다</h3>
          <p className={styles.rateNote}>
            아래 점수와 <strong>별개의 사실</strong>입니다. 점수가 높아도 차단돼 있으면 AI
            답변에 나올 수 없습니다.
          </p>
          <ul className={styles.caveatList}>
            {exposure.gates.map((gate) => (
              <li key={gate.gate_id}>
                <strong>{gate.label_ko}</strong>
                {gate.description_ko === null ? null : ` — ${gate.description_ko}`}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className={hasScore ? styles.rateCard : styles.rateCardUnmeasured}>
        <p className={styles.rateLabel}>GEO 준비도 · {report.target_url}</p>
        {/* 본문은 큰 숫자, 게이지는 우측 레일 — SEO 와 같다.
            v0.3.18 에서 여기에도 게이지를 넣었는데, 레일에 이미 하나가 있어 **같은 값이
            한 화면에 두 번** 나왔다. 게다가 SEO 본문은 큰 숫자라 두 축이 서로 다르게
            보였다(사용자 지적). 게이지는 한 곳에만 둔다. */}
        <p className={hasScore ? styles.rateValue : styles.rateValueUnmeasured}>
          {hasScore ? formatScoreWithUnit(readiness.score) : '점수를 낼 수 없습니다'}
        </p>
        {readiness.band_label_ko === null ? null : (
          <p className={styles.rateDenominator}>{readiness.band_label_ko}</p>
        )}
        <p className={styles.interval}>
          측정 범위 {formatPercent(readiness.coverage)} · 신뢰도{' '}
          {formatPercent(readiness.confidence)} · 채점 규칙 {readiness.spec_version}
        </p>
        <p className={styles.rateMeaning}>{report.summary_ko}</p>
      </div>

      <Card title="영역별" headingLevel={3} tone="flat">
        <ul className={styles.categoryList}>
          {scored.map((category) => (
            <CategoryRow key={category.category_id} category={category} />
          ))}
        </ul>
      </Card>

      {/* "무엇부터" 가 먼저다. 판정 목록은 상태를 말하고, 이 목록은 순서를 말한다. */}
      <ReadinessQueue improvements={report.improvements ?? []} />

      {/* 영역 점수만으로는 무엇을 고칠지 알 수 없다 — 판정과 고침 방법이 이어져야 한다. */}
      <ReadinessChecks
        checks={report.checks ?? []}
        issues={report.issues ?? []}
        severities={severities}
      />

      {reference.length === 0 ? null : (
        <Card title="참고 · 별도 확인 필요" headingLevel={3} tone="flat">
          <p className={styles.rateNote}>
            아래 항목은 <strong>점수에 반영되지 않습니다.</strong> 감점된 것도, 통과한 것도
            아닙니다 — 저희가 확실하게 재지 못하는 영역이라 처음부터 배점에서 빼두었습니다.
          </p>
          <ul className={styles.categoryList}>
            {reference.map((category) => (
              <li key={category.category_id} className={styles.categoryRow}>
                <div className={styles.categoryHead}>
                  <span className={styles.categoryName}>{category.name_ko}</span>
                  <span className={styles.categoryUnmeasured}>점수 미반영</span>
                </div>
                <p className={styles.categoryMeta}>
                  항목 {category.not_applicable_check_ids.length +
                    category.unknown_check_ids.length +
                    category.failing_check_ids.length}
                  개 · 점수에 들어갔다면 {category.weight}점 몫이었을 영역입니다
                </p>
                {category.outside_score_reason_ko === null ? null : (
                  <p className={styles.referenceReason}>{category.outside_score_reason_ko}</p>
                )}
                {report.lookup === null ? null : <Lookup lookup={report.lookup} />}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {report.notes_ko.length > 0 ? (
        <section className={styles.caveats} aria-label="함께 알아야 하는 것">
          <h3 className={styles.caveatTitle}>함께 알아야 하는 것</h3>
          <ul className={styles.caveatList}>
            {report.notes_ko.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className={styles.pending}>
        이 결과는 <strong>저장되지 않습니다.</strong> 화면을 새로 고치면 사라지며, 다시
        보시려면 다시 측정해야 합니다 — 관측 기록과 달리 준비도 진단은 아직 이력이 남지
        않습니다.
      </p>
    </div>
  );
}

/**
 * 한 영역.
 *
 * 못 잰 항목 수를 실패 항목 수와 **같은 자리에** 둔다. 측정 불가를 빼고 보여주면 그
 * 영역이 실제보다 잘 나온 것처럼 읽히는데, 그 배점은 분모에 그대로 남아 있다.
 */
function CategoryRow({ category }: { readonly category: GeoCategory }) {
  const scored = category.score !== null;
  return (
    <li className={styles.categoryRow}>
      <div className={styles.categoryHead}>
        <span className={styles.categoryName}>{category.name_ko}</span>
        <span className={scored ? styles.categoryScore : styles.categoryUnmeasured}>
          {scored ? formatScoreWithUnit(category.score) : '측정 불가'}
        </span>
      </div>
      <p className={styles.categoryMeta}>
        배점 {category.weight}점 · 실패 {category.failing_check_ids.length}개 · 측정 불가{' '}
        {category.unknown_check_ids.length}개 · 해당 없음{' '}
        {category.not_applicable_check_ids.length}개
      </p>
    </li>
  );
}

const CORPUS_LABELS: Record<string, string> = {
  local: '네이버 지역',
  blog: '블로그',
  news: '뉴스',
  cafearticle: '카페',
};

/**
 * 참고 조회가 무엇을 보고 무엇을 버렸는가.
 *
 * **버린 건수를 반드시 함께 보여준다.** 검색하면 수백 건인데 보고서에 몇 개뿐이면,
 * 그 이유를 말해 주지 않는 한 "이 도구가 못 찾았다" 로 읽힌다. 실제로는 이름이 비슷한
 * 다른 업체를 걸러낸 것이고, 그 판단이야말로 사람이 확인해야 하는 부분이다.
 */
function Lookup({ lookup }: { readonly lookup: GeoLookup }) {
  const corpora = Object.entries(lookup.totals);
  const unavailable = Object.entries(lookup.unavailable);

  return (
    <div className={styles.lookup}>
      <p className={styles.lookupHead}>
        {lookup.engine === 'NAVER' ? '네이버' : lookup.engine} 검색 결과
      </p>
      {corpora.length === 0 ? null : (
        <p className={styles.categoryMeta}>
          {corpora
            .map(([corpus, total]) => `${CORPUS_LABELS[corpus] ?? corpus} ${total}건`)
            .join(' · ')}
        </p>
      )}
      <p className={styles.categoryMeta}>
        {lookup.considered}건을 살펴 <strong>{lookup.accepted}건</strong>을 이 사업자의 것으로
        보았고,{' '}
        <strong>{lookup.rejected_as_another_business}건</strong>은 이름이 비슷한 다른 업체로 보여
        제외했습니다.
      </p>
      {unavailable.length === 0 ? null : (
        <p className={styles.categoryMeta}>
          조회하지 못함: {unavailable.map(([corpus, why]) => `${CORPUS_LABELS[corpus] ?? corpus}(${why})`).join(', ')}
        </p>
      )}
      <p className={styles.referenceReason}>
        <strong>네이버만 조회했습니다.</strong> 구글·다음은 보지 않았습니다. 그리고 이름이
        비슷한 업체를 가리는 일은 기계가 완벽히 하지 못합니다 — 위 숫자를 근거로 쓰시기
        전에 눈으로 한 번 확인해 주십시오.
      </p>
    </div>
  );
}
