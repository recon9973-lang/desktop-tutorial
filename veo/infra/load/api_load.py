"""Drive the VEO API under concurrency and measure what comes back.

The application is exercised **in process**, over ``httpx.ASGITransport``. That choice
buys reproducibility — no port, no server to start, no network variance — and it costs
realism, in a way that has to be stated rather than buried:

* There is no socket, no TLS, no HTTP parsing on the wire and no reverse proxy. Absolute
  numbers from this harness are lower bounds on production latency, not predictions.
* Uvicorn's event loop, worker count and backpressure are not exercised at all.
* What *is* real: FastAPI routing and validation, the dependency graph, the scoring
  evaluator, and — for the DB scenarios — SQLAlchemy, the connection pool and PostgreSQL.

Use it as a regression baseline for application-level work ("did this change make the
evaluator four times slower?"), not as a capacity model.

Every target is this process or, for scenarios that need a URL, the loopback fixture site
in :mod:`fixture_site`. Nothing here can reach a third party — see :mod:`safety`.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import httpx
from metrics import Samples

__all__ = ["Scenario", "build_client", "run_scenario", "scenarios"]

RequestFn = Callable[[httpx.AsyncClient], Awaitable[httpx.Response]]


@dataclass(frozen=True, slots=True)
class Scenario:
    """One measured workload.

    ``needs_database`` is separate from a plain skip so the runner can say *why* a
    scenario did not run. A silently missing scenario reads as a passing one.
    """

    name: str
    describe: str
    request: RequestFn
    needs_database: bool = False


# --------------------------------------------------------------------------- #
# Payloads
# --------------------------------------------------------------------------- #


def _evaluate_payload(spec_id: str, version: str, check_ids: list[str]) -> dict[str, Any]:
    """A full, plausible set of check outcomes for the scoring evaluator.

    Statuses are cycled rather than all PASS so the evaluator walks its caps, gates and
    severity coefficients instead of the one cheap path through the middle.
    """
    statuses = ("PASS", "WARNING", "FAIL", "NOT_APPLICABLE", "PASS", "PASS")
    outcomes = []
    for index, check_id in enumerate(check_ids):
        status = statuses[index % len(statuses)]
        applicable = status != "NOT_APPLICABLE"
        outcomes.append(
            {
                "check_id": check_id,
                "status": status,
                "confidence": 0.9 if applicable else 0.0,
                "confidence_level": "HIGH" if applicable else "NONE",
                "affected_weight": 1.0 if status in {"WARNING", "FAIL"} else 0.0,
                "evaluated_weight": 1.0 if applicable else 0.0,
                "evidence_ids": [],
            }
        )
    return {"spec_id": spec_id, "spec_version": version, "outcomes": outcomes}


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #


def scenarios(api_prefix: str) -> list[Scenario]:
    """The workloads, built against whatever specs the repository actually ships.

    The spec id and version are read from the registry rather than written down here, so
    a version bump does not turn this harness into a 404 generator that reports a
    wonderful error rate.
    """
    from veo.scoring.spec import available_specs, load_spec

    catalogue = available_specs()
    if not catalogue:
        raise RuntimeError("no scoring specs are published; the load scenarios need one")

    spec_id = "veo.seo.readiness" if "veo.seo.readiness" in catalogue else next(iter(catalogue))
    version = catalogue[spec_id][-1]
    spec = load_spec(spec_id, version)
    check_ids = [check.id for category in spec.categories for check in category.checks]
    payload = _evaluate_payload(spec_id, version, check_ids)

    async def health(client: httpx.AsyncClient) -> httpx.Response:
        return await client.get(f"{api_prefix}/health")

    async def spec_list(client: httpx.AsyncClient) -> httpx.Response:
        return await client.get(f"{api_prefix}/scoring/specs")

    async def spec_detail(client: httpx.AsyncClient) -> httpx.Response:
        return await client.get(f"{api_prefix}/scoring/specs/{spec_id}/{version}")

    async def evaluate(client: httpx.AsyncClient) -> httpx.Response:
        return await client.post(f"{api_prefix}/scoring/evaluate", json=payload)

    async def project_list(client: httpx.AsyncClient) -> httpx.Response:
        return await client.get(f"{api_prefix}/projects")

    return [
        Scenario(
            name="health",
            describe="the cheapest possible route — the floor this harness can measure",
            request=health,
        ),
        Scenario(
            name="scoring-spec-list",
            describe="loads and serialises every published spec summary",
            request=spec_list,
        ),
        Scenario(
            name="scoring-spec-detail",
            describe=f"full {spec_id}@{version}: {len(check_ids)} checks, caps and gates",
            request=spec_detail,
        ),
        Scenario(
            name="scoring-evaluate",
            describe=f"the evaluator over {len(check_ids)} check outcomes — the product's hot path",
            request=evaluate,
        ),
        Scenario(
            name="projects-list",
            describe="a tenant-scoped read through SQLAlchemy and the connection pool",
            request=project_list,
            needs_database=True,
        ),
    ]


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


@contextmanager
def build_client(*, database_url: str | None) -> Iterator[tuple[httpx.AsyncClient, bool]]:
    """The real application, with a real session factory when a database is offered.

    Authentication is deliberately bypassed with a dependency override rather than by
    minting a token: a load run measuring password hashing tells you about the hash
    parameters, not about the endpoint under test. The principal is constructed by hand,
    exactly as the credential and authz suites do.

    Yields ``(client, database_ready)``.
    """
    import uuid

    from veo.api.app import create_app
    from veo.authz import Principal
    from veo.authz.deps import get_principal
    from veo.contracts.enums import Role
    from veo.db.session import get_db

    app = create_app()
    database_ready = False

    if database_url:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session, sessionmaker
        from veo.db.models import Organization

        engine = create_engine(database_url, future=True, pool_size=20, max_overflow=10)
        factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

        with factory() as probe:
            organization = probe.execute(select(Organization).limit(1)).scalar_one_or_none()
            if organization is None:
                raise RuntimeError(
                    f"{database_url} has no organizations row. The tenant-scoped scenario "
                    "would measure an empty result set. Seed one organization first."
                )
            organization_id = organization.id

        principal = Principal(
            user_id=uuid.uuid4(),
            organization_id=organization_id,
            roles=frozenset({Role.SUPER_ADMIN}),
            session_id=uuid.uuid4().hex,
        )

        def session_dependency() -> Iterator[Session]:
            # A fresh session per request. Sharing one across concurrent requests would
            # measure a lock, not the database.
            opened = factory()
            try:
                yield opened
            finally:
                opened.close()

        app.dependency_overrides[get_db] = session_dependency
        app.dependency_overrides[get_principal] = lambda: principal
        database_ready = True

    # base_url is a .invalid host on purpose: ASGITransport never opens a socket, and if
    # this harness is ever changed to a real transport the requests fail loudly instead
    # of quietly finding somebody's server.
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://veo.load.invalid")
    try:
        yield client, database_ready
    finally:
        if database_ready:
            engine.dispose()


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


async def run_scenario(
    client: httpx.AsyncClient,
    scenario: Scenario,
    *,
    concurrency: int,
    requests: int,
    warmup: int,
) -> Samples:
    """Fire ``requests`` requests through ``concurrency`` workers and time each one.

    Warm-up requests are made and discarded. The first call through a FastAPI route pays
    for response-model construction and, for the DB scenarios, for opening a pooled
    connection; counting that as a latency sample makes every run look like it has a
    long tail it does not have.
    """
    for _ in range(warmup):
        await scenario.request(client)

    samples = Samples(name=scenario.name, concurrency=concurrency)
    counter = {"remaining": requests}
    lock = asyncio.Lock()

    async def worker() -> None:
        while True:
            async with lock:
                if counter["remaining"] <= 0:
                    return
                counter["remaining"] -= 1
            started = time.perf_counter()
            try:
                response = await scenario.request(client)
            except Exception as exc:  # noqa: BLE001 - every failure mode is a data point
                elapsed = (time.perf_counter() - started) * 1000
                samples.record(elapsed, ok=False, label=f"exception:{type(exc).__name__}")
                continue
            elapsed = (time.perf_counter() - started) * 1000
            ok = 200 <= response.status_code < 300
            samples.record(elapsed, ok=ok, label=f"http:{response.status_code}")

    started_at = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    samples.wall_seconds = time.perf_counter() - started_at
    return samples
