import type { GeoImprovement } from '@/lib/observations';

import styles from './geo.module.css';

/**
 * 오늘 고칠 것 — 돌아오는 점수 큰 순 (확정 시안 v2.2 §1).
 *
 * 판정 목록은 "무엇이 어떤 상태인가" 를 말하고, 이 목록은 **"무엇부터 손대는가"** 를
 * 말한다. 둘은 다른 질문이라 화면도 다른 자리에 둔다.
 *
 * `+N점` 은 채점기가 실제 산식으로 계산한 값이다. 화면이 어림하지 않는다 — 어림하면
 * 고친 뒤의 실제 점수와 어긋나고, 그러면 순서 자체를 믿을 수 없게 된다.
 *
 * 각 줄은 같은 화면의 그 항목 카드로 간다. 무엇부터 할지 정한 다음 바로 근거와 고침
 * 방법을 읽을 수 있어야, 목록이 목록으로 끝나지 않는다.
 */
export function ReadinessQueue({
  improvements,
}: {
  readonly improvements: readonly GeoImprovement[];
}) {
  // 상한에 걸린 항목은 지금 고쳐도 점수가 오르지 않는다. 순위 목록에 0점짜리를 섞으면
  // "이걸 하면 오른다" 는 이 목록의 약속이 깨진다 — 그 사실은 항목 카드가 말한다.
  const worth = improvements.filter((item) => !item.blocked_by_cap && item.gain_points > 0);
  if (worth.length === 0) return null;

  const shown = worth.slice(0, 5);

  return (
    <section className={styles.queueSection} aria-labelledby="geo-queue">
      <h3 id="geo-queue" className={styles.checksTitle}>
        오늘 고칠 것 — 돌아오는 점수 큰 순
      </h3>
      <ol className={styles.queueList}>
        {shown.map((item) => (
          <li key={item.check_id} className={styles.queueRow}>
            <a
              className={styles.queueTitle}
              href={item.category_id === '' ? '#geo-checks' : `#check-${item.category_id}`}
            >
              {item.title_ko}
            </a>
            <span className={styles.queueGain}>+{item.gain_points.toFixed(1)}점</span>
          </li>
        ))}
      </ol>
      {worth.length > shown.length ? (
        <p className={styles.checksNote}>
          이 아래로 {worth.length - shown.length}개가 더 있습니다 — 항목별 판정에서
          전부 볼 수 있습니다.
        </p>
      ) : null}
    </section>
  );
}
