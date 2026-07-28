import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CHECK_STATUSES, StatusChip } from './StatusChip';
import type { CheckStatus } from './StatusChip';

const EXPECTED_LABELS: Record<CheckStatus, string> = {
  PASS: '통과',
  WARNING: '주의',
  FAIL: '실패',
  NOT_APPLICABLE: '해당 없음',
  UNKNOWN: '측정 불가',
};

describe('StatusChip', () => {
  it('exposes exactly the five check states', () => {
    expect([...CHECK_STATUSES]).toEqual([
      'PASS',
      'WARNING',
      'FAIL',
      'NOT_APPLICABLE',
      'UNKNOWN',
    ]);
  });

  it.each(CHECK_STATUSES)('renders the Korean label for %s', (status) => {
    render(<StatusChip status={status} />);
    expect(screen.getByText(EXPECTED_LABELS[status])).toBeInTheDocument();
  });

  it.each(CHECK_STATUSES)(
    'renders a non-colour shape indicator for %s',
    (status) => {
      const { container } = render(<StatusChip status={status} />);
      const indicator = container.querySelector('[data-shape]');
      expect(indicator).not.toBeNull();
      expect(indicator?.getAttribute('data-shape')).toBeTruthy();
      // The icon is decorative; the text label carries the meaning.
      expect(indicator?.getAttribute('aria-hidden')).toBe('true');
    },
  );

  it('gives every state a distinct shape so colour is never the only signal', () => {
    const shapes = CHECK_STATUSES.map((status) => {
      const { container } = render(<StatusChip status={status} />);
      return container.querySelector('[data-shape]')?.getAttribute('data-shape');
    });
    expect(new Set(shapes).size).toBe(CHECK_STATUSES.length);
    expect(shapes).not.toContain(null);
    expect(shapes).not.toContain(undefined);
  });

  it('reads NOT_APPLICABLE as 해당 없음 and never styles it as a failure', () => {
    const { container } = render(<StatusChip status="NOT_APPLICABLE" />);
    expect(screen.getByText('해당 없음')).toBeInTheDocument();
    const chip = container.querySelector('[data-status="NOT_APPLICABLE"]');
    expect(chip).not.toBeNull();
    expect(chip?.getAttribute('data-tone')).toBe('neutral');

    const failChip = render(<StatusChip status="FAIL" />).container.querySelector(
      '[data-status="FAIL"]',
    );
    expect(failChip?.getAttribute('data-tone')).toBe('danger');
    expect(chip?.getAttribute('data-tone')).not.toBe(
      failChip?.getAttribute('data-tone'),
    );
    expect(chip?.className).not.toBe(failChip?.className);
  });

  it('reads UNKNOWN as 측정 불가 rather than a failure', () => {
    const { container } = render(<StatusChip status="UNKNOWN" />);
    expect(screen.getByText('측정 불가')).toBeInTheDocument();
    expect(
      container.querySelector('[data-status="UNKNOWN"]')?.getAttribute('data-tone'),
    ).toBe('unknown');
  });

  it('renders an accessible description alongside the label when provided', () => {
    render(<StatusChip status="WARNING" detail="정규 URL 일부가 자기 참조가 아닙니다" />);
    expect(screen.getByText('주의')).toBeInTheDocument();
    expect(
      screen.getByText('정규 URL 일부가 자기 참조가 아닙니다'),
    ).toBeInTheDocument();
  });
});
