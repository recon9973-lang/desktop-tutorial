import { describe, expect, it, vi } from 'vitest';
import { createRef } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Button } from './Button/Button';
import { FormError } from './FormError/FormError';
import { ScoreCard } from './ScoreCard/ScoreCard';
import { CHECK_STATUSES, CHECK_STATUS_DESCRIPTORS, StatusChip } from './StatusChip/StatusChip';
import { TextField } from './TextField/TextField';
import { UserMenu } from './UserMenu/UserMenu';

/**
 * Regression cover for the defects found in the WCAG 2.2 AA audit.
 *
 * Each `describe` names the success criterion it protects. What these cannot
 * check is anything that needs layout or a real accessibility tree: colour
 * (jsdom applies no CSS), focus *visibility*, or how a screen reader actually
 * voices a region. Those are listed in `apps/web/docs/accessibility.md` as
 * manual checks.
 */

describe('Button · SC 2.4.3 focus order', () => {
  it('never becomes `disabled` merely because it is busy', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<Button type="submit">로그인</Button>);

    const button = screen.getByRole('button', { name: '로그인' });
    await user.tab();
    expect(document.activeElement).toBe(button);

    rerender(
      <Button type="submit" busy>
        로그인
      </Button>,
    );

    // A real browser removes a `disabled` button from the tab order and drops
    // focus to <body>, throwing the reader to the top of the page at the exact
    // moment they are waiting for a result. jsdom does not reproduce that blur,
    // so what is asserted here is the cause rather than the effect: the element
    // stays enabled and stays in the tab order. The focus behaviour itself is
    // on the manual list in apps/web/docs/accessibility.md.
    expect(button).toBeEnabled();
    expect(button).not.toHaveAttribute('tabindex', '-1');
    expect(document.activeElement).toBe(button);
  });

  it('announces the busy state without lying about being disabled', () => {
    render(<Button busy>로그인</Button>);
    const button = screen.getByRole('button', { name: /로그인/ });
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toBeEnabled();
  });

  it('ignores a click while busy, so aria-disabled is not a decoration', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button busy onClick={onClick}>
        로그인
      </Button>,
    );
    await user.click(screen.getByRole('button', { name: /로그인/ }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('still honours a genuinely disabled button', () => {
    render(<Button disabled>프로젝트 등록</Button>);
    expect(screen.getByRole('button', { name: '프로젝트 등록' })).toBeDisabled();
  });
});

describe('FormError · SC 3.3.1 error identification', () => {
  it('can be given focus, so a form can send the reader to the summary', () => {
    const ref = createRef<HTMLDivElement>();
    render(<FormError ref={ref} message="이메일을 입력해 주세요." />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('tabindex', '-1');
    ref.current?.focus();
    expect(document.activeElement).toBe(alert);
  });

  it('is not reachable by Tab, only by being sent there', async () => {
    const user = userEvent.setup();
    render(
      <>
        <FormError message="이메일을 입력해 주세요." />
        <button type="button">확인</button>
      </>,
    );
    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: '확인' }));
  });

  it('lists each problem so the summary names what to fix', () => {
    render(
      <FormError
        message="입력을 확인해 주세요."
        problems={['이메일을 입력해 주세요.', '비밀번호를 입력해 주세요.']}
      />,
    );
    const items = within(screen.getByRole('alert')).getAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual([
      '이메일을 입력해 주세요.',
      '비밀번호를 입력해 주세요.',
    ]);
  });
});

