'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import { readInvite } from './invite-wire';
import { ROLES, ROLE_LABELS, type Role } from './roles';

import styles from './team.module.css';

/**
 * 팀원 초대 — 이름·이메일·역할 세 칸.
 *
 * 메일을 보내지 않는다. 엔진이 1회용 링크를 돌려주고, 그 링크를 화면에 띄운다. 관리자가
 * 복사해 쓰던 방법으로 전달한다. 직원 몇 명을 들이는 데 메일 발송 인프라를 세울 이유가
 * 적고, 필요해지면 그때 이 자리에 붙이면 된다.
 *
 * **링크를 자동으로 지우지 않는다.** 한 번 닫으면 다시 볼 수 없고(토큰은 해시로만
 * 저장된다), 그때는 재발송뿐이다. 그래서 관리자가 직접 닫을 때까지 남겨 둔다.
 */
export function InviteForm() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<Role>('ANALYST');
  const [invite, setInvite] = useState<{ url: string; expiresAt: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/team', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ displayName, email, role }),
      });
      const body: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        const message =
          typeof body === 'object' && body !== null && 'message' in body
            ? String((body as { message: unknown }).message)
            : '초대하지 못했습니다.';
        setError(message);
        return;
      }

      const issued = readInvite(body);
      if (issued.inviteUrl === '') {
        // 빈 링크를 성공처럼 그리지 않는다. 예전에 그렇게 해서, 발급 문구와 복사 버튼은
        // 멀쩡한데 링크 칸만 빈 화면이 나왔다 — 관리자가 빈 값을 복사해 전달했다.
        setError('계정은 만들어졌지만 초대 링크를 받지 못했습니다. 목록에서 재발송을 눌러 주십시오.');
        router.refresh();
        return;
      }
      setInvite({ url: issued.inviteUrl, expiresAt: issued.expiresAt });
      setCopied(false);
      setDisplayName('');
      setEmail('');
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form className={styles.form} onSubmit={submit} noValidate>
        <TextField
          label="이름"
          name="displayName"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          required
        />
        <TextField
          label="이메일"
          name="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <div className={styles.field}>
          <label className={styles.label} htmlFor="invite-role">
            역할
          </label>
          <select
            id="invite-role"
            className={styles.select}
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
          >
            {ROLES.map((item) => (
              <option key={item} value={item}>
                {ROLE_LABELS[item].label}
              </option>
            ))}
          </select>
          {/* 역할 이름만 보고는 고를 수 없다. 고른 것이 무엇을 할 수 있는지 바로 아래 적는다. */}
          <p className={styles.hint}>{ROLE_LABELS[role].note}</p>
        </div>

        <FormError message={error} />

        <Button type="submit" disabled={busy}>
          {busy ? '초대하는 중…' : '초대하기'}
        </Button>
      </form>

      {invite === null ? null : (
        <div className={styles.invite} role="status">
          <p className={styles.inviteLead}>
            <strong>초대 링크가 발급됐습니다.</strong> 이 링크를 본인에게 전달하십시오.
            메일은 자동으로 나가지 않습니다.
          </p>
          <div className={styles.inviteRow}>
            <code className={styles.inviteUrl}>{invite.url}</code>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                void navigator.clipboard?.writeText(invite.url).then(() => setCopied(true));
              }}
            >
              {copied ? '복사됨' : '복사'}
            </Button>
          </div>
          <p className={styles.inviteNote}>
            한 번만 쓸 수 있고 {formatWhen(invite.expiresAt)}에 만료됩니다. 이 창을 닫으면
            링크를 다시 볼 수 없습니다 — 그때는 목록에서 <strong>재발송</strong>을 누르십시오.
          </p>
          <Button type="button" variant="secondary" onClick={() => setInvite(null)}>
            닫기
          </Button>
        </div>
      )}
    </>
  );
}

function formatWhen(value: string): string {
  if (value === '') return '정해진 기한';
  const moment = new Date(value);
  return Number.isNaN(moment.getTime())
    ? '정해진 기한'
    : moment.toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}
