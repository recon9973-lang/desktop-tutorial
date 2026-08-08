'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, FormError } from '@veo/ui';

import styles from './competitors.module.css';

/**
 * 브랜드를 등록하는 칸.
 *
 * 필드 순서가 **효과가 큰 순서**다. 대표번호가 위에 있는 이유는 그것이 흔한 상호를
 * 확정선 위로 올리는 유일한 항목이기 때문이다. 주소부터 물으면 사용자는 시간을 쓰고도
 * 측정이 안 되는 상태로 남는다.
 */
export function BrandForm({
  projectId,
  isOwnBrand,
}: {
  readonly projectId: string;
  readonly isOwnBrand: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({
    displayName: '',
    homepageUrl: '',
    phoneNumbers: '',
    addressTerms: '',
    ownDomains: '',
    doctorNames: '',
    treatments: '',
    otherTerms: '',
    aliases: '',
  });

  function set(key: keyof typeof values) {
    return (event: { target: { value: string } }) =>
      setValues((current) => ({ ...current, [key]: event.target.value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/brand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // 화면에서는 셋으로 나눠 받고, 보낼 때 하나로 합친다. 서버의 구별 표현은
        // 목록 하나이고(brand_identities.distinguishing_terms), 나누는 것은 사람이
        // 채우기 쉬우라는 것이지 뜻이 다른 값이라서가 아니다.
        body: JSON.stringify({
          projectId,
          isOwnBrand,
          ...values,
          distinguishingTerms: [values.doctorNames, values.treatments, values.otherTerms]
            .filter((one) => one.trim() !== '')
            .join(', '),
        }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setError(
          typeof record['message'] === 'string' ? record['message'] : '저장하지 못했습니다.',
        );
        return;
      }
      setValues({
        displayName: '',
        homepageUrl: '',
        phoneNumbers: '',
        addressTerms: '',
        ownDomains: '',
        doctorNames: '',
        treatments: '',
        otherTerms: '',
        aliases: '',
      });
      setOpen(false);
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button type="button" variant="secondary" onClick={() => setOpen(true)}>
        {isOwnBrand ? '자사 브랜드 등록' : '비교 대상 추가'}
      </Button>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <label className={styles.label}>
        상호 <span className={styles.required}>필수</span>
        <input
          className={styles.input}
          value={values.displayName}
          onChange={set('displayName')}
          placeholder="간판에 적힌 정식 상호"
          required
        />
      </label>

      {/* 가장 위에 둔다 — 흔한 상호를 확정선 위로 올리는 유일한 항목이다. */}
      <label className={styles.label}>
        대표번호
        <input
          className={styles.input}
          value={values.phoneNumbers}
          onChange={set('phoneNumbers')}
          placeholder="02-1234-5678"
        />
        <span className={styles.hint}>
          <strong>가장 효과가 큽니다.</strong> 흔한 상호는 이름만으로 확정되지 않고, 소재지만
          으로도 확정선에 이르지 못합니다.
        </span>
      </label>

      <label className={styles.label}>
        소재지
        <input
          className={styles.input}
          value={values.addressTerms}
          onChange={set('addressTerms')}
          placeholder="서울 강남구 테헤란로, 강남역"
        />
        <span className={styles.hint}>
          AI 답변이 실제로 말할 만한 표현으로 — 행정동·역명·랜드마크. 쉼표로 여러 개.
        </span>
      </label>

      <label className={styles.label}>
        {isOwnBrand ? '자사 도메인' : '홈페이지 도메인'}
        <input
          className={styles.input}
          value={values.ownDomains}
          onChange={set('ownDomains')}
          placeholder="ondam.kr"
        />
        <span className={styles.hint}>
          주소를 통째로 붙여 넣어도 됩니다 — <code>https://ondam.kr/about</code> 은{' '}
          <code>ondam.kr</code> 로 저장됩니다.
        </span>
        <span className={styles.hint}>
          <strong>네이버 블로그·인스타그램 주소는 넣지 마십시오.</strong>{' '}
          <code>blog.naver.com</code> 은 모든 블로그가 함께 쓰는 주소라, 넣으면 남의 글이
          인용돼도 우리 업체로 잡힙니다. 자기 도메인이 없으면 비워 두고 상호·대표번호·
          소재지로 가리십시오 — 저장할 때 서버가 한 번 더 막습니다.
        </span>
      </label>

      {/*
        한 칸에 원장명·시술·진료시간을 다 넣게 두면 채우기 힘들고, 무엇을 넣어야
        하는지도 안 보인다(사장님 지적 2026-08-08). 셋으로 나눠 받고 보낼 때 합친다.

        **진료시간은 여기 두지 않는다.** 이 값들은 AI 답변 본문과 글자로 대조해 "이
        언급이 우리 업체인가" 를 가리는 데 쓴다(`detection/disambiguation.py`).
        답변에 "월~금 09:00-18:00" 이 나올 일은 거의 없어서, 넣어도 대조에 안 걸리고
        칸만 채운다.
      */}
      <label className={styles.label}>
        원장·의료진 이름
        <input
          className={styles.input}
          value={values.doctorNames}
          onChange={set('doctorNames')}
          placeholder="정세현, 홍길동"
        />
        <span className={styles.hint}>
          <strong>상호 다음으로 효과가 큽니다.</strong> AI 답변이 &ldquo;○○ 원장&rdquo;
          이라고 말하면 그것으로 동명 병원과 갈립니다. 여러 명이면 쉼표로.
        </span>
      </label>

      <label className={styles.label}>
        진료과목·대표 시술
        <input
          className={styles.input}
          value={values.treatments}
          onChange={set('treatments')}
          placeholder="추나요법, 다이어트, 교통사고"
        />
        <span className={styles.hint}>
          AI 답변에 실제로 나올 만한 말로. &ldquo;한방내과&rdquo; 같은 분류명보다
          &ldquo;추나요법&rdquo; 처럼 환자가 쓰는 말이 잘 걸립니다.
        </span>
      </label>

      <label className={styles.label}>
        그 밖의 구별 표현
        <input
          className={styles.input}
          value={values.otherTerms}
          onChange={set('otherTerms')}
          placeholder="건물명, 층수, 함께 쓰는 별칭"
        />
        <span className={styles.hint}>
          <strong>진료시간은 넣지 마십시오.</strong> 이 값들은 AI 답변 본문과 글자로
          대조하는 데 쓰는데, 답변에 &ldquo;월~금 09:00-18:00&rdquo; 이 나올 일은 거의
          없어 대조에 걸리지 않습니다.
        </span>
      </label>

      <label className={styles.label}>
        다른 이름
        <input
          className={styles.input}
          value={values.aliases}
          onChange={set('aliases')}
          placeholder="줄임말, 옛 상호, 영문 표기"
        />
      </label>

      {!isOwnBrand ? (
        <label className={styles.label}>
          홈페이지 주소 (전체)
          <input
            className={styles.input}
            value={values.homepageUrl}
            onChange={set('homepageUrl')}
            placeholder="https://competitor.kr"
          />
          <span className={styles.hint}>
            비교 대상은 이 주소로 같은 곳을 두 번 등록하지 않게 막습니다. 위 도메인 칸과
            달리 <strong>주소 전체</strong>를 넣으며, 블로그 주소여도 됩니다 — 여기 값은
            인용 대조에 쓰지 않습니다.
          </span>
        </label>
      ) : null}

      <div className={styles.actions}>
        <Button type="submit" busy={busy}>
          저장
        </Button>
        <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
          취소
        </Button>
      </div>
      <FormError message={error} />
    </form>
  );
}
