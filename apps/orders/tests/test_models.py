import pytest
from django.db import IntegrityError

from apps.orders.models import Order, OrderLine, OrderStatus
from apps.orders.tests.factories import OrderFactory
from apps.partners.tests.factories import RetailerFactory

pytestmark = pytest.mark.django_db


def test_new_order_defaults_to_received():
    order = OrderFactory()

    order.refresh_from_db()
    assert order.status == OrderStatus.RECEIVED


def test_duplicate_po_number_for_same_retailer_is_rejected():
    retailer = RetailerFactory()
    OrderFactory(retailer=retailer, external_po_number="PO-1")

    with pytest.raises(IntegrityError):
        OrderFactory(retailer=retailer, external_po_number="PO-1")


def test_same_po_number_under_different_retailer_is_allowed():
    OrderFactory(external_po_number="PO-1")

    OrderFactory(external_po_number="PO-1")

    assert Order.objects.filter(external_po_number="PO-1").count() == 2


def test_order_line_quantity_shipped_defaults_to_zero():
    order = OrderFactory()

    line = OrderLine.objects.create(order=order, sku="SKU-1", quantity=2, unit_price_cents=999)

    line.refresh_from_db()
    assert line.quantity_shipped == 0


@pytest.mark.parametrize(
    "field_values",
    [
        {"quantity": 0},
        {"unit_price_cents": -1},
        {"quantity_shipped": -1},
    ],
    ids=["quantity_zero", "negative_price", "negative_quantity_shipped"],
)
def test_order_line_check_constraints_reject_bad_values(field_values):
    order = OrderFactory()
    values = {"sku": "SKU-1", "quantity": 1, "unit_price_cents": 100, **field_values}

    with pytest.raises(IntegrityError):
        OrderLine.objects.create(order=order, **values)
