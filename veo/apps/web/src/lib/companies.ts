import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';

/**
 * 업체와 그 업체의 측정 URL.
 *
 * 엔진의 도메인 모델은 고객 → 프로젝트 → 사이트 세 단계다. 직원에게 그 세 단계를 밟게
 * 하지 않는다 — 단계 수는 구현 사정이지 사용자가 알아야 할 일이 아니다. 화면은 **업체명과
 * 측정 URL** 만 받고, 가운데 프로젝트는 여기서 만든다.
 *
 * 업체에게 로그인 계정을 발급하지 않는다. 직원이 URL 을 저장·관리하고 결과를 전달한다.
 */

export interface MeasuredSite {
  readonly siteId: string;
  readonly origin: string;
  readonly displayName: string;
  readonly isPrimary: boolean;
}

export interface Company {
  readonly customerId: string;
  readonly name: string;
  readonly industry: string | null;
  readonly sites: readonly MeasuredSite[];
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/**
 * 목록 응답의 본문.
 *
 * 페이지 응답은 `{ data: [...], page_info }` 이고 `callConsoleApi` 가 이미 `data` 를
 * 벗겨 주므로, 여기 들어오는 값이 곧 배열이다. 한때 `data.items` 를 찾았는데 그런 키는
 * 없어서 **모든 목록이 조용히 빈 배열**이 됐다 — 등록은 성공하는데 화면에는 아무것도
 * 안 나오는, 원인을 찾기 어려운 실패였다.
 */
function items(data: unknown): readonly Record<string, unknown>[] {
  return Array.isArray(data) ? data.map(asRecord) : [];
}

function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}

function textOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

/**
 * 화면에 그릴 업체 목록.
 *
 * 목록 세 벌을 한 번씩 읽고 여기서 이어 붙인다. 업체마다 프로젝트를, 프로젝트마다
 * 사이트를 따로 부르면 업체 수만큼 왕복이 늘어난다 — 서버가 한국에서 멀 때 그 차이가
 * 화면 로딩 전체를 좌우한다.
 */
export async function listCompanies(): Promise<ConsoleOutcome<readonly Company[]>> {
  const customers = await callConsoleApi('/api/customers?page_size=200');
  if (!customers.ok) return customers;

  const projects = await callConsoleApi('/api/projects?page_size=200');
  if (!projects.ok) return projects;

  const sites = await callConsoleApi('/api/sites?page_size=200');
  if (!sites.ok) return sites;

  const sitesByProject = new Map<string, MeasuredSite[]>();
  for (const site of items(sites.data)) {
    const projectId = text(site, 'project_id');
    const list = sitesByProject.get(projectId) ?? [];
    list.push({
      siteId: text(site, 'id'),
      origin: text(site, 'origin'),
      displayName: text(site, 'display_name'),
      isPrimary: site['is_primary'] === true,
    });
    sitesByProject.set(projectId, list);
  }

  const sitesByCustomer = new Map<string, MeasuredSite[]>();
  for (const project of items(projects.data)) {
    const customerId = textOrNull(project, 'customer_id');
    if (customerId === null) continue;
    const list = sitesByCustomer.get(customerId) ?? [];
    list.push(...(sitesByProject.get(text(project, 'id')) ?? []));
    sitesByCustomer.set(customerId, list);
  }

  const companies = items(customers.data).map((customer) => {
    const customerId = text(customer, 'id');
    return {
      customerId,
      name: text(customer, 'name'),
      industry: textOrNull(customer, 'industry'),
      sites: sitesByCustomer.get(customerId) ?? [],
    };
  });

  return { ok: true, data: companies, meta: customers.meta };
}

/** URL 을 `https://호스트` 형태로 다듬는다. 경로·질의·자격정보는 사이트 등록이 거부한다. */
export function toOrigin(input: string): string | null {
  const trimmed = input.trim();
  if (trimmed === '') return null;

  // 스킴이 이미 있는데 http·https 가 아니면 **거부한다**. 앞에 `https://` 를 덧붙이면
  // `file:///etc/passwd` 가 `https://file` 이 되어, 있지도 않은 호스트를 지어내게 된다.
  const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(trimmed);
  if (scheme !== null && !/^https?$/i.test(scheme[1] ?? '')) return null;

  const withScheme = scheme === null ? `https://${trimmed}` : trimmed;
  try {
    const url = new URL(withScheme);
    if (url.username !== '' || url.password !== '') return null;
    if (url.protocol !== 'https:' && url.protocol !== 'http:') return null;
    return `${url.protocol}//${url.host}`;
  } catch {
    return null;
  }
}

/** 업체명에서 프로젝트 식별자를 만든다. 한글은 URL 조각으로 쓸 수 없어 접미사에 기댄다. */
function slugFor(name: string, suffix: string): string {
  const ascii = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return ascii === '' ? `site-${suffix}` : `${ascii}-${suffix}`.slice(0, 60);
}

export type CreateCompanyFailure =
  | { readonly reason: 'INVALID_NAME' }
  | { readonly reason: 'INVALID_URL' }
  | { readonly reason: 'API'; readonly outcome: ConsoleOutcome<unknown> };

