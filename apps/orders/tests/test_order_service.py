from unittest import mock

import pytest
from django.db import IntegrityError

from apps.orders.errors import DuplicateOrderError, OrderNotFoundError
from apps.orders.models import Order, OrderLine, OrderStatus
from apps.orders.services import orders
from apps.orders.tests.factories import OrderFactory, OrderLineFactory
from apps.partners.tests.factories import RetailerFactory, SupplierFactory

pytestmark = pytest.mark.django_db

SHIP_TO = {"name": "Jane Doe", "line1": "1 Main St", "city": "Austin", "state": "TX"}
LINES = [
    {"sku": "SKU-1", "quantity": 2, "unit_price_cents": 999},
    {"sku": "SKU-2", "quantity": 1, "unit_price_cents": 0},
]


def create_order(**overrides):
    kwargs = {
        "retailer": RetailerFactory(),
        "supplier": SupplierFactory(),
        "external_po_number": "PO-1",
        "ship_to": SHIP_TO,
        "lines": LINES,
        **overrides,
    }
    return orders.create_order(**kwargs)


def test_create_order_persists_order_and_lines():
    retailer, supplier = RetailerFactory(), SupplierFactory()

    order = create_order(retailer=retailer, supplier=supplier)

    saved = Order.objects.get(pk=order.pk)
    assert saved.retailer == retailer
    assert saved.supplier == supplier
    assert saved.external_po_number == "PO-1"
    assert saved.ship_to == SHIP_TO
    assert saved.status == OrderStatus.RECEIVED
    assert list(saved.lines.values("sku", "quantity", "unit_price_cents", "quantity_shipped")) == [
        {"sku": "SKU-1", "quantity": 2, "unit_price_cents": 999, "quantity_shipped": 0},
        {"sku": "SKU-2", "quantity": 1, "unit_price_cents": 0, "quantity_shipped": 0},
    ]


def test_create_order_rejects_duplicate_po_number_for_same_retailer():
    retailer = RetailerFactory()
    first = create_order(retailer=retailer, external_po_number="PO-1")

    with pytest.raises(DuplicateOrderError):
        create_order(retailer=retailer, external_po_number="PO-1")

    assert list(Order.objects.all()) == [first]
    assert OrderLine.objects.count() == len(LINES)


def test_create_order_allows_same_po_number_for_another_retailer():
    create_order(external_po_number="PO-1")

    create_order(external_po_number="PO-1")

    assert Order.objects.filter(external_po_number="PO-1").count() == 2


def test_create_order_leaves_nothing_behind_when_a_line_fails():
    with (
        mock.patch.object(OrderLine.objects, "bulk_create", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        create_order()

    assert Order.objects.count() == 0
    assert OrderLine.objects.count() == 0


def test_create_order_does_not_report_other_integrity_errors_as_duplicates():
    bad_lines = [LINES[0], {"sku": "SKU-2", "quantity": 0, "unit_price_cents": 100}]

    with pytest.raises(IntegrityError):
        create_order(lines=bad_lines)

    assert Order.objects.count() == 0
    assert OrderLine.objects.count() == 0


def test_get_order_returns_the_order_with_its_lines():
    order = OrderFactory()
    lines = OrderLineFactory.create_batch(2, order=order)

    found = orders.get_order(retailer=order.retailer, order_id=order.pk)

    assert found == order
    assert list(found.lines.all()) == lines


def test_get_order_hides_another_retailers_order():
    order = OrderFactory()

    with pytest.raises(OrderNotFoundError):
        orders.get_order(retailer=RetailerFactory(), order_id=order.pk)


def test_get_order_raises_for_unknown_id():
    with pytest.raises(OrderNotFoundError):
        orders.get_order(retailer=RetailerFactory(), order_id=999_999)


def test_get_order_query_count_does_not_grow_with_lines(django_assert_num_queries):
    order = OrderFactory()
    OrderLineFactory.create_batch(5, order=order)

    with django_assert_num_queries(2):
        found = orders.get_order(retailer=order.retailer, order_id=order.pk)
        assert len(found.lines.all()) == 5
