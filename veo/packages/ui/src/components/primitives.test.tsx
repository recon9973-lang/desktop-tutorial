import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from './Button/Button';
import { Card } from './Card/Card';
import { EmptyState } from './EmptyState/EmptyState';
import { ErrorState } from './ErrorState/ErrorState';
import { Skeleton } from './Skeleton/Skeleton';

describe('Button', () => {
  it('renders a real button element with its label', () => {
    render(<Button>측정 시작</Button>);
    expect(screen.getByRole('button', { name: '측정 시작' })).toBeInTheDocument();
  });

  it('announces a busy button to assistive tech without dropping it from the tab order', () => {
    render(<Button busy>측정 시작</Button>);
    const button = screen.getByRole('button', { name: /측정 시작/ });
    // `disabled` would take focus away from whoever pressed it. See
    // `a11y.test.tsx` — "Button · SC 2.4.3 focus order".
    expect(button).toBeEnabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveAttribute('aria-disabled', 'true');
  });
});

describe('Card', () => {
  it('renders a titled section as a labelled region', () => {
    render(
      <Card title="점검 항목">
        <p>본문</p>
      </Card>,
    );
    const region = screen.getByRole('region', { name: '점검 항목' });
    expect(region).toBeInTheDocument();
    expect(screen.getByText('본문')).toBeInTheDocument();
  });
});

describe('Skeleton', () => {
  it('is hidden from assistive tech and announces a loading state on its container', () => {
    const { container } = render(<Skeleton lines={3} label="불러오는 중" />);
    const root = container.firstElementChild;
    expect(root).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('불러오는 중')).toBeInTheDocument();
    expect(container.querySelectorAll('[data-skeleton-line]')).toHaveLength(3);
  });
});

describe('EmptyState', () => {
  it('renders the standard Korean empty message without inventing a number', () => {
    const { container } = render(<EmptyState />);
    expect(screen.getByText('아직 측정 데이터가 없습니다')).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\d/);
  });

  it('accepts a custom description and action', () => {
    render(
      <EmptyState
        description="프로젝트를 등록하면 점검을 시작할 수 있습니다."
        action={<Button>프로젝트 등록</Button>}
      />,
    );
    expect(
      screen.getByText('프로젝트를 등록하면 점검을 시작할 수 있습니다.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '프로젝트 등록' })).toBeInTheDocument();
  });
});

describe('ErrorState', () => {
  it('renders as an alert with a Korean message', () => {
    render(<ErrorState description="데이터를 불러오지 못했습니다." />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('데이터를 불러오지 못했습니다.');
  });
});
