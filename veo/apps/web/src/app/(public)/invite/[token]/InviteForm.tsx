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
  /** 비밀번호를 정한 뒤 알려 줄 로그인 아이디. 이메일을 못 받았으면 `null`. */
  const [account, setAccount] = useState<string | null>(null);

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
        // 곧바로 로그인 화면으로 넘기지 않는다. 초대받은 사람은 방금 비밀번호를
        // 정했을 뿐 **자기 아이디가 무엇인지 모른다** — 관리자가 링크만 전달했다면
        // 더 그렇다. 넘겨 버리면 빈 이메일 칸 앞에서 멈춘다.
        const body: unknown = await response.json().catch(() => null);
        const found =
          typeof body === 'object' && body !== null && 'email' in body
            ? (body as { email: unknown }).email
            : null;
        setAccount(typeof found === 'string' ? found : null);
        setDone(true);
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
    setFormError(inviteMessageFor(reason));
    setProblems([]);
    summaryWantsFocus.current = true;
  }

  if (done) {
    return (
      <div role="status">
        <h2>비밀번호를 설정했습니다</h2>
        {account === null ? (
          <p>
            초대할 때 받은 이메일 주소로 로그인하십시오. 주소를 모르면 초대한 담당자에게
            확인해 주십시오.
          </p>
        ) : (
          <p>
            로그인 아이디는 <strong>{account}</strong> 입니다. 방금 정한 비밀번호와 함께
            사용하십시오.
          </p>
        )}
        <Button type="button" onClick={() => router.push('/login')}>
          로그인하러 가기
        </Button>
      </div>
    );
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
