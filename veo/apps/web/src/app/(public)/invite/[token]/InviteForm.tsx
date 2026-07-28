'use client';

import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, FormError, TextField } from '@veo/ui';

import {
  INVITE_MESSAGES,
  MIN_INVITE_PASSWORD_LENGTH,
  inviteMessageFor,
} from '@/lib/invite-messages';

export interface InviteFormProps {
  /** Taken from the URL. Never rendered — it is a credential until it is spent. */
  token: string;
}

const PASSWORD_ID = 'veo-invite-password';
const CONFIRM_ID = 'veo-invite-confirm';
const ERROR_ID = 'veo-invite-error';

interface FieldErrors {
  password?: string;
  confirm?: string;
}

export function InviteForm({ token }: InviteFormProps) {
  const router = useRouter();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [problems, setProblems] = useState<readonly string[]>([]);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  const summaryRef = useRef<HTMLDivElement>(null);
  const summaryWantsFocus = useRef(false);

  // Same reasoning as the sign-in form: focus moves after the commit, because
  // focusing a region React has not written the message into yet announces nothing.
  useEffect(() => {
    if (summaryWantsFocus.current && formError !== null) {
      summaryWantsFocus.current = false;
      summaryRef.current?.focus();
    }
  }, [formError]);

  function validate(): FieldErrors {
    const found: FieldErrors = {};
    if (password.length < MIN_INVITE_PASSWORD_LENGTH) {
      found.password = INVITE_MESSAGES.passwordTooShort;
    }
    if (confirm !== password) {
      found.confirm = INVITE_MESSAGES.confirmMismatch;
    }
    return found;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    const found = validate();
    setFieldErrors(found);
    if (Object.keys(found).length > 0) {
      setFormError(INVITE_MESSAGES.summary);
      setProblems(Object.values(found));
      summaryWantsFocus.current = true;
      return;
    }

    setPending(true);
    setFormError(null);
    setProblems([]);

    let reason = 'SERVER_ERROR';
    try {
      const response = await fetch('/api/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });
      if (response.ok) {
        setDone(true);
        setPending(false);
        // Sign-in is a separate act. This screen proves the password was set; it
        // does not hand out a session, so there is only one way to become
        // authenticated in the product.
        router.push('/login');
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
    setFormError(inviteMessageFor(reason));
    setProblems([]);
    summaryWantsFocus.current = true;
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <FormError
        id={ERROR_ID}
        ref={summaryRef}
        message={formError}
        problems={problems}
      />

      <TextField
        id={PASSWORD_ID}
        name="password"
        type="password"
        label="새 비밀번호"
        autoComplete="new-password"
        hint={`${MIN_INVITE_PASSWORD_LENGTH}자 이상으로 정해 주세요.`}
        value={password}
        error={fieldErrors.password ?? null}
        onChange={(event) => setPassword(event.target.value)}
        disabled={done}
      />

      <TextField
        id={CONFIRM_ID}
        name="confirm"
        type="password"
        label="새 비밀번호 확인"
        autoComplete="new-password"
        value={confirm}
        error={fieldErrors.confirm ?? null}
        onChange={(event) => setConfirm(event.target.value)}
        disabled={done}
      />

      <Button type="submit" busy={pending} disabled={done}>
        비밀번호 설정하고 시작하기
      </Button>
    </form>
  );
}
