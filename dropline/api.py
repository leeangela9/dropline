"""API-wide plumbing shared by every app's views."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from dropline.errors import ConflictError, DomainError, NotFoundError

# An error category missing from this table is a bug, so it falls through to a 500.
_STATUS_BY_CATEGORY = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
)


def exception_handler(exc, context):
    """Map domain errors to HTTP; everything else keeps DRF's default handling."""
    if isinstance(exc, DomainError):
        for category, status_code in _STATUS_BY_CATEGORY:
            if isinstance(exc, category):
                set_rollback()
                return Response({"detail": exc.message, "code": exc.code}, status=status_code)
        return None
    return drf_exception_handler(exc, context)
