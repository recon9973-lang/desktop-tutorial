'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import styles from './companies.module.css';

/**
 * 업체 등록 — 이름과 주소 두 칸.
 *
 * 엔진은 고객 → 프로젝트 → 사이트 세 단계를 요구하지만, 그건 저장 구조지 사람이 밟을
 * 절차가 아니다. 가운데 단계는 서버가 만든다.
 */

interface CompanyFormProps {
  /** 이미 있는 업체에 주소를 더하는 경우. 비어 있으면 새 업체를 만든다. */
  readonly customerId?: string;
  readonly companyName?: string;
}

export function CompanyForm({ customerId, companyName }: CompanyFormProps) {
  const router = useRouter();
  const addingToExisting = customerId !== undefined;

  const [name, setName] = useState(companyName ?? '');
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, url, customerId: customerId ?? '' }),
      });
      const body: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        const message =
          typeof body === 'object' && body !== null && 'message' in body
            ? String((body as { message: unknown }).message)
            : '등록하지 못했습니다.';
        setError(message);
        return;
      }

      setUrl('');
      if (!addingToExisting) setName('');
      // 서버 컴포넌트가 목록을 그리므로, 새로 그려 달라고 알린다.
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      {addingToExisting ? null : (
        <TextField
          label="업체명"
          name="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="온담의원"
          autoComplete="organization"
          required
        />
      )}
      <TextField
        label="측정 URL"
        name="url"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="ondam.co.kr"
        hint="주소창에서 복사해 붙여 넣으셔도 됩니다. 경로는 자동으로 떼어 냅니다."
        inputMode="url"
        required
      />
      <FormError message={error} />
      <Button type="submit" busy={busy}>
        {addingToExisting ? 'URL 추가' : '업체 등록'}
      </Button>
    </form>
  );
}
