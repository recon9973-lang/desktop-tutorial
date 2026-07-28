'use client';

import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, FormError, TextField } from '@veo/ui';

import {
  FIELD_MESSAGES,
  LOGIN_MESSAGES,
  loginMessageFor,
  looksLikeEmail,
} from '@/lib/login-messages';
import styles from './login.module.css';

export interface LoginFormProps {
  /** Validated destination from `?next=`, or `null`. */
  nextPath: string | null;
}

interface FieldErrors {
  email?: string;
  password?: string;
}

interface SessionResponseBody {
  ok?: unknown;
  redirectTo?: unknown;
  reason?: unknown;
}

const EMAIL_ID = 'veo-login-email';
const PASSWORD_ID = 'veo-login-password';
const ERROR_ID = 'veo-login-error';

export function LoginForm({ nextPath }: LoginFormProps) {
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [summaryProblems, setSummaryProblems] = useState<readonly string[]>([]);
  const [pending, setPending] = useState(false);

  const summaryRef = useRef<HTMLDivElement>(null);
  const summaryWantsFocus = useRef(false);

  /**
   * Asks for the reader to be sent to the error summary after the next render.
   *
   * Focusing the first bad field instead — which this form used to do — tells
   * someone using a screen reader about exactly one problem, and hides the rest
   * until they fix that one and submit again. And on a rejected sign-in there is
   * no bad field to focus at all, so focus simply stayed on the submit button
   * with the message unread above it.
   *
   * The move waits for the commit rather than happening inline: React has not
   * written the message into the region yet when the handler runs, and focusing
   * an empty region is how a summary ends up being announced as nothing.
   */
  function requestSummaryFocus() {
    summaryWantsFocus.current = true;
  }

  useEffect(() => {
    if (summaryWantsFocus.current && formError !== null) {
      summaryWantsFocus.current = false;
      summaryRef.current?.focus();
    }
  }, [formError, summaryProblems]);

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    const trimmedEmail = email.trim();

    if (trimmedEmail === '') {
      errors.email = FIELD_MESSAGES.emailRequired;
    } else if (!looksLikeEmail(trimmedEmail)) {
      errors.email = FIELD_MESSAGES.emailFormat;
    }

    if (password === '') {
      errors.password = FIELD_MESSAGES.passwordRequired;
    }

    return errors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }

    setFormError(null);
    const errors = validate();
    setFieldErrors(errors);

    // Order matches the fields on screen, so the summary reads top to bottom.
    const problems = [errors.email, errors.password].filter(
      (problem): problem is string => problem !== undefined,
    );

    if (problems.length > 0) {
      setFormError(FIELD_MESSAGES.summary);
      setSummaryProblems(problems);
      requestSummaryFocus();
      return;
    }

    setSummaryProblems([]);
    setPending(true);
    try {
      const response = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password,
          next: nextPath,
        }),
      });

      const body: SessionResponseBody = await response
        .json()
        .then((value: unknown) => (typeof value === 'object' && value !== null ? value : {}))
        .catch(() => ({}));

      if (response.ok && body.ok === true && typeof body.redirectTo === 'string') {
        // The token was set as an httpOnly cookie by the route handler. Nothing
        // about the session is held here; the server re-reads it on the next render.
        router.replace(body.redirectTo);
        router.refresh();
        return;
      }

      setFormError(loginMessageFor(body.reason));
      requestSummaryFocus();
    } catch {
      // The request never completed. Say so; do not imply anything about the account.
      setFormError(LOGIN_MESSAGES.UNAVAILABLE);
      requestSummaryFocus();
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <FormError
        id={ERROR_ID}
        ref={summaryRef}
        message={formError}
        problems={summaryProblems}
      />

      <TextField
        id={EMAIL_ID}
        label="이메일"
        name="email"
        type="email"
        autoComplete="username"
        inputMode="email"
        required
        value={email}
        disabled={pending}
        error={fieldErrors.email ?? null}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />

      <TextField
        id={PASSWORD_ID}
        label="비밀번호"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        disabled={pending}
        error={fieldErrors.password ?? null}
        onChange={(event) => {
          setPassword(event.target.value);
        }}
      />

      <Button type="submit" busy={pending} block>
        로그인
      </Button>
    </form>
  );
}
