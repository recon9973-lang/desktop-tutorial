"""A small website that exists only on this machine, for anything that needs a URL.

VEO's crawler and its SEO checks want a site to look at. The one thing they must never
be pointed at during a load run is a site somebody actually owns, so this serves
``infra/load/fixtures/site`` over loopback and nothing else.

The bind address is hard-coded to 127.0.0.1. It is not configurable, because the only
reason to make it configurable is to expose it.

Run it standalone::

    .venv/bin/python infra/load/fixture_site.py --port 8731

or use :class:`FixtureSite` as a context manager from a scenario.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import threading
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Self

from safety import assert_local_target

__all__ = ["SITE_ROOT", "FixtureSite"]

SITE_ROOT = Path(__file__).resolve().parent / "fixtures" / "site"

#: Loopback only. Not a default — a constant.
BIND_HOST = "127.0.0.1"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler without the per-request line on stderr.

    A load run makes thousands of requests; logging each one would cost more than the
    requests do and would drown the measurement it is supposed to support.
    """

    def log_message(self, format: str, *args: object) -> None:
        return


class FixtureSite(AbstractContextManager["FixtureSite"]):
    """A threaded HTTP server over the fixture directory, bound to loopback."""

    def __init__(self, *, port: int = 0, root: Path | None = None) -> None:
        self._root = root or SITE_ROOT
        if not self._root.is_dir():
            raise FileNotFoundError(f"fixture site directory is missing: {self._root}")
        handler = functools.partial(_QuietHandler, directory=str(self._root))
        # Port 0 lets the OS pick a free one, so two runs never collide.
        self._server = http.server.ThreadingHTTPServer((BIND_HOST, port), handler)
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[0], self._server.server_address[1]
        return assert_local_target(f"http://{host}:{port}")

    def start(self) -> FixtureSite:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local load-test fixture site.")
    parser.add_argument("--port", type=int, default=8731)
    args = parser.parse_args()
    with FixtureSite(port=args.port) as site:
        print(f"fixture site on {site.base_url} (Ctrl-C to stop)")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
