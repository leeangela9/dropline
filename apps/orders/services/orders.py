"""Creating and reading orders. Status changes do not belong here (see T1.2)."""

from collections.abc import Sequence
from typing import Any, TypedDict

from django.db import IntegrityError, transaction

from apps.orders.errors import DuplicateOrderError, OrderNotFoundError
from apps.orders.models import ORDER_UNIQUE_PO_CONSTRAINT, Order, OrderLine
from apps.partners.models import Retailer, Supplier
from dropline.db import violated_constraint


class LineInput(TypedDict):
    sku: str
    quantity: int
    unit_price_cents: int


def create_order(
    *,
    retailer: Retailer,
    supplier: Supplier,
    external_po_number: str,
    ship_to: dict[str, Any],
    lines: Sequence[LineInput],
) -> Order:
    """Create an order and its lines together, or nothing at all.

    Raises DuplicateOrderError if the retailer already has an order with this PO number.
    The database constraint decides that, so two concurrent requests cannot both succeed.
    """
    try:
        with transaction.atomic():
            order = Order.objects.create(
                retailer=retailer,
                supplier=supplier,
                external_po_number=external_po_number,
                ship_to=ship_to,
            )
            OrderLine.objects.bulk_create(
                OrderLine(
                    order=order,
                    sku=line["sku"],
                    quantity=line["quantity"],
                    unit_price_cents=line["unit_price_cents"],
                )
                for line in lines
            )
    # Caught outside the atomic block: the transaction is unusable until it has rolled back.
    except IntegrityError as exc:
        if violated_constraint(exc) == ORDER_UNIQUE_PO_CONSTRAINT:
            raise DuplicateOrderError() from exc
        raise
    return order


def get_order(*, retailer: Retailer, order_id: int) -> Order:
    """Return the retailer's order with its lines loaded.

    Another retailer's order raises OrderNotFoundError, the same as an id that does not exist.
    """
    try:
        return Order.objects.filter(retailer=retailer).prefetch_related("lines").get(pk=order_id)
    except Order.DoesNotExist:
        raise OrderNotFoundError() from None
