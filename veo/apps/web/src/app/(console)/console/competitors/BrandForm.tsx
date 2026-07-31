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
    distinguishingTerms: '',
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
        body: JSON.stringify({ projectId, isOwnBrand, ...values }),
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
        distinguishingTerms: '',
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
          placeholder="ondam.example"
        />
        <span className={styles.hint}>
          도메인은 동명 업체와 공유되지 않습니다. 답변이 이 주소를 근거로 인용하면 그것만으로
          확정됩니다.
        </span>
      </label>

      <label className={styles.label}>
        구별 표현
        <input
          className={styles.input}
          value={values.distinguishingTerms}
          onChange={set('distinguishingTerms')}
          placeholder="대표 시술, 원장 성함, 남다른 진료시간"
        />
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
          홈페이지 주소
          <input
            className={styles.input}
            value={values.homepageUrl}
            onChange={set('homepageUrl')}
            placeholder="https://example.com"
          />
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
