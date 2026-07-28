import styles from './SiteFooter.module.css';

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <p className={styles.credits}>
          VEO — 개발 VENOM · 연구 및 방법론 VEO-LAB
        </p>
        <p className={styles.note}>
          VEO가 계산하는 점수는 검색엔진과 AI 답변 엔진이 사이트를 읽을 수 있는 기술·구조
          준비도입니다. 검색 순위를 예측하거나 보장하지 않으며, 수집한 값은 모두 출처와 수집
          시각을 함께 표시합니다.
        </p>
      </div>
    </footer>
  );
}
