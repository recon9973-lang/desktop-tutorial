import type { ReactNode } from 'react';
import { cx } from '../../utils/cx';
import styles from './Card.module.css';

export type CardTone = 'default' | 'flat' | 'raised';
export type CardHeadingLevel = 2 | 3 | 4;

export interface CardProps {
  /** When present the card becomes a named landmark region. */
  title?: string;
  description?: string;
  headingLevel?: CardHeadingLevel;
  aside?: ReactNode;
  footer?: ReactNode;
  tone?: CardTone;
  id?: string;
  className?: string;
  children: ReactNode;
}

export function Card({
  title,
  description,
  headingLevel = 2,
  aside,
  footer,
  tone = 'default',
  id,
  className,
  children,
}: CardProps) {
  const Heading = `h${headingLevel}` as 'h2' | 'h3' | 'h4';
  const toneClass = tone === 'flat' ? styles.flat : tone === 'raised' ? styles.raised : undefined;

  return (
    <section
      id={id}
      aria-label={title}
      className={cx(styles.card, toneClass, className)}
    >
      {title !== undefined || aside !== undefined ? (
        <div className={styles.header}>
          <div className={styles.headings}>
            {title !== undefined ? <Heading className={styles.title}>{title}</Heading> : null}
            {description !== undefined ? (
              <p className={styles.description}>{description}</p>
            ) : null}
          </div>
          {aside !== undefined ? <div className={styles.aside}>{aside}</div> : null}
        </div>
      ) : null}
      <div className={styles.body}>{children}</div>
      {footer !== undefined ? <div className={styles.footer}>{footer}</div> : null}
    </section>
  );
}
