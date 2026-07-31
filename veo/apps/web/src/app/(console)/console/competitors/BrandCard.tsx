import type { Brand } from '@/lib/brands';
import { strengthLabel } from '@/lib/brands';

import styles from './competitors.module.css';

/**
 * 브랜드 한 건 — 그리고 **이 상태로 측정이 되는지.**
 *
 * 등록된 값을 나열하는 것이 목적이 아니다. 목적은 `측정 불가` 를 눈에 띄게 만드는
 * 것이다. 그 상태로 관측을 돌리면 이 브랜드의 언급이 전부 검수 대기로 넘어가고,
 * 사용자는 결과를 보고 나서야 "왜 다 보류지" 를 묻게 된다. 그때는 이미 돈이 나갔다.
 */
export function BrandCard({ brand }: { readonly brand: Brand }) {
  const measurable = brand.identity_strength === 'SUFFICIENT';

  return (
    <li className={measurable ? styles.brand : styles.brandWeak}>
      <p className={styles.brandHead}>
        <span className={styles.brandName}>{brand.display_name}</span>
        <span className={measurable ? styles.ok : styles.warn}>
          {strengthLabel(brand.identity_strength)}
        </span>
        {brand.name_is_generic ? (
          <span className={styles.generic}>여러 업체가 함께 쓰는 이름</span>
        ) : null}
      </p>

      <dl className={styles.fields}>
        <Field label="등록 도메인" values={brand.own_domains} />
        <Field label="소재지" values={brand.address_terms} />
        <Field label="대표번호" values={brand.phone_numbers} />
        <Field label="구별 표현" values={brand.distinguishing_terms} />
        <Field label="다른 이름" values={brand.aliases} />
      </dl>

      {brand.gaps_ko.length > 0 ? (
        <ul className={styles.gaps}>
          {brand.gaps_ko.map((gap) => (
            <li key={gap}>{gap}</li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/** 빈 칸을 감추지 않는다. 비어 있다는 사실이 이 화면에서 가장 중요한 정보다. */
function Field({ label, values }: { readonly label: string; readonly values: readonly string[] }) {
  return (
    <div className={styles.field}>
      <dt>{label}</dt>
      <dd className={values.length === 0 ? styles.empty : undefined}>
        {values.length === 0 ? '없음' : values.join(' · ')}
      </dd>
    </div>
  );
}
