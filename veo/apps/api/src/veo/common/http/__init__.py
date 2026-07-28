"""Shared HTTP helpers used by every outbound provider client."""

from veo.common.http.capped_read import read_capped

__all__ = ["read_capped"]
