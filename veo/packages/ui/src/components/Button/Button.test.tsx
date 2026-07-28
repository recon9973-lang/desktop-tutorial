import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Button } from './Button';

describe('Button — busy', () => {
  it('stays focusable while busy, so the reader is not thrown to the top of the page', () => {
    render(<Button busy>저장</Button>);
    const button = screen.getByRole('button', { name: '저장' });

    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveAttribute('aria-disabled', 'true');
  });

  it('swallows a click while busy, so a second submit is not sent', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(
      <Button busy onClick={onClick}>
        저장
      </Button>,
    );
    await user.click(screen.getByRole('button', { name: '저장' }));

    expect(onClick).not.toHaveBeenCalled();
  });

  it('passes the click through when it is not busy', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={onClick}>저장</Button>);
    await user.click(screen.getByRole('button', { name: '저장' }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('a genuinely disabled button is still disabled', () => {
    render(<Button disabled>저장</Button>);
    expect(screen.getByRole('button', { name: '저장' })).toBeDisabled();
  });
});

describe('Button — serialisable from a Server Component', () => {
  /**
   * A Server Component cannot pass a function prop across a client boundary. React
   * answers with "Event handlers cannot be passed to Client Component props" — a
   * *runtime* error, so the build succeeds, the deploy succeeds, and the page fails.
   *
   * That is how it reached production. Keeping a button focusable while busy meant
   * attaching an `onClick` to swallow the second click, and it was attached
   * unconditionally. Every `/console/*` route is server-rendered, so every one of
   * them returned 500 while the public pages carried on working normally.
   *
   * No test here caught it, because every one of them renders on the client — where
   * a handler is perfectly legal. So these assert on the *element* rather than on
   * behaviour: a button that is neither busy nor given an `onClick` must carry no
   * handler at all, and therefore stay serialisable.
   */
  /**
   * Called as a function, not written as JSX. `<Button busy/>` builds an element
   * whose props are what was *passed in*; calling it returns the `<button>` it
   * renders, which is where the handler either is or is not.
   */
  function renderedProps(props: Parameters<typeof Button>[0]): { onClick?: unknown } {
    return (Button(props) as ReactElement<{ onClick?: unknown }>).props;
  }

  it('attaches no click handler when it is neither busy nor given one', () => {
    expect(renderedProps({ children: '저장' }).onClick).toBeUndefined();
  });

  it('attaches one when busy, so the second submit can be swallowed', () => {
    expect(typeof renderedProps({ children: '저장', busy: true }).onClick).toBe('function');
  });

  it('attaches one when the caller supplies it', () => {
    expect(typeof renderedProps({ children: '저장', onClick: () => {} }).onClick).toBe(
      'function',
    );
  });
});
