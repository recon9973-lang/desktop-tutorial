"""Adapters for external data providers.

One subpackage per provider. An adapter's job is to turn a provider's answer into VEO's
vocabulary **without losing what the provider actually said**, and to turn a provider's
silence into a stated ``UNKNOWN`` rather than into a plausible number.

This ``__init__`` is a package marker only. See ``keywords/INTEGRATION_REQUEST.md`` —
creating it was unavoidable to make ``providers.naver`` importable, and the file is
deliberately empty of logic so that ownership of ``providers/`` outside ``naver/``
remains open.
"""

from __future__ import annotations
