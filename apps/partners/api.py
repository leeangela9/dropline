"""How the API layer learns which retailer is calling."""

from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.partners.models import Retailer

RETAILER_HEADER = "X-Retailer-Id"


def retailer_from_request(request: Request) -> Retailer:
    """Return the calling retailer. Every view gets its retailer from here and nowhere else.

    Temporary: trusts a plain retailer id in a header. T0.4 replaces the body of this
    function with API key authentication; callers do not change.
    """
    raw = request.headers.get(RETAILER_HEADER, "")
    if not raw.isascii() or not raw.isdigit():
        raise ValidationError(
            {RETAILER_HEADER: ["This header is required and must be an integer."]}
        )
    try:
        return Retailer.objects.get(pk=int(raw))
    except Retailer.DoesNotExist:
        raise ValidationError({RETAILER_HEADER: ["Unknown retailer."]}) from None
