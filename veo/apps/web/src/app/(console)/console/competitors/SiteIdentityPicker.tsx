'use client';

import { useState } from 'react';
import { Button, FormError } from '@veo/ui';

import styles from './competitors.module.css';

/**
 * 홈페이지에서 읽어 온 식별 정보를 **고르게** 한다.
 *
 * 자동으로 채우지 않는 이유는 편의의 문제가 아니다. 식별 값이 하나 더해지면 판별
 * 확신도가 올라가고, 확정선(0.75)을 넘으면 **사람 검수를 건너뛴다.** 그래서 틀린 값을
 * 자동으로 넣는 것은 틀린 판정을 검수 없이 확정시키는 일이다.
 *
 * 거래처 홈페이지 5곳에서 실제로 나온 오검출(2026-08-09) —
 * 소재지 후보 `변경시 반드시 사전동`(개인정보처리방침 문장 토막), 대표번호 자리에 담당자
 * 휴대폰, 대표자 자리에 `원장` `소개` `정회원`. 서버가 상당수를 걸러 내지만 남는 것이
 * 있고, 남는 것을 거르는 것은 사람이다.
 *
 * 그래서 **사이트가 스스로 선언한 값만 미리 체크된다.** 본문에서 찾은 값은 사람이
 * 직접 누른다.
 */

export type CandidateField =
  | 'DISPLAY_NAME'
  | 'OWN_DOMAIN'
  | 'PHONE'
  | 'ADDRESS'
  | 'REPRESENTATIVE'
  | 'BUSINESS_NUMBER';

export interface IdentityCandidate {
  readonly field: CandidateField;
  readonly value: string;
  readonly source: string;
  readonly preselected: boolean;
  readonly note_ko: string;
}

export interface SiteIdentityDraft {
  readonly url: string;
  readonly candidates: readonly IdentityCandidate[];
  readonly notes_ko: readonly string[];
}

/** 고른 값이 들어갈 폼의 칸. */
export type PickedValues = {
  displayName?: string;
  ownDomains?: string;
  phoneNumbers?: string;
  addressTerms?: string;
  doctorNames?: string;
};

const LABELS: Record<CandidateField, string> = {
  DISPLAY_NAME: '상호',
  OWN_DOMAIN: '홈페이지 도메인',
  PHONE: '대표번호',
  ADDRESS: '소재지',
  REPRESENTATIVE: '대표자·원장',
  BUSINESS_NUMBER: '사업자등록번호',
};

/**
 * 고를 수 있는 항목의 순서 — **효과가 큰 순서**다.
 *
 * `BUSINESS_NUMBER` 는 여기 없다. 고르는 값이 아니라 **참고로 보여 주는 값**이기
 * 때문이다. 이 값들은 AI 답변 본문과 글자로 대조해 "이 언급이 우리 업체인가" 를
 * 가린다(`detection/disambiguation.py`). 답변에 사업자등록번호가 인쇄될 일은 거의
 * 없어서, 넣어도 대조에 안 걸리고 칸만 채운다 — 진료시간을 구별 표현에 넣지 않는
 * 것과 같은 이유다. 대신 같은 상호의 다른 업체인지 사람이 대조할 때 쓰라고 보여 준다.
 */
const PICKABLE: readonly CandidateField[] = [
  'DISPLAY_NAME',
  'PHONE',
  'ADDRESS',
  'OWN_DOMAIN',
  'REPRESENTATIVE',
];

/** 한 칸에 값 하나만 들어가는 항목. 여러 개를 고를 수 없다. */
const SINGLE: readonly CandidateField[] = ['DISPLAY_NAME'];

const TARGET: Record<CandidateField, keyof PickedValues | null> = {
  DISPLAY_NAME: 'displayName',
  OWN_DOMAIN: 'ownDomains',
  PHONE: 'phoneNumbers',
  ADDRESS: 'addressTerms',
  REPRESENTATIVE: 'doctorNames',
  BUSINESS_NUMBER: null,
};

function keyOf(one: IdentityCandidate): string {
  return `${one.field}:${one.value}`;
}

/**
 * 처음 체크돼 있는 것 — 사이트가 스스로 선언한 값뿐이다.
 *
 * 칸이 하나인 항목(:data:`SINGLE`)은 **하나만** 체크한다. 실측 2026-08-09 —
 * venomad.com 은 구조화 데이터와 `og:site_name` 에 서로 다른 상호를 적어 두어
 * 선언된 상호가 둘이었다. 둘 다 체크해 두면 화면은 둘을 고른 것처럼 보이는데 저장은
 * 하나만 된다. 무엇이 저장될지 화면이 거짓말하게 두지 않는다.
 */
export function initialPicks(draft: SiteIdentityDraft): ReadonlySet<string> {
  const picked = new Set<string>();
  const takenSingles = new Set<CandidateField>();
  for (const one of draft.candidates) {
    if (!one.preselected) continue;
    if (SINGLE.includes(one.field)) {
      if (takenSingles.has(one.field)) continue;
      takenSingles.add(one.field);
    }
    picked.add(keyOf(one));
  }
  return picked;
}

