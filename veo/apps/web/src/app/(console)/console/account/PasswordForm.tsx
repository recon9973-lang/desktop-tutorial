'use client';

import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import { MIN_INVITE_PASSWORD_LENGTH } from '@/lib/invite-messages';

const MESSAGES: Record<string, string> = {
  WRONG_CURRENT_PASSWORD: '현재 비밀번호가 올바르지 않습니다.',
  SAME_PASSWORD: '새 비밀번호가 기존 비밀번호와 같습니다.',
  WEAK_PASSWORD: `비밀번호는 ${MIN_INVITE_PASSWORD_LENGTH}자 이상으로 정해 주세요.`,
  SIGNED_OUT: '세션이 만료되었습니다. 다시 로그인해 주세요.',
  SERVER_ERROR: '지금은 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.',
  UNAVAILABLE: '서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요.',
  NOT_CONFIGURED: '서버가 아직 연결되지 않았습니다. 운영자에게 문의해 주세요.',
};

const SUMMARY = '입력한 내용을 확인해 주세요.';

export function PasswordForm() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [problems, setProblems] = useState<readonly string[]>([]);
  const [pending, setPending] = useState(false);
  const [changed, setChanged] = useState(false);

  const summaryRef = useRef<HTMLDivElement>(null);
  const wantsFocus = useRef(false);

  useEffect(() => {
    if (wantsFocus.current && formError !== null) {
      wantsFocus.current = false;
      summaryRef.current?.focus();
    }
  }, [formError]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    const found: Record<string, string> = {};
    if (current === '') found.current = '현재 비밀번호를 입력해 주세요.';
    if (next.length < MIN_INVITE_PASSWORD_LENGTH) {
      found.next = `새 비밀번호는 ${MIN_INVITE_PASSWORD_LENGTH}자 이상이어야 합니다.`;
    }
    if (confirm !== next) found.confirm = '두 번 입력한 비밀번호가 서로 다릅니다.';

    setFieldErrors(found);
    if (Object.keys(found).length > 0) {
      setFormError(SUMMARY);
      setProblems(Object.values(found));
      wantsFocus.current = true;
      return;
    }

    setPending(true);
    setFormError(null);
    setProblems([]);
    setChanged(false);

    let reason = 'SERVER_ERROR';
    try {
      const response = await fetch('/api/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentPassword: current, newPassword: next }),
      });
      if (response.ok) {
        setCurrent('');
        setNext('');
        setConfirm('');
        setChanged(true);
        setPending(false);
        return;
      }
      const body: unknown = await response.json().catch(() => null);
      if (typeof body === 'object' && body !== null) {
        const parsed = body as { reason?: unknown };
        if (typeof parsed.reason === 'string') reason = parsed.reason;
      }
    } catch {
      reason = 'UNAVAILABLE';
    }

    setPending(false);
    setFormError(MESSAGES[reason] ?? MESSAGES.SERVER_ERROR!);
    setProblems([]);
    wantsFocus.current = true;
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <FormError id="veo-password-error" ref={summaryRef} message={formError} problems={problems} />

      {changed ? (
        <p role="status">
          비밀번호를 변경했습니다. 다른 기기에서는 모두 로그아웃되었고, 지금 이 화면은 그대로
          사용하실 수 있습니다.
        </p>
      ) : null}

      <TextField
        id="veo-password-current"
        name="current"
        type="password"
        label="현재 비밀번호"
        autoComplete="current-password"
        value={current}
        error={fieldErrors.current ?? null}
        onChange={(event) => setCurrent(event.target.value)}
      />
      <TextField
        id="veo-password-next"
        name="next"
        type="password"
        label="새 비밀번호"
        autoComplete="new-password"
        hint={`${MIN_INVITE_PASSWORD_LENGTH}자 이상으로 정해 주세요.`}
        value={next}
        error={fieldErrors.next ?? null}
        onChange={(event) => setNext(event.target.value)}
      />
      <TextField
        id="veo-password-confirm"
        name="confirm"
        type="password"
        label="새 비밀번호 확인"
        autoComplete="new-password"
        value={confirm}
        error={fieldErrors.confirm ?? null}
        onChange={(event) => setConfirm(event.target.value)}
      />

      <Button type="submit" busy={pending}>비밀번호 변경</Button>
    </form>
  );
}
