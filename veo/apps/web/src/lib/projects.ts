import 'server-only';

import { callConsoleApi, readAllPages, type ConsoleOutcome } from '@/lib/console-api';
import { record, text, textOrNull } from '@/lib/json';

/**
 * 프로젝트 — 측정이 실제로 매달리는 단위.
 *
 * 업체 화면은 세 단계(고객 → 프로젝트 → 사이트)를 일부러 감춘다. 직원이 URL 하나를
 * 넣으면 가운데 프로젝트는 알아서 생긴다. 그럼에도 이 화면이 따로 있는 이유는,
 * **브랜드 식별과 GEO 관측이 업체가 아니라 프로젝트에 달리기 때문**이다. 어느
 * 프로젝트가 잴 준비가 되었는지는 업체 화면으로는 알 수 없다.
 *
 * 그래서 여기는 등록하는 자리가 아니라 **어디까지 준비됐는지 보는 자리**다.
 */

export interface ProjectSite {
  readonly id: string;
  readonly origin: string;
  readonly isPrimary: boolean;
}

export interface ProjectRow {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly locale: string;
  /** 업체명. 프로젝트가 어느 고객사에도 붙어 있지 않으면 null 이다. */
  readonly customerName: string | null;
  readonly sites: readonly ProjectSite[];
  readonly seoSpecVersion: string | null;
  readonly geoSpecVersion: string | null;
}


function items(data: unknown): readonly Record<string, unknown>[] {
  return Array.isArray(data) ? data.map(record) : [];
}



/**
 * 프로젝트 목록.
 *
 * 목록 세 벌을 한 번씩 읽고 여기서 이어 붙인다. 프로젝트마다 사이트를 따로 부르면
 * 프로젝트 수만큼 왕복이 늘어난다.
 */
export async function listProjects(): Promise<ConsoleOutcome<readonly ProjectRow[]>> {
  const projects = await readAllPages('/api/projects');
  if (!projects.ok) return projects;

  const customers = await readAllPages('/api/customers');
  if (!customers.ok) return customers;

  const sites = await readAllPages('/api/sites');
  if (!sites.ok) return sites;

  const nameByCustomer = new Map<string, string>();
  for (const customer of items(customers.data)) {
    nameByCustomer.set(text(customer, 'id'), text(customer, 'name'));
  }

  const sitesByProject = new Map<string, ProjectSite[]>();
  for (const site of items(sites.data)) {
    const projectId = text(site, 'project_id');
    const list = sitesByProject.get(projectId) ?? [];
    list.push({
      id: text(site, 'id'),
      origin: text(site, 'origin'),
      isPrimary: site['is_primary'] === true,
    });
    sitesByProject.set(projectId, list);
  }

  const rows = items(projects.data).map((project) => {
    const id = text(project, 'id');
    const customerId = textOrNull(project, 'customer_id');
    return {
      id,
      name: text(project, 'name'),
      slug: text(project, 'slug'),
      locale: text(project, 'locale'),
      customerName: customerId === null ? null : (nameByCustomer.get(customerId) ?? null),
      sites: sitesByProject.get(id) ?? [],
      seoSpecVersion: textOrNull(project, 'default_seo_spec_version'),
      geoSpecVersion: textOrNull(project, 'default_geo_spec_version'),
    };
  });

  return { ok: true, data: rows, meta: projects.meta };
}

/**
 * 프로젝트 이름을 고친다 — **만들면 못 고치던 것**(v0.3.83).
 *
 * 서버에는 `PATCH /api/projects/{id}` 가 처음부터 있었다. 화면이 없어서 오타 하나도
 * 못 고쳤다(`audit/2026-08-08-server-ui-gap.md` §B). 브랜드에서 같은 모양의 구멍이
 * 이미 두 번 나왔다(v0.3.69).
 *
 * **이름만 보낸다.** 서버는 slug·업체·지역·명세 판까지 받지만, 그것들은 측정 조건이라
 * 바꾸면 지난 진단과 비교가 끊긴다(ADR 0010). 화면에서 무심코 바뀌면 안 되는 값이다 —
 * 필요해지면 그때 따로 연다.
 */
export async function updateProject(
  projectId: string,
  changes: { readonly name: string },
): Promise<ConsoleOutcome<{ readonly id: string; readonly name: string }>> {
  const outcome = await callConsoleApi(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'PATCH',
    body: { name: changes.name },
  });
  if (!outcome.ok) return outcome;

  const row = record(outcome.data);
  return {
    ok: true,
    data: { id: text(row, 'id'), name: text(row, 'name') },
    meta: outcome.meta,
  };
}
