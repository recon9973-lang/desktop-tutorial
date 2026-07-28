"""VEO asynchronous job runtime.

Phase 0 delivers the runtime skeleton only: queues, state machine, idempotency,
progress, cooperative cancellation, partial-success accounting and safe error mapping.
The collectors and analysers that produce real findings arrive in later phases; the
task stubs here raise :class:`NotImplementedError` rather than inventing results.
"""

__version__ = "0.1.0"
