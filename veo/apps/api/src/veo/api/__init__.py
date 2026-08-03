"""HTTP surface of VEO.

``app``/``create_app`` are loaded lazily (PEP 562): an eager
``from veo.api.app import ...`` here would make ``import veo.api.deps`` pull in
``veo.api.app`` — which imports feature routers (e.g. ``veo.public.router``)
that themselves import ``veo.api.deps`` — an import cycle whenever a router
module is imported before ``veo.api``.
"""

import importlib
from typing import Any

__all__ = ["app", "create_app"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        # importlib, not `from veo.api import app`: the submodule shares its name
        # with the attribute, so the from-import would re-enter this hook forever.
        module = importlib.import_module("veo.api.app")
        for public in __all__:
            # Rebind after the import, which set `veo.api.app` to the submodule —
            # the eager re-export shadowed it with the FastAPI instance, and
            # callers of `veo.api.app` must keep seeing that.
            globals()[public] = getattr(module, public)
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