export type CreateCompanyResult =
  | { readonly ok: true; readonly customerId: string; readonly siteId: string }
  | ({ readonly ok: false } & CreateCompanyFailure);

/**
 * 업체와 첫 측정 URL을 함께 만든다.
 *
 * 세 번의 쓰기가 필요하고 그 사이에 실패할 수 있다. 중간에 끊기면 URL 없는 업체가 남는데,
 * 그 편이 나은 실패다 — 지우고 다시 만들면 되고, 아무것도 조용히 잘못 연결되지 않는다.
 * 되돌리기를 흉내 내려다 절반만 지워지는 쪽이 더 나쁘다.
 */
export async function createCompany(
  name: string,
  rawUrl: string,
  suffix: string,
): Promise<CreateCompanyResult> {
  const companyName = name.trim();
  if (companyName === '') return { ok: false, reason: 'INVALID_NAME' };

  const origin = toOrigin(rawUrl);
  if (origin === null) return { ok: false, reason: 'INVALID_URL' };

  const customer = await callConsoleApi('/api/customers', {
    method: 'POST',
    body: { name: companyName },
  });
  if (!customer.ok) return { ok: false, reason: 'API', outcome: customer };
  const customerId = text(asRecord(customer.data), 'id');

  const project = await callConsoleApi('/api/projects', {
    method: 'POST',
    body: {
      customer_id: customerId,
      slug: slugFor(companyName, suffix),
      name: companyName,
    },
  });
  if (!project.ok) return { ok: false, reason: 'API', outcome: project };

  const site = await callConsoleApi('/api/sites', {
    method: 'POST',
    body: {
      project_id: text(asRecord(project.data), 'id'),
      origin,
      display_name: companyName,
      is_primary: true,
    },
  });
  if (!site.ok) return { ok: false, reason: 'API', outcome: site };

  return { ok: true, customerId, siteId: text(asRecord(site.data), 'id') };
}

/** 이미 있는 업체에 측정 URL 을 더한다. */
export async function addSite(
  customerId: string,
  companyName: string,
  rawUrl: string,
  suffix: string,
): Promise<CreateCompanyResult> {
  const origin = toOrigin(rawUrl);
  if (origin === null) return { ok: false, reason: 'INVALID_URL' };

  const projects = await callConsoleApi(
    `/api/projects?customer_id=${encodeURIComponent(customerId)}&page_size=1`,
  );
  if (!projects.ok) return { ok: false, reason: 'API', outcome: projects };

  const existing = items(projects.data)[0];
  let projectId = existing === undefined ? '' : text(existing, 'id');

  if (projectId === '') {
    const created = await callConsoleApi('/api/projects', {
      method: 'POST',
      body: { customer_id: customerId, slug: slugFor(companyName, suffix), name: companyName },
    });
    if (!created.ok) return { ok: false, reason: 'API', outcome: created };
    projectId = text(asRecord(created.data), 'id');
  }

  const site = await callConsoleApi('/api/sites', {
    method: 'POST',
    body: { project_id: projectId, origin, display_name: origin, is_primary: false },
  });
  if (!site.ok) return { ok: false, reason: 'API', outcome: site };

  return { ok: true, customerId, siteId: text(asRecord(site.data), 'id') };
}


/**
 * 주소로 진단할 자리를 찾거나 만든다.
 *
 * 업체를 먼저 등록하게 하지 않는다 — 영업 중에 주소 하나를 넣어 보는 것이 이 도구의
 * 첫 쓰임인데, 그 앞에 등록 절차를 세우면 쓰지 않게 된다. 주소를 넣으면 잰다. 저장은
 * 결과가 나온 뒤 **주소를 기준으로** 알아서 된다.
 *
 * 업체명은 처음에는 호스트 이름을 쓰고, 나중에 사람이 바꿀 수 있다. 이름을 먼저 물어서
 * 얻는 것보다, 결과를 보고 나서 정리하는 편이 실제 일하는 순서에 가깝다.
 */
export async function findOrCreateSiteByOrigin(
  rawUrl: string,
  suffix: string,
): Promise<CreateCompanyResult> {
  const origin = toOrigin(rawUrl);
  if (origin === null) return { ok: false, reason: 'INVALID_URL' };

  const sites = await callConsoleApi('/api/sites?page_size=200');
  if (!sites.ok) return { ok: false, reason: 'API', outcome: sites };

  const existing = items(sites.data).find((site) => text(site, 'origin') === origin);
  if (existing !== undefined) {
    // 같은 주소를 다시 넣었다. 새로 만들지 않는다 — 그러면 이력이 두 갈래로 쪼개진다.
    return { ok: true, customerId: '', siteId: text(existing, 'id') };
  }

  const label = hostLabel(origin);
  return createCompany(label, origin, suffix);
}

/** `https://www.ondam.co.kr` → `ondam.co.kr`. 사람이 부르는 이름에 가깝게. */
function hostLabel(origin: string): string {
  try {
    return new URL(origin).host.replace(/^www\./, '');
  } catch {
    return origin;
  }
}
