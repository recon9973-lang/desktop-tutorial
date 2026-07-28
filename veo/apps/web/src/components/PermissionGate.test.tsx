import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { PermissionGate } from './PermissionGate';

const PROTECTED = '조치가 필요한 항목 12건';

describe('PermissionGate', () => {
  it('renders the protected content when the permission is held', () => {
    render(
      <PermissionGate identity={{ permissions: ['issue:read'] }} permission="issue:read">
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );
    expect(screen.getByText(PROTECTED)).toBeInTheDocument();
  });

  it('renders the denial instead of the content when the permission is missing', () => {
    render(
      <PermissionGate identity={{ permissions: ['report:read'] }} permission="issue:read">
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );

    expect(screen.queryByText(PROTECTED)).toBeNull();
    expect(screen.getByText('권한이 없습니다')).toBeInTheDocument();
  });

  it('denies when there is no identity', () => {
    render(
      <PermissionGate identity={null} permission="issue:read">
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );
    expect(screen.queryByText(PROTECTED)).toBeNull();
    expect(screen.getByText('권한이 없습니다')).toBeInTheDocument();
  });

  it('never leaks the protected content into the markup when denied', () => {
    const { container } = render(
      <PermissionGate identity={{ permissions: [] }} permission="issue:read">
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );
    expect(container.innerHTML).not.toContain(PROTECTED);
  });

  it('explains which permission is required, so the reader can ask for the right thing', () => {
    render(
      <PermissionGate identity={{ permissions: [] }} permission="issue:read">
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );
    expect(screen.getByText('issue:read')).toBeInTheDocument();
  });

  it('announces the denial as a status region rather than only in colour', () => {
    render(
      <PermissionGate identity={{ permissions: [] }} permission="issue:read">
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('권한이 없습니다');
  });

  it('uses a caller-supplied fallback when one is given', () => {
    render(
      <PermissionGate
        identity={{ permissions: [] }}
        permission="issue:read"
        fallback={<p>리포트만 열람할 수 있습니다.</p>}
      >
        <p>{PROTECTED}</p>
      </PermissionGate>,
    );
    expect(screen.getByText('리포트만 열람할 수 있습니다.')).toBeInTheDocument();
    expect(screen.queryByText('권한이 없습니다')).toBeNull();
  });
});
