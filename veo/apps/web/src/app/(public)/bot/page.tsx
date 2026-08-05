/**
 * VEOBot 안내 페이지.
 *
 * **왜 있어야 하는가.** 우리 크롤러의 User-Agent 가 이 주소를 가리킨다. 사이트 운영자가
 * 로그에서 낯선 봇을 보면 그 주소를 열어 본다. 2026-08-06 실측에서 이 주소는 **HTTP 404**
 * 였다 — 우리는 남의 서버를 두드리면서 안내를 약속만 하고 있었다. 안내가 없는 봇은
 * 악성 스캐너와 구별되지 않고, 막는 것이 운영자에게 합리적인 선택이 된다.
 *
 * 작업의뢰서 §5.2 는 이 페이지를 "봇 출시 전 **선행 게시 필수**" 로 정했다.
 *
 * **여기 적힌 숫자는 전부 코드의 실제 값이다.** 지어낸 값을 적으면 이 페이지가 곧 거짓이
 * 되고, 그때부터 운영자는 우리 말을 믿을 이유가 없다. 값을 바꾸면 이 페이지도 함께
 * 바꾼다 — `apps/api/tests/common/test_bot_identity.py` 가 UA 와 robots 이름이 갈리는
 * 것을 막고, 나머지 값은 이 파일의 출처 주석이 가리키는 자리에 있다.
 */

import type { Metadata } from 'next';

import styles from '@/styles/page.module.css';

export const metadata: Metadata = {
  title: 'VEOBot — 크롤러 안내',
  description:
    'VEO 의 진단 크롤러 VEOBot 의 신원, 요청 정책, robots.txt 로 차단하는 방법과 문의처를 안내합니다.',
};

/** `veo.common.security.fetcher.DEFAULT_USER_AGENT` 와 같은 문자열. */
const USER_AGENT = 'VEOBot/1.0 (+https://veo.seokorea.org/bot)';
/** `veo.common.security.fetcher.CRAWLER_FROM`. */
const FROM = 'bot@seokorea.org';
/** `veo.seo.parsing.robots.CRAWLER_AGENT_NAME` — robots.txt 가 매칭하는 이름. */
const ROBOTS_TOKEN = 'VEOBot';

/** 값과 그 출처를 한 줄로. 출처를 적는 이유는 이 표가 코드와 갈라지지 않게 하기 위해서다. */
const POLICY: readonly { readonly label: string; readonly value: string }[] = [
  { label: '동일 호스트 요청 간격', value: '최소 1초' },
  { label: '동일 호스트 동시 연결', value: '2개 이하' },
  { label: '동일 호스트 시간당 요청', value: '450회 이하' },
  { label: '연결 대기', value: '10초' },
  { label: '응답 대기(전체)', value: '30초' },
  { label: '받는 문서 크기', value: '최대 2MB' },
  { label: 'robots.txt', value: 'VEOBot 대상 Disallow 를 지킵니다' },
  { label: '쿠키·로그인', value: '보내지 않습니다. 공개된 페이지만 읽습니다' },
];

export default function BotPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>크롤러 안내</p>
        <h1 className={styles.heroTitle}>VEOBot 은 무엇을 하는 봇입니까</h1>
        <p className={styles.lede}>
          VEOBot 은 VENOM 이 운영하는 SEO·GEO 진단 크롤러입니다. 사이트가 검색엔진과 AI
          답변 엔진에 읽히는 상태인지 점검하기 위해, 진단을 의뢰받은 주소의 공개된
          페이지와 <code>robots.txt</code>·사이트맵을 읽습니다. 그 밖의 요청은 보내지
          않으며, 어떤 내용도 변경하지 않습니다.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="veo-bot-identity">
        <h2 id="veo-bot-identity" className={styles.sectionTitle}>
          로그에서 이렇게 보입니다
        </h2>
        <pre className={styles.code}>
          <code>
            {`User-Agent: ${USER_AGENT}\nFrom: ${FROM}`}
          </code>
        </pre>
        <p className={styles.linkCardText}>
          VEOBot 은 <strong>다른 크롤러의 이름을 쓰지 않습니다.</strong> 로그에 Googlebot
          이나 Yeti 로 찍힌 요청은 저희가 아닙니다.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="veo-bot-policy">
        <h2 id="veo-bot-policy" className={styles.sectionTitle}>
          요청 정책
        </h2>
        <ul className={styles.list}>
          {POLICY.map((row) => (
            <li key={row.label} className={styles.linkCardText}>
              <strong>{row.label}</strong> — {row.value}
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="veo-bot-block">
        <h2 id="veo-bot-block" className={styles.sectionTitle}>
          차단하려면
        </h2>
        <p className={styles.linkCardText}>
          <code>robots.txt</code> 에 아래를 넣으면 VEOBot 은 그 규칙을 지킵니다. 진단을
          의뢰하신 경우에도 마찬가지입니다 — 차단되어 있으면 진단은 &ldquo;수집하지
          못했다&rdquo;고 보고하며, 임의로 우회하지 않습니다.
        </p>
        <pre className={styles.code}>
          <code>{`User-agent: ${ROBOTS_TOKEN}\nDisallow: /`}</code>
        </pre>
        <p className={styles.linkCardText}>
          일부 경로만 막으려면 <code>Disallow</code> 에 그 경로를 적으시면 됩니다.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="veo-bot-contact">
        <h2 id="veo-bot-contact" className={styles.sectionTitle}>
          문의
        </h2>
        <p className={styles.linkCardText}>
          요청이 과도하거나 즉시 중단이 필요하시면{' '}
          <a href={`mailto:${FROM}`}>{FROM}</a> 으로 알려 주십시오. 사이트 주소와 로그에
          찍힌 시각을 함께 보내 주시면 확인이 빠릅니다.
        </p>
        <p className={styles.linkCardText}>운영 주체: VENOM (veo.seokorea.org)</p>
      </section>
    </div>
  );
}
