"""Organizations, plus the plumbing the Phase 1 resource routers share.

``/organizations`` is read-only: a caller reads the one organization they authenticated
into, and there is no endpoint that lists them all.

The modules :mod:`veo.organizations.http`, :mod:`veo.organizations.fields`,
:mod:`veo.organizations.errors` and :mod:`veo.organizations.audit` are shared by the
customers, projects and sites packages as well. They live here because an organization is
the root of that dependency chain — customers, projects and sites import from this
package and nothing imports back, so there is no cycle to trip over.
"""