/** 고른 것을 폼의 칸별 문자열로 모은다. 여러 개면 쉼표로 잇는다. */
export function collectPicked(
  draft: SiteIdentityDraft,
  picked: ReadonlySet<string>,
): PickedValues {
  const out: PickedValues = {};
  for (const field of PICKABLE) {
    const chosen = draft.candidates
      .filter((one) => one.field === field && picked.has(keyOf(one)))
      .map((one) => one.value);
    if (chosen.length === 0) continue;
    const target = TARGET[field];
    if (target === null) continue;
    out[target] = SINGLE.includes(field) ? (chosen[0] as string) : chosen.join(', ');
  }
  return out;
}

export function SiteIdentityPicker({
  draft,
  busy,
  error,
  initialUrl = '',
  onLoad,
  onApply,
}: {
  readonly draft: SiteIdentityDraft | null;
  readonly busy: boolean;
  readonly error: string | null;
  /** 이미 등록된 홈페이지 주소. 있으면 미리 채운다 — 같은 것을 두 번 치게 하지 않는다. */
  readonly initialUrl?: string;
  readonly onLoad: (url: string) => void;
  readonly onApply: (picked: PickedValues) => void;
}) {
  const [url, setUrl] = useState(initialUrl);
  const [picked, setPicked] = useState<ReadonlySet<string>>(new Set());
  /** 어느 초안에 대한 선택인지. 새 초안이 오면 선택을 갈아엎는다. */
  const [pickedFor, setPickedFor] = useState<string | null>(null);

  // 초안이 바뀌면 선택을 다시 잡는다. `useEffect` 로 상태를 지우는 대신 그리는 중에
  // 견주는 이유는, 지난 사이트에서 고른 값이 한 프레임이라도 새 사이트의 것처럼
  // 보이면 안 되기 때문이다.
  const stamp = draft === null ? null : `${draft.url}#${draft.candidates.length}`;
  const current = stamp === pickedFor ? picked : draft === null ? new Set<string>() : initialPicks(draft);
  if (stamp !== pickedFor && draft !== null) {
    setPickedFor(stamp);
    setPicked(current);
  }

  function toggle(one: IdentityCandidate): void {
    const next = new Set(current);
    if (SINGLE.includes(one.field)) {
      for (const key of current) {
        if (key.startsWith(`${one.field}:`)) next.delete(key);
      }
    }
    if (current.has(keyOf(one))) next.delete(keyOf(one));
    else next.add(keyOf(one));
    setPicked(next);
    setPickedFor(stamp);
  }

  const references = draft?.candidates.filter((one) => one.field === 'BUSINESS_NUMBER') ?? [];

  return (
    <section className={styles.fromSite} aria-labelledby="from-site-heading">
      <h3 id="from-site-heading" className={styles.fromSiteTitle}>
        홈페이지에서 불러오기
      </h3>
      <p className={styles.fromSiteLede}>
        상호·대표번호·소재지·대표자를 읽어 옵니다. <strong>읽어 오기만 하고 저장하지
        않습니다</strong> — 맞는 것만 골라 주십시오.
      </p>

      <div className={styles.fromSiteRow}>
        <input
          className={styles.input}
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://ondam.kr"
          aria-label="읽어 올 홈페이지 주소"
        />
        <Button
          type="button"
          variant="secondary"
          busy={busy}
          onClick={() => onLoad(url.trim())}
        >
          불러오기
        </Button>
      </div>

      <FormError message={error} />

      {draft === null ? null : (
        <>
          {draft.notes_ko.map((note) => (
            <p key={note} className={styles.fromSiteNote}>
              {note}
            </p>
          ))}

          {PICKABLE.map((field) => {
            const found = draft.candidates.filter((one) => one.field === field);
            if (found.length === 0) return null;
            return (
              <fieldset key={field} className={styles.fromSiteGroup}>
                <legend className={styles.fromSiteLegend}>{LABELS[field]}</legend>
                {found.map((one) => (
                  <label key={keyOf(one)} className={styles.fromSiteChoice}>
                    <input
                      type="checkbox"
                      checked={current.has(keyOf(one))}
                      onChange={() => toggle(one)}
                    />
                    <span className={styles.fromSiteValue}>{one.value}</span>
                    <span className={styles.fromSiteWhy}>{one.note_ko}</span>
                  </label>
                ))}
              </fieldset>
            );
          })}

          {references.length === 0 ? null : (
            <p className={styles.fromSiteNote}>
              사업자등록번호 {references.map((one) => one.value).join(', ')} — 참고용입니다.
              AI 답변에 인쇄될 일이 거의 없어 식별에는 쓰지 않습니다. 같은 상호의 다른
              업체인지 대조하실 때 쓰십시오.
            </p>
          )}

          {draft.candidates.length === 0 ? null : (
            <Button type="button" variant="secondary" onClick={() => onApply(collectPicked(draft, current))}>
              고른 값 넣기
            </Button>
          )}
        </>
      )}
    </section>
  );
}
