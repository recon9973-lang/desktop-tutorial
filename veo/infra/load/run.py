"""Entry point for the VEO load harness.

    .venv/bin/python infra/load/run.py --requests 500 --concurrency 16

Nothing here can reach a host that is not this machine. See :mod:`safety`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

# The harness lives outside the packages it drives, so put them on the path before any
# veo import. Same three entries pytest.ini uses, kept in step with it deliberately.
for entry in (
    str(HERE),
    str(REPO_ROOT / "apps" / "api" / "src"),
    str(REPO_ROOT / "apps" / "worker" / "src"),
):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from api_load import build_client, run_scenario, scenarios
from queue_backlog import (
    BrokerUnavailable,
    broker_url,
    run_backlog_experiment,
)


def _print(text: str = "") -> None:
    print(text)


def _run_api(args: argparse.Namespace) -> int:
    from veo.core.settings import get_settings

    api_prefix = get_settings().api_prefix
    database_url = args.database_url or os.environ.get("VEO_LOAD_DATABASE_URL") or None

    _print("=" * 78)
    _print("VEO API load — in-process ASGI. Lower bound on latency, not a capacity model.")
    _print("=" * 78)

    failures = 0
    with build_client(database_url=database_url) as (client, database_ready):
        chosen = scenarios(api_prefix)
        if args.scenario:
            chosen = [s for s in chosen if s.name in args.scenario]
            if not chosen:
                _print(f"no scenario matched {args.scenario}")
                return 2

        async def drive() -> None:
            nonlocal failures
            for scenario in chosen:
                _print()
                _print(f"--- {scenario.name} ---")
                _print(f"  what         : {scenario.describe}")
                if scenario.needs_database and not database_ready:
                    _print(
                        "  SKIPPED      : no database. Set VEO_LOAD_DATABASE_URL (or pass\n"
                        "                 --database-url) to a migrated VEO database with at\n"
                        "                 least one organizations row. This scenario is the\n"
                        "                 only one that touches SQLAlchemy and the connection\n"
                        "                 pool, so skipping it leaves those unmeasured."
                    )
                    continue
                samples = await run_scenario(
                    client,
                    scenario,
                    concurrency=args.concurrency,
                    requests=args.requests,
                    warmup=args.warmup,
                )
                report = samples.report()
                _print(report.render())
                if report.failed:
                    failures += report.failed

        asyncio.run(drive())

    _print()
    if failures:
        _print(f"{failures} request(s) failed. A load run with errors is not a baseline.")
        return 1
    return 0


def _run_queue(args: argparse.Namespace) -> int:
    _print()
    _print("=" * 78)
    _print("VEO queue backlog and recovery")
    _print("=" * 78)
    try:
        result = run_backlog_experiment(
            produce=args.produce,
            drain_timeout_seconds=args.drain_timeout,
        )
    except BrokerUnavailable as exc:
        _print()
        _print("  NOT RUN — no broker.")
        _print()
        for line in str(exc).splitlines():
            _print(f"  {line}")
        _print()
        _print("  Queue backlog recovery is UNVERIFIED in this environment.")
        return 0
    _print()
    _print(result.render())
    return 0 if result.drained else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=400, help="requests per scenario")
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--warmup", type=int, default=10, help="discarded requests per scenario")
    parser.add_argument(
        "--scenario", action="append", help="run only this scenario (repeatable)"
    )
    parser.add_argument("--database-url", help="a migrated VEO database for the DB scenario")
    parser.add_argument("--produce", type=int, default=2_000, help="queue: messages to flood")
    parser.add_argument("--drain-timeout", type=float, default=120.0)
    parser.add_argument(
        "--only", choices=("api", "queue"), help="run only one half of the harness"
    )
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")

    status = 0
    if args.only in (None, "api"):
        status |= _run_api(args)
    if args.only in (None, "queue"):
        status |= _run_queue(args)

    if broker_url() is None and args.only != "api":
        _print()
        _print(
            "Reminder: without a broker, this run measured the API only. Redis-specific\n"
            "behaviour — visibility timeouts, redelivery after a worker dies, prefetch\n"
            "across worker processes — remains unverified."
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
