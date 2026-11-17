"""Database helpers shared across apps."""

from django.db import IntegrityError


def violated_constraint(exc: IntegrityError) -> str | None:
    """Name of the constraint Postgres reported for this error, if it reported one.

    Lets a service turn one specific constraint violation into a domain error and
    re-raise every other IntegrityError untouched.
    """
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)
