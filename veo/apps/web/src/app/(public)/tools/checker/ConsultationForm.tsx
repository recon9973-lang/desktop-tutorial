'use client';

import { useState, type FormEvent } from 'react';

import styles from './public-checker.module.css';

/** 서버가 실제로 적어 둔 것. 화면은 이 목록을 그대로 보인다. */
interface Receipt {
  readonly storedFieldsKo: readonly string[];
  readonly retentionNoteKo: string;
  readonly consentNoteKo: string;
}

/**
 * 결과를 본 뒤 "상담 받겠다" 를 누르는 자리.
 *
 * 접수 창구는 처음부터 서버에 서 있었는데(`POST /public/v1/leads`) 누를 자리가 없었다.
 * 무료 진단은 돌아가고 결과 공유도 되는데 **영업으로 이어지는 문이 없었다.**
 *
 * 받는 것은 회신에 필요한 최소한이다 — 이름과 연락처 하나, 선택으로 홈페이지 주소.
 * 생년월일도, 주민번호도, **광고 수신 동의 체크박스도 없다.** 서버 스키마가 그 외의
 * 항목을 거부하므로, 여기에 칸을 늘려도 저장되지 않는다.
 *
 * **무엇을 저장했는지는 우리가 적지 않는다.** 접수가 끝나면 서버가 저장한 항목을
 * 한국어로 돌려주고 그것을 그대로 보인다. 우리가 따로 적으면 실제 저장한 것과
 * 갈라지고, 갈라진 쪽은 개인정보 안내문이라 더 나쁘다.
 */
export function ConsultationForm({ siteUrl }: { readonly siteUrl: string | null }) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasChannel = phone.trim() !== '' || email.trim() !== '';

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    if (name.trim() === '') {
      setError('연락 시 부를 이름을 적어 주세요.');
      return;
    }
    if (!hasChannel) {
      setError('전화번호 또는 이메일 중 하나는 적어 주세요.');
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/public-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, phone, email, siteUrl }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

      if (!response.ok) {
        setError(
          typeof record['message'] === 'string' ? record['message'] : '접수하지 못했습니다.',
        );
        return;
      }
      setReceipt((record['receipt'] as Receipt | undefined) ?? null);
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setBusy(false);
    }
  }

  if (receipt !== null) {
    return (
      <section className={styles.consultDone} aria-live="polite">
        <h3 className={styles.consultTitle}>상담 요청이 접수되었습니다</h3>
        {receipt.storedFieldsKo.length > 0 ? (
          <>
            <p className={styles.consultSub}>저장한 항목은 이것뿐입니다.</p>
            <ul className={styles.consultStored}>
              {receipt.storedFieldsKo.map((field) => (
                <li key={field}>{field}</li>
              ))}
            </ul>
          </>
        ) : null}
        {receipt.retentionNoteKo !== '' ? (
          <p className={styles.consultNote}>{receipt.retentionNoteKo}</p>
        ) : null}
        {receipt.consentNoteKo !== '' ? (
          <p className={styles.consultNote}>{receipt.consentNoteKo}</p>
        ) : null}
      </section>
    );
  }

  return (
    <section className={styles.consult}>
      <h3 className={styles.consultTitle}>이 결과로 상담 받기</h3>
      <p className={styles.consultSub}>
        회신에 필요한 것만 받습니다 — 이름과 연락처 하나. <strong>광고 수신 동의는 받지
        않습니다.</strong>
      </p>

      <form className={styles.consultForm} onSubmit={submit} noValidate>
        <label className={styles.consultField}>
          <span>이름</span>
          <input
            type="text"
            value={name}
            maxLength={40}
            autoComplete="name"
            onChange={(event) => setName(event.target.value)}
          />
        </label>

        <label className={styles.consultField}>
          <span>전화번호</span>
          <input
            type="tel"
            value={phone}
            maxLength={20}
            autoComplete="tel"
            onChange={(event) => setPhone(event.target.value)}
          />
        </label>

        <label className={styles.consultField}>
          <span>이메일</span>
          <input
            type="email"
            value={email}
            maxLength={120}
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <p className={styles.consultHint}>
          전화번호와 이메일 중 <strong>하나만</strong> 적으셔도 됩니다.
          {siteUrl !== null ? ` 방금 진단한 ${siteUrl} 도 함께 전달됩니다.` : ''}
        </p>

        <button type="submit" className={styles.consultButton} disabled={busy}>
          {busy ? '접수하는 중…' : '상담 요청'}
        </button>

        {error !== null ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </section>
  );
}
