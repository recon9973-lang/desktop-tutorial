import type { ReactNode } from 'react';
import { cx } from '../../utils/cx';
import styles from './ScoreCard.module.css';

export interface ScoreCardProps {
  title: string;
  /** `null` means the score could not be computed. It is never shown as 0. */
  score: number | null;
  /** Scoring spec identity, e.g. "veo.seo.readiness 1.0.0". Always displayed. */
  specVersion: string;
  /** Share of applicable checks that produced a verdict, 0–1. Always displayed. */
  coverage: number;
  /** Weighted evidence confidence, 0–1. Always displayed. */
  confidence: number;
  /** Optional band label from the scoring spec, e.g. "양호". */
  bandLabel?: string;
  /** Optional short explanation of what the score means. */
  note?: string;
  children?: ReactNode;
  className?: string;
}

function formatRatio(value: number): string {
  if (!Number.isFinite(value)) {
    return '측정 불가';
  }
  const clamped = Math.min(Math.max(value, 0), 1);
  return `${(clamped * 100).toFixed(1)}%`;
}

export function ScoreCard({
  title,
  score,
  specVersion,
  coverage,
  confidence,
  bandLabel,
  note,
  children,
  className,
}: ScoreCardProps) {
  const hasScore = score !== null && Number.isFinite(score);

  return (
    <section
      className={cx(styles.card, className)}
      aria-label={title}
      data-veo-score-state={hasScore ? 'scored' : 'unmeasured'}
    >
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {bandLabel !== undefined && hasScore ? (
          <span className={styles.band}>{bandLabel}</span>
        ) : null}
      </div>

      {/*
        The number on screen is split across two elements for layout, which a
        screen reader would read as "72.4 ／ 100점". The visible glyphs are
        therefore hidden from assistive technology and one written sentence is
        given instead, so the scale is never lost and the fullwidth solidus is
        never voiced as punctuation noise.
      */}
      <p className={styles.scoreRow}>
        {hasScore ? (
          <>
            <span className={styles.score} aria-hidden="true">
              {score.toFixed(1)}
            </span>
            <span className={styles.scale} aria-hidden="true">
              ／ 100점
            </span>
            <span className={styles.srOnly}>{`100점 만점에 ${score.toFixed(1)}점`}</span>
          </>
        ) : (
          <span className={styles.unmeasured}>측정 불가</span>
        )}
      </p>

      {note !== undefined ? <p className={styles.note}>{note}</p> : null}

      <dl className={styles.meta}>
        <div className={styles.metaItem}>
          <dt className={styles.metaTerm}>기준 버전</dt>
          <dd className={styles.metaValue}>{specVersion}</dd>
        </div>
        <div className={styles.metaItem}>
          <dt className={styles.metaTerm}>측정 범위</dt>
          <dd className={styles.metaValue}>{formatRatio(coverage)}</dd>
        </div>
        <div className={styles.metaItem}>
          <dt className={styles.metaTerm}>신뢰도</dt>
          <dd className={styles.metaValue}>{formatRatio(confidence)}</dd>
        </div>
      </dl>

      {children}

      <p className={styles.disclaimer}>
        기술·구조 준비도 점수입니다. 검색 순위를 예측하거나 보장하지 않습니다.
      </p>
    </section>
  );
}
