'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import own from './projects.module.css';

/**
 * 프로젝트 이름 고치기 — **만들면 못 고치던 것.**
 *
 * 서버에는 `PATCH /api/projects/{id}` 가 처음부터 있었다. 화면이 없어서 오타 하나도
 * 못 고쳤다(`audit/2026-08-08-server-ui-gap.md` §B). 브랜드에서 같은 모양의 구멍이
 * 이미 두 번 나왔다(v0.3.69) — 만드는 길만 있고 고치는 길이 없는 화면.
 *
 * ## 이름만 고친다
 *
 * 서버는 slug·업체·지역·명세 판까지 받는다. 여기서는 **이름 하나만** 보낸다. 나머지는
 * **측정 조건**이라, 바꾸면 지난 진단과 비교가 끊긴다(ADR 0010). 이름은 사람이 부르는
 * 말일 뿐이라 언제 바꿔도 잰 값에 닿지 않는다.
 *
 * ## 접었다 편다
 *
 * 목록에 입력칸을 늘 펼쳐 두면 프로젝트 다섯 개짜리 화면이 입력칸 다섯 개가 된다.
 * 고치는 일은 드물다 — 평소에는 이름만 보이고, 누를 때 열린다.
 */
export function ProjectNameForm({
  projectId,
  projectName,
}: {
  readonly projectId: string;
  readonly projectName: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(projectName);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const trimmed = name.trim();
  // 안 바뀐 이름을 보내면 서버는 성공을 돌려주고 화면은 새로 고쳐진다 — 아무 일도
  // 안 일어난 것을 "고쳤습니다" 로 보이게 만들 이유가 없다.
  const unchanged = trimmed === projectName;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    if (trimmed === '') {
      setError('프로젝트 이름을 적어 주십시오.');
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/project', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId, name: trimmed }),
      });
      const payload: unknown = await response.json().catch(() => null);
      const body =
        typeof payload === 'object' && payload !== null
          ? (payload as Record<string, unknown>)
          : {};

      if (!response.ok || body['ok'] !== true) {
        // 서버가 준 문장이 있으면 그것을 쓴다. 없을 때만 우리 문장을 낸다 —
        // 지어낸 사유가 사람에게 나가면 그 사람은 엉뚱한 곳을 고친다.
        setError(
          typeof body['message'] === 'string'
            ? body['message']
            : '수정하지 못했습니다. 잠시 후 다시 시도해 주십시오.',
        );
        return;
      }

      setOpen(false);
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className={own.renameOpen}
        onClick={() => {
          setName(projectName);
          setError(null);
          setOpen(true);
        }}
      >
        이름 고치기
      </button>
    );
  }

  return (
    <form className={own.renameForm} onSubmit={submit}>
      <TextField
        label="프로젝트 이름"
        name="projectName"
        value={name}
        onChange={(event) => setName(event.target.value)}
        disabled={busy}
        autoFocus
      />
      {/*
        `null` 일 때도 **켜 둔다.** 라이브 영역을 조건부로 붙였다 떼면 화면 낭독기가
        나중에 들어온 오류를 읽지 못한다(`FormError` 머리말).
      */}
      <FormError message={error} />
      <div className={own.renameActions}>
        <Button type="submit" disabled={busy || unchanged}>
          {busy ? '저장 중…' : '저장'}
        </Button>
        <Button type="button" variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
          취소
        </Button>
      </div>
    </form>
  );
}
