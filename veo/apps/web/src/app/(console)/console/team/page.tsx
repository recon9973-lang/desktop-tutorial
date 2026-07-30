import type { Metadata } from 'next';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { hasPermission } from '@/lib/permissions';
import { requireConsoleIdentity } from '@/lib/session';
import { listMembers, type Member } from '@/lib/team';
import styles from '@/styles/page.module.css';

import { InviteForm } from './InviteForm';
import { MemberRow } from './MemberRow';
import own from './team.module.css';

export const metadata: Metadata = {
  title: '팀원 관리',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * 한 조직의 사람들.
 *
 * 엔진에는 초대·역할 변경·계정 비활성·재발송이 모두 있었고, 없던 것은 이 화면뿐이었다.
 * 그래서 여기는 새 규칙을 만들지 않는다 — 엔진이 이미 정한 여섯 역할을 그대로 보여주고,
 * 권한 판정도 엔진에 맡긴다.
 *
 * 목록을 보는 것과 사람을 바꾸는 것은 권한이 다르다. `user:read` 만 있으면 명단을 보고,
 * 바꾸려면 `user:manage` 가 필요하다. 링크를 숨기는 것은 예의일 뿐이라, 주소를 직접
 * 쳐도 여기서 다시 막는다.
 */
export default async function TeamPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="user:read">
      <TeamContent
        selfId={identity.userId}
        canManage={hasPermission(identity, 'user:manage')}
      />
    </PermissionGate>
  );
}

async function TeamContent({
  selfId,
  canManage,
}: {
  readonly selfId: string;
  readonly canManage: boolean;
}) {
  const outcome = await listMembers();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>팀원 관리</h1>
        <p className={styles.lede}>
          이 조직에서 콘솔을 쓰는 사람들입니다. 초대하면 1회용 링크가 나오며, 메일은
          자동으로 나가지 않으니 링크를 직접 전달하십시오.
        </p>
      </div>

      {canManage ? (
        <section className={styles.section} aria-labelledby="invite-member">
          <h2 id="invite-member" className={styles.sectionTitle}>
            팀원 초대
          </h2>
          <Card title="새 팀원" headingLevel={3}>
            <InviteForm />
          </Card>
        </section>
      ) : null}

      <section className={styles.section} aria-labelledby="member-list">
        <h2 id="member-list" className={styles.sectionTitle}>
          팀원 {outcome.ok ? `(${outcome.data.length}명)` : ''}
        </h2>

        {canManage ? null : (
          <p className={styles.sectionNote}>
            명단을 보고 있습니다. 초대와 역할 변경은 최고 관리자만 할 수 있습니다.
          </p>
        )}

        {outcome.ok ? (
          <MemberList members={outcome.data} selfId={selfId} canManage={canManage} />
        ) : (
          <ErrorState
            title="팀원을 불러오지 못했습니다"
            description={
              outcome.message ?? '서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.'
            }
          />
        )}
      </section>
    </div>
  );
}

function MemberList({
  members,
  selfId,
  canManage,
}: {
  readonly members: readonly Member[];
  readonly selfId: string;
  readonly canManage: boolean;
}) {
  if (members.length === 0) {
    // 자기 자신은 늘 있으므로 실제로는 거의 나오지 않는다. 그래도 빈 화면을 두지 않는다.
    return <EmptyState description="아직 팀원이 없습니다. 위에서 초대해 시작하십시오." />;
  }

  // 손이 가야 하는 사람부터 위로: 초대 수락 대기 → 활성 → 비활성.
  const ordered = [...members].sort((a, b) => rank(a) - rank(b));

  return (
    <ul className={own.list}>
      {ordered.map((member) => (
        <MemberRow
          key={member.id}
          {...member}
          isSelf={member.id === selfId}
          canManage={canManage}
        />
      ))}
    </ul>
  );
}

function rank(member: Member): number {
  if (!member.isActive) return 2;
  return member.hasPassword ? 1 : 0;
}
