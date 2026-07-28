"""Managing the people inside one organization.

Adding a colleague, giving them a role, taking it away, and letting them set and change
their own password. Everything here is organization-scoped: an administrator of one
agency can never see, name or alter a person in another.

The package deliberately does not re-export its router — see the note in
``veo.auth.__init__`` for what that costs.
"""
