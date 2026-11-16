import pytest
from django.db import IntegrityError

from apps.orders.models import Order, OrderLine, OrderStatus
from apps.partners.models import Retailer, Supplier

SHIP_TO = {"name": "Jane Doe", "line1": "1 Main St", "city": "Austin", "state": "TX"}


@pytest.fixture
def retailer():
    return Retailer.objects.create(name="Acme Retail")


@pytest.fixture
def supplier():
    return Supplier.objects.create(name="Widget Co", sla_hours=48)


def make_order(retailer, supplier, po="PO-1"):
    return Order.objects.create(
        retailer=retailer, supplier=supplier, external_po_number=po, ship_to=SHIP_TO
    )


@pytest.mark.django_db
def test_new_order_defaults_to_received(retailer, supplier):
    order = make_order(retailer, supplier)

    order.refresh_from_db()
    assert order.status == OrderStatus.RECEIVED


@pytest.mark.django_db
def test_duplicate_po_number_for_same_retailer_is_rejected(retailer, supplier):
    make_order(retailer, supplier, po="PO-1")

    with pytest.raises(IntegrityError):
        make_order(retailer, supplier, po="PO-1")


@pytest.mark.django_db
def test_same_po_number_under_different_retailer_is_allowed(retailer, supplier):
    other = Retailer.objects.create(name="Other Retail")
    make_order(retailer, supplier, po="PO-1")

    make_order(other, supplier, po="PO-1")

    assert Order.objects.filter(external_po_number="PO-1").count() == 2


@pytest.mark.django_db
def test_order_line_quantity_shipped_defaults_to_zero(retailer, supplier):
    order = make_order(retailer, supplier)

    line = OrderLine.objects.create(order=order, sku="SKU-1", quantity=2, unit_price_cents=999)

    line.refresh_from_db()
    assert line.quantity_shipped == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_values",
    [
        {"quantity": 0},
        {"unit_price_cents": -1},
        {"quantity_shipped": -1},
    ],
    ids=["quantity_zero", "negative_price", "negative_quantity_shipped"],
)
def test_order_line_check_constraints_reject_bad_values(retailer, supplier, field_values):
    order = make_order(retailer, supplier)
    values = {"sku": "SKU-1", "quantity": 1, "unit_price_cents": 100, **field_values}

    with pytest.raises(IntegrityError):
        OrderLine.objects.create(order=order, **values)
