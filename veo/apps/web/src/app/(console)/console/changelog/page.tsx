import type { Metadata } from 'next';
import { Card } from '@veo/ui';

import { APP_VERSION, CHANGELOG } from '@/lib/changelog';
import styles from '@/styles/page.module.css';

import own from './changelog.module.css';

export const metadata: Metadata = {
  title: '변경 이력',
  robots: { index: false, follow: false },
};

/**
 * 버전별 변경 이력 — 하단 버전 표시를 누르면 오는 화면.
 *
 * 어느 판을 쓰고 있는지, 판마다 무엇이 바뀌었는지를 사람이 읽는 자리다.
 * 권한 게이트가 없다 — 릴리스 노트는 콘솔에 들어온 모두가 볼 수 있어야 한다.
 */
export default function ConsoleChangelogPage() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>변경 이력</h1>
        <p className={styles.lede}>
          현재 버전은 <strong>v{APP_VERSION}</strong> 입니다. 업데이트마다 무엇이 바뀌었는지
          기록합니다. 진단 결과에 붙는 &ldquo;명세&rdquo; 버전은 점수 계산 규칙의 버전으로,
          앱 버전과는 다른 축입니다.
        </p>
      </div>

      <div className={own.entries}>
        {CHANGELOG.map((entry) => (
          <Card key={entry.version}>
            <div className={own.entryHead}>
              <span
                className={entry.version === APP_VERSION ? own.badgeCurrent : own.badge}
              >
                v{entry.version}
              </span>
              <h2 className={own.entryTitle}>{entry.title}</h2>
              <span className={own.entryDate}>{entry.date}</span>
            </div>
            <ul className={own.items}>
              {entry.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  );
}
