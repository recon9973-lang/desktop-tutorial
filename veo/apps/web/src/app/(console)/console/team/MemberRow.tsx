'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@veo/ui';

import { readInvite } from './invite-wire';
import { ROLES, ROLE_LABELS, isRole, type Role } from './roles';

import styles from './team.module.css';

/**
 * 팀원 한 줄 — 역할 바꾸기, 계정 끄기, 초대 다시 보내기.
 *
 * **자기 자신은 손대지 못하게 한다.** 최고 관리자가 스스로의 역할을 낮추거나 계정을
 * 끄면 조직에 관리자가 없어지고, 그때는 데이터베이스를 직접 손대는 것 말고 방법이 없다.
 * 엔진도 막지만 화면에서 먼저 막아, 누를 수 없는 버튼을 누르고 오류를 받는 일이 없게 한다.
 *
 * 계정을 지우는 버튼은 두지 않는다. 비활성으로 충분하고, 지우면 그 사람이 실행한 진단의
 * "누가 측정했는가" 가 함께 사라진다.
 */

export interface MemberRowProps {
  readonly id: string;
  readonly displayName: string;
  readonly email: string;
  readonly roles: readonly string[];
  readonly isActive: boolean;
  readonly hasPassword: boolean;
  readonly lastLoginAt: string | null;
  /** 지금 보고 있는 사람 자신인가. */
  readonly isSelf: boolean;
  /** 팀원을 관리할 권한이 있는가. 없으면 보기만 한다. */
  readonly canManage: boolean;
}

export function MemberRow(member: MemberRowProps) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [invite, setInvite] = useState<string | null>(null);

  const current = member.roles.find(isRole) ?? 'ANALYST';
  const locked = !member.canManage || member.isSelf;

  async function send(what: string, body: unknown, method: 'POST' | 'PATCH'): Promise<void> {
    if (busy !== null) return;
    setBusy(what);
    setError(null);
    try {
      const response = await fetch('/api/team', {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: member.id, ...(body as object) }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        setError(
          typeof payload === 'object' && payload !== null && 'message' in payload
            ? String((payload as { message: unknown }).message)
            : '처리하지 못했습니다.',
        );
        return;
      }
      if (what === 'invite') {
        const issued = readInvite(payload).inviteUrl;
        // 빈 링크는 전달할 수 없다. 성공으로 보이는 빈 칸 대신 실패라고 말한다.
        if (issued === '') {
          setError('초대 링크를 받지 못했습니다. 다시 시도해 주십시오.');
          return;
        }
        setInvite(issued);
      }
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다.');
    } finally {
      setBusy(null);
    }
  }

  return (
    <li className={member.isActive ? styles.member : styles.memberOff}>
      <div className={styles.memberMain}>
        <div className={styles.memberWho}>
          <span className={styles.memberName}>
            {member.displayName}
            {member.isSelf ? <span className={styles.selfTag}>나</span> : null}
          </span>
          <span className={styles.memberEmail}>{member.email}</span>
        </div>

        <div className={styles.memberState}>
          {/* 상태를 색으로만 알리지 않는다. 기획서 §12.1 */}
          {!member.isActive ? (
            <span className={styles.stateOff}>비활성 — 로그인할 수 없습니다</span>
          ) : member.hasPassword ? (
            <span className={styles.stateOn}>
              {member.lastLoginAt === null
                ? '활성 · 아직 접속 기록 없음'
                : `활성 · 마지막 접속 ${formatWhen(member.lastLoginAt)}`}
            </span>
          ) : (
            <span className={styles.statePending}>초대 수락 대기 — 비밀번호를 아직 정하지 않았습니다</span>
          )}
        </div>
      </div>

      <div className={styles.memberActions}>
        <label className={styles.roleLabel} htmlFor={`role-${member.id}`}>
          역할
        </label>
        <select
          id={`role-${member.id}`}
          className={styles.select}
          value={current}
          disabled={locked || busy !== null}
          onChange={(event) => void send('role', { role: event.target.value as Role }, 'PATCH')}
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {ROLE_LABELS[role].label}
            </option>
          ))}
        </select>

        {locked ? null : (
          <>
            {member.hasPassword ? null : (
              <Button
                type="button"
                variant="secondary"
                disabled={busy !== null}
                onClick={() => void send('invite', {}, 'POST')}
              >
                {busy === 'invite' ? '발급 중…' : '초대 재발송'}
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              disabled={busy !== null}
              onClick={() => void send('status', { isActive: !member.isActive }, 'PATCH')}
            >
              {member.isActive ? '계정 끄기' : '계정 켜기'}
            </Button>
          </>
        )}
      </div>

      {member.isSelf && member.canManage ? (
        <p className={styles.rowNote}>
          자기 계정의 역할과 상태는 바꿀 수 없습니다. 관리자가 스스로를 내리면 조직에
          관리자가 남지 않습니다.
        </p>
      ) : null}

      {invite === null ? null : (
        <p className={styles.rowInvite} role="status">
          새 초대 링크입니다. 본인에게 전달하십시오 — <code>{invite}</code>
        </p>
      )}

      {error === null ? null : (
        <p className={styles.rowError} role="alert">
          {error}
        </p>
      )}
    </li>
  );
}

function formatWhen(value: string): string {
  const moment = new Date(value);
  return Number.isNaN(moment.getTime())
    ? value
    : moment.toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}