describe('StatusChip · SC 1.4.1 use of colour', () => {
  it('gives every state a distinct icon shape and a distinct Korean label', () => {
    const shapes = new Set<string>();
    const labels = new Set<string>();

    for (const status of CHECK_STATUSES) {
      const { container, unmount } = render(<StatusChip status={status} />);
      const chip = container.querySelector('[data-status]');
      expect(chip?.getAttribute('data-status')).toBe(status);

      const shape = container.querySelector('[data-shape]')?.getAttribute('data-shape');
      expect(shape, `${status} has no shape indicator`).toBeTruthy();
      shapes.add(shape ?? '');
      labels.add(CHECK_STATUS_DESCRIPTORS[status].label);

      // The visible label is the signal a monochrome rendering falls back to.
      expect(chip?.textContent).toContain(CHECK_STATUS_DESCRIPTORS[status].label);
      unmount();
    }

    expect(shapes.size).toBe(CHECK_STATUSES.length);
    expect(labels.size).toBe(CHECK_STATUSES.length);
  });

  it('marks the icon decorative, because the text already carries the state', () => {
    const { container } = render(<StatusChip status="UNKNOWN" />);
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('측정 불가')).toBeInTheDocument();
  });
});

describe('ScoreCard · SC 1.4.1 use of colour', () => {
  it('marks an unmeasured score in the markup, not only by tinting the number', () => {
    const { container } = render(
      <ScoreCard
        title="SEO 기술 준비도"
        score={null}
        specVersion="veo.seo.readiness 1.0.0"
        coverage={0}
        confidence={0}
      />,
    );
    expect(container.querySelector('[data-veo-score-state="unmeasured"]')).not.toBeNull();
    expect(screen.getByText('측정 불가')).toBeInTheDocument();
  });

  it('marks a real score as scored', () => {
    const { container } = render(
      <ScoreCard
        title="SEO 기술 준비도"
        score={72.4}
        specVersion="veo.seo.readiness 1.0.0"
        coverage={1}
        confidence={0.8}
        bandLabel="양호"
      />,
    );
    expect(container.querySelector('[data-veo-score-state="scored"]')).not.toBeNull();
    // The band is a word, not a colour: it survives being read aloud.
    expect(screen.getByText('양호')).toBeInTheDocument();
  });

  it('reads the score out with its scale rather than as a bare number', () => {
    render(
      <ScoreCard
        title="SEO 기술 준비도"
        score={72.4}
        specVersion="veo.seo.readiness 1.0.0"
        coverage={1}
        confidence={0.8}
      />,
    );
    expect(screen.getByText(/100점 만점에 72\.4점/)).toBeInTheDocument();
  });
});

describe('UserMenu · SC 4.1.1 unique ids', () => {
  it('can be rendered twice on one page without colliding ids', () => {
    const { container } = render(
      <>
        <UserMenu name="이재훈" email="a@example.com" roleLabels={['분석가']} defaultOpen />
        <UserMenu name="박세일" email="b@example.com" roleLabels={['영업']} defaultOpen />
      </>,
    );

    const ids = [...container.querySelectorAll('[id]')].map((node) => node.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('names the role list without depending on a shared id', () => {
    render(
      <UserMenu name="이재훈" email="a@example.com" roleLabels={['분석가']} defaultOpen />,
    );
    expect(screen.getByRole('list', { name: '역할' })).toBeInTheDocument();
  });
});

describe('TextField · SC 3.3.1 / 3.3.2', () => {
  it('ties the error to the input and marks the input invalid', () => {
    render(
      <TextField
        id="veo-email"
        label="이메일"
        name="email"
        error="이메일 형식이 올바르지 않습니다."
        hint="회사 계정으로 로그인하세요."
      />,
    );

    const input = screen.getByLabelText(/이메일/);
    expect(input).toHaveAttribute('aria-invalid', 'true');

    const describedBy = (input.getAttribute('aria-describedby') ?? '').split(' ');
    const described = describedBy
      .map((id) => document.getElementById(id)?.textContent ?? '')
      .join(' | ');

    // The correction is announced before the guidance that has already been read.
    expect(described).toMatch(/이메일 형식이 올바르지 않습니다\..*회사 계정으로 로그인하세요\./);
  });

  it('leaves a valid field free of aria-invalid rather than setting it to false', () => {
    render(<TextField label="이메일" name="email" />);
    expect(screen.getByLabelText('이메일')).not.toHaveAttribute('aria-invalid');
  });
});
