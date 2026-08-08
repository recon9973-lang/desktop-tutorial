'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, FormError } from '@veo/ui';

import type { Brand } from '@/lib/brands';

import styles from './competitors.module.css';
import {
  SiteIdentityPicker,
  type PickedValues,
  type SiteIdentityDraft,
} from './SiteIdentityPicker';

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
  brand,
  siteOrigin = '',
}: {
  readonly projectId: string;
  readonly isOwnBrand: boolean;
  /**
   * 이 프로젝트에 **이미 등록된** 홈페이지 주소. 있으면 "홈페이지에서 불러오기" 칸에
   * 미리 넣는다.
   *
   * 거래처 등록에서 받은 주소를 여기서 또 손으로 치게 두면, 손으로 치는 만큼 안 친다.
   * 비교 대상에는 넘기지 않는다 — 우리 사이트를 경쟁사 칸에 미리 넣으면 그것을 그대로
   * 눌러 **경쟁사에 우리 도메인이 저장된다.**
   */
  readonly siteOrigin?: string;
  /**
   * 주면 **수정**, 안 주면 등록.
   *
   * 서버에는 처음부터 고치는 길이 있었고(`PATCH /projects/{id}/brands/{brandId}`),
   * 프록시도 `brandId` 를 받고 있었다. **화면에 단추가 없었을 뿐이다** — 한 번 저장하면
   * 오타 하나도 못 고쳤다. 부를 수 없는 기능은 없는 기능이다(0-E).
   */
  readonly brand?: Brand;
}) {
  const router = useRouter();
  const editing = brand !== undefined;
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** 서버가 되돌린 칸. 그 칸만 빨갛게 칠한다. */
  const [invalid, setInvalid] = useState<'ownDomains' | null>(null);
  /** 왜 틀렸는지. 모달로 한 번만 보여주고 화면에는 남기지 않는다. */
  const [modal, setModal] = useState<string | null>(null);
  const [values, setValues] = useState({
    displayName: brand?.display_name ?? '',
    homepageUrl: '',
    phoneNumbers: (brand?.phone_numbers ?? []).join(', '),
    addressTerms: (brand?.address_terms ?? []).join(', '),
    ownDomains: (brand?.own_domains ?? []).join(', '),
    // 저장은 목록 하나로 하므로, 되읽을 때 셋으로 다시 가를 수 없다. 통째로 첫 칸에
    // 넣으면 원장명이 아닌 것이 원장명 칸에 앉는다 — 마지막 칸에 담고 옮기게 한다.
    doctorNames: '',
    treatments: '',
    otherTerms: (brand?.distinguishing_terms ?? []).join(', '),
    aliases: (brand?.aliases ?? []).join(', '),
  });

  /** 홈페이지에서 읽어 온 후보. 고르기 전까지는 폼에 들어가지 않는다. */
  const [draft, setDraft] = useState<SiteIdentityDraft | null>(null);
  const [reading, setReading] = useState(false);
  const [readError, setReadError] = useState<string | null>(null);

  function set(key: keyof typeof values) {
    return (event: { target: { value: string } }) =>
      setValues((current) => ({ ...current, [key]: event.target.value }));
  }

  async function loadFromSite(url: string): Promise<void> {
    if (reading) return;
    if (url === '') {
      setReadError('홈페이지 주소를 입력해 주십시오.');
      return;
    }
    setReading(true);
    setReadError(null);
    setDraft(null);
    try {
      const response = await fetch('/api/brand-identity-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId, url }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setReadError(
          typeof record['message'] === 'string' ? record['message'] : '홈페이지를 읽지 못했습니다.',
        );
        return;
      }
      setDraft(record['draft'] as SiteIdentityDraft);
    } catch {
      setReadError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setReading(false);
    }
  }

  /**
   * 고른 값을 칸에 넣는다. **이미 적혀 있는 것은 덮지 않는다** — 사람이 손으로 쓴
   * 값이 자동으로 읽어 온 값에 밀리면, 무엇이 저장될지 사람이 알 수 없게 된다.
   */
  function applyPicked(picked: PickedValues): void {
    setValues((current) => {
      const next = { ...current };
      for (const [key, value] of Object.entries(picked) as [keyof typeof values, string][]) {
        if (value !== undefined && value !== '' && current[key].trim() === '') {
          next[key] = value;
        }
      }
      return next;
    });
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
        // 화면에서는 셋으로 나눠 받고, 보낼 때 하나로 합친다. 서버의 구별 표현은
        // 목록 하나이고(brand_identities.distinguishing_terms), 나누는 것은 사람이
        // 채우기 쉬우라는 것이지 뜻이 다른 값이라서가 아니다.
        body: JSON.stringify({
          projectId,
          isOwnBrand,
          ...(editing ? { brandId: brand.id } : {}),
          ...values,
          distinguishingTerms: [values.doctorNames, values.treatments, values.otherTerms]
            .filter((one) => one.trim() !== '')
            .join(', '),
        }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        const message =
          typeof record['message'] === 'string' ? record['message'] : '저장하지 못했습니다.';
        // 입력 오류는 **어느 칸인지 칠하고 모달로 설명한다.** 칸 아래에 미리 길게
        // 적어 두면 아무도 안 읽고, 정작 틀렸을 때는 안 보인다(사장님 지적 2026-08-08).
        if (record['reason'] === 'INVALID') {
          setInvalid('ownDomains');
          setModal(message);
          return;
        }
        setError(message);
        return;
      }
      setInvalid(null);
      if (!editing) {
        setValues({
          displayName: '',
          homepageUrl: '',
          phoneNumbers: '',
          addressTerms: '',
          ownDomains: '',
          doctorNames: '',
          treatments: '',
          otherTerms: '',
          aliases: '',
        });
      }
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
        {editing ? '수정' : isOwnBrand ? '자사 브랜드 등록' : '비교 대상 추가'}
      </Button>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      {/* 칸 위에 둔다. 손으로 다 채운 뒤에 보이면 아무도 안 쓴다. */}
      <SiteIdentityPicker
        draft={draft}
        busy={reading}
        error={readError}
        initialUrl={siteOrigin}
        onLoad={(url) => void loadFromSite(url)}
        onApply={applyPicked}
      />

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
      </label>

      <label className={styles.label}>
        소재지
        <input
          className={styles.input}
          value={values.addressTerms}
          onChange={set('addressTerms')}
          placeholder="서울 강남구 테헤란로, 강남역"
        />
      </label>

      <label className={styles.label}>
        {isOwnBrand ? '자사 도메인' : '홈페이지 도메인'}
        <input
          className={invalid === 'ownDomains' ? styles.inputInvalid : styles.input}
          value={values.ownDomains}
          onChange={(event) => {
            setInvalid(null);
            set('ownDomains')(event);
          }}
          placeholder="ondam.kr"
          aria-invalid={invalid === 'ownDomains'}
        />
      </label>

      {/*
        한 칸에 원장명·시술·진료시간을 다 넣게 두면 채우기 힘들고, 무엇을 넣어야
        하는지도 안 보인다(사장님 지적 2026-08-08). 셋으로 나눠 받고 보낼 때 합친다.

        **진료시간은 여기 두지 않는다.** 이 값들은 AI 답변 본문과 글자로 대조해 "이
        언급이 우리 업체인가" 를 가리는 데 쓴다(`detection/disambiguation.py`).
        답변에 "월~금 09:00-18:00" 이 나올 일은 거의 없어서, 넣어도 대조에 안 걸리고
        칸만 채운다.
      */}
      <label className={styles.label}>
        원장·의료진 이름
        <input
          className={styles.input}
          value={values.doctorNames}
          onChange={set('doctorNames')}
          placeholder="정세현, 홍길동"
        />
      </label>

      <label className={styles.label}>
        진료과목·대표 시술
        <input
          className={styles.input}
          value={values.treatments}
          onChange={set('treatments')}
          placeholder="추나요법, 다이어트, 교통사고"
        />
      </label>

      <label className={styles.label}>
        그 밖의 구별 표현
        <input
          className={styles.input}
          value={values.otherTerms}
          onChange={set('otherTerms')}
          placeholder="건물명, 층수, 함께 쓰는 별칭"
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
          홈페이지 주소 (전체)
          <input
            className={styles.input}
            value={values.homepageUrl}
            onChange={set('homepageUrl')}
            placeholder="https://competitor.kr"
          />
          </label>
      ) : null}

      {modal === null ? null : (
        /* 왜 안 되는지는 **틀렸을 때만** 말한다. 칸 아래에 미리 적어 두면 아무도
           안 읽고, 정작 틀렸을 때는 안 보인다. */
        <div className={styles.modalBackdrop} role="presentation" onClick={() => setModal(null)}>
          <div
            className={styles.modal}
            role="alertdialog"
            aria-modal="true"
            aria-label="입력을 확인해 주십시오"
            onClick={(event) => event.stopPropagation()}
          >
            <p className={styles.modalBody}>{modal}</p>
            <Button type="button" onClick={() => setModal(null)}>
              확인
            </Button>
          </div>
        </div>
      )}

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
