import 'server-only';

import { callConsoleApi, type ConsoleOutcome, readAllPages } from '@/lib/console-api';

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
  /** 이 사이트가 달린 프로젝트 — 이슈·브랜드가 프로젝트에 달리므로 화면이 건너갈 때 쓴다. */
  readonly projectId: string;
}

export interface Company {
  readonly customerId: string;
  readonly name: string;
  readonly industry: string | null;
  /**
   * 소재지. **상호는 식별자가 아니다** — 서울치과는 수십 곳이라, 목록에 이름만
   * 있으면 어느 곳을 맡고 있는지 사람이 가리지 못한다.
   *
   * 측정에 쓰는 값이 아니다. AI 답변과 대조하는 소재지 표현은 브랜드 식별의
   * `address_terms` 에 따로 있다.
   */
  readonly address: string | null;
  /** 사람이 거래처로 등록했는가. 주소만 넣고 재 본 자리는 false 다. */
  readonly isRegistered: boolean;
  readonly sites: readonly MeasuredSite[];
  /** 이 업체의 프로젝트들. 브랜드 식별·관측은 **프로젝트**에 달린다. */
  readonly projects: readonly { readonly id: string; readonly name: string }[];
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
export async function listCompanies(
  {
    registered,
  }: {
    /**
     * true 면 거래처만, false 면 재 본 자리만, 생략하면 둘 다.
     *
     * 기본을 "거래처만" 으로 두지 않는다 — 부르는 곳이 일곱이고, 그중 하나라도 전부를
     * 뜻했다면 조용히 절반만 받는다. 무엇을 원하는지는 부르는 화면이 말한다.
     */
    registered?: boolean;
  } = {},
): Promise<ConsoleOutcome<readonly Company[]>> {
  const filter = registered === undefined ? '' : `?registered=${String(registered)}`;
  // 세 벌은 서로를 필요로 하지 않는다. 줄을 세우면 왕복이 세 번이고, 서버가 한국에서
  // 멀 때 그 두 번이 그대로 화면 대기 시간이 된다 — 이어 붙이는 일은 셋이 다 온 뒤에
  // 해도 똑같다.
  const [customers, projects, sites] = await Promise.all([
    readAllPages(`/api/customers${filter}`),
    readAllPages('/api/projects'),
    readAllPages('/api/sites'),
  ]);
  if (!customers.ok) return customers;
  if (!projects.ok) return projects;
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
      projectId,
    });
    sitesByProject.set(projectId, list);
  }

  const sitesByCustomer = new Map<string, MeasuredSite[]>();
  const projectsByCustomer = new Map<string, { id: string; name: string }[]>();
  for (const project of items(projects.data)) {
    const customerId = textOrNull(project, 'customer_id');
    if (customerId === null) continue;
    const list = sitesByCustomer.get(customerId) ?? [];
    list.push(...(sitesByProject.get(text(project, 'id')) ?? []));
    sitesByCustomer.set(customerId, list);

    const owned = projectsByCustomer.get(customerId) ?? [];
    owned.push({ id: text(project, 'id'), name: text(project, 'name') });
    projectsByCustomer.set(customerId, owned);
  }

  const companies = items(customers.data).map((customer) => {
    const customerId = text(customer, 'id');
    return {
      customerId,
      name: text(customer, 'name'),
      industry: textOrNull(customer, 'industry'),
      address: textOrNull(customer, 'address'),
      // 서버가 값을 안 주면 등록된 것으로 본다. 예전 응답을 읽는 동안 멀쩡한 업체가
      // 목록에서 사라지느니, 재 본 자리가 잠깐 섞이는 편이 낫다.
      isRegistered: customer['is_registered'] !== false,
      sites: sitesByCustomer.get(customerId) ?? [],
      projects: projectsByCustomer.get(customerId) ?? [],
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
  /** 그 주소는 이미 누군가에게 달려 있다. `owner` 는 그 업체명 — 어디 있는지 말해 준다. */
  | { readonly reason: 'DUPLICATE'; readonly owner: string; readonly siteId: string }
  | { readonly reason: 'API'; readonly outcome: ConsoleOutcome<unknown> };

/**
 * 이 주소가 이미 등록돼 있는가.
 *
 * 주소만 넣고 재는 길(`findOrCreateSiteByOrigin`)에는 이 검사가 처음부터 있었는데, 업체
 * 관리에서 손으로 등록하는 길에는 없었다. 그래서 진단이 자동으로 만들어 둔 업체와 사람이
 * 등록한 업체가 **같은 주소로 나란히** 남았다(사용자 지적: 참사랑한의원이 두 번).
 *
 * 엔진에도 중복 거절이 있지만 그것은 프로젝트 안에서만 본다 — 프로젝트가 다르면 통과한다.
 * 조직 전체에서 한 주소는 한 자리여야 이력이 갈라지지 않는다.
 *
 * 못 읽으면 `null` 을 돌려준다. 읽지 못한 것을 "없다" 로 삼아 새로 만들면 중복이 생기고,
 * "있다" 로 삼아 막으면 멀쩡한 등록이 거절된다 — 판단을 부르는 쪽에 넘긴다.
 */
type OriginLookup =
  | { readonly kind: 'FREE' }
  | { readonly kind: 'TAKEN'; readonly company: Company; readonly site: MeasuredSite }
  | { readonly kind: 'UNREADABLE'; readonly failure: CreateCompanyFailure };

async function ownerOfOrigin(origin: string): Promise<OriginLookup> {
  // 재 본 자리까지 포함해 전부 본다. 거래처만 보면 재 본 자리와 겹치는 등록을 못 잡는다.
  const companies = await listCompanies();
  // 못 읽었다. 이것을 "없다" 로 삼아 새로 만들면 중복이 생긴다 — 실패로 돌려보낸다.
  if (!companies.ok) return { kind: 'UNREADABLE', failure: { reason: 'API', outcome: companies } };

  for (const company of companies.data) {
    const site = company.sites.find((one) => one.origin === origin);
    if (site !== undefined) return { kind: 'TAKEN', company, site };
  }
  return { kind: 'FREE' };
}

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
  /**
   * 소재지. 비워도 등록은 된다 — 필수로 만들면 모르는 채로 아무거나 적는다.
   *
   * 재 보기만 하던 자리를 거래처로 올릴 때도 함께 채운다. 그때가 소재지를 처음
   * 아는 시점인 경우가 많다.
   */
  address: string = '',
  /**
   * 거래처로 등록하는 것인가.
   *
   * 기본은 참이다 — 이 함수를 부르는 곳 대부분이 사람이 누른 등록이고, 기본을 뒤집으면
   * 값을 빠뜨린 곳이 목록에서 조용히 사라진다. 주소만 넣고 재려고 자리를 만드는 쪽만
   * 거짓을 보낸다.
   */
  registered: boolean = true,
): Promise<CreateCompanyResult> {
  const companyName = name.trim();
  if (companyName === '') return { ok: false, reason: 'INVALID_NAME' };

  const origin = toOrigin(rawUrl);
  if (origin === null) return { ok: false, reason: 'INVALID_URL' };

  // 만들기 **전에** 본다. 만든 뒤에 되돌리려 하면 절반만 지워진 상태가 남는다.
  const found = await ownerOfOrigin(origin);
  if (found.kind === 'UNREADABLE') return { ok: false, ...found.failure };

  if (found.kind === 'TAKEN') {
    // 이미 거래처면 중복이다.
    if (found.company.isRegistered) {
      return {
        ok: false,
        reason: 'DUPLICATE',
        owner: found.company.name,
        siteId: found.site.siteId,
      };
    }

    // 재 보기만 하던 자리다. **새로 만들지 않고 그 자리를 올린다** — 새로 만들면
    // 그때까지의 진단 이력이 옛 자리에 남아 갈라지고, 화면에는 같은 업체가 둘이 된다.
    // 이 등록 폼이 곧 "거래처로 등록" 이다.
    const promoted = await callConsoleApi(`/api/customers/${found.company.customerId}`, {
      method: 'PATCH',
      // 소재지는 **보낼 때만** 보낸다. 빈 값을 보내면 이미 적어 둔 소재지가 지워진다.
      body: {
        name: companyName,
        is_registered: true,
        ...(address.trim() === '' ? {} : { address: address.trim() }),
      },
    });
    if (!promoted.ok) return { ok: false, reason: 'API', outcome: promoted };
    return { ok: true, customerId: found.company.customerId, siteId: found.site.siteId };
  }

  const customer = await callConsoleApi('/api/customers', {
    method: 'POST',
    body: {
      name: companyName,
      is_registered: registered,
      ...(address.trim() === '' ? {} : { address: address.trim() }),
    },
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

  // 다른 업체에 이미 달린 주소는 여기서도 막는다. 한 주소가 두 업체에 달리면 어느 쪽
  // 이력이 그 사이트의 이력인지 말할 수 없게 된다. 재 보기만 한 자리라도 마찬가지다 —
  // 옮기는 것은 등록 폼이 할 일이고, 여기서 조용히 뺏어 오면 그 자리의 이력이 사라진다.
  const found = await ownerOfOrigin(origin);
  if (found.kind === 'UNREADABLE') return { ok: false, ...found.failure };
  if (found.kind === 'TAKEN') {
    return {
      ok: false,
      reason: 'DUPLICATE',
      owner: found.company.name,
      siteId: found.site.siteId,
    };
  }

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

  const sites = await readAllPages('/api/sites');
  if (!sites.ok) return { ok: false, reason: 'API', outcome: sites };

  const existing = items(sites.data).find((site) => text(site, 'origin') === origin);
  if (existing !== undefined) {
    // 같은 주소를 다시 넣었다. 새로 만들지 않는다 — 그러면 이력이 두 갈래로 쪼개진다.
    return { ok: true, customerId: '', siteId: text(existing, 'id') };
  }

  // 재 보려고 만드는 자리다. 거래처 목록에 넣지 않는다 — 영업 중에 넣어 본 주소가
  // 섞이면 목록이 "우리가 맡은 곳"을 말하지 못한다(사용자 지적). 업체 관리의 등록
  // 폼에 같은 주소를 넣으면 이 자리가 그대로 거래처로 올라간다.
  const label = hostLabel(origin);
  // 소재지는 빈 값이다. 재 보려고 만드는 자리라 아는 것이 주소 하나뿐이고,
  // **모르는 것을 지어내지 않는다.** 거래처로 올릴 때 사람이 채운다.
  return createCompany(label, origin, suffix, '', false);
}

/** `https://www.ondam.co.kr` → `ondam.co.kr`. 사람이 부르는 이름에 가깝게. */
function hostLabel(origin: string): string {
  try {
    return new URL(origin).host.replace(/^www\./, '');
  } catch {
    return origin;
  }
}
