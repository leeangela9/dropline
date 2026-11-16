import pytest
from django.urls import reverse

from apps.orders.models import Order, OrderLine
from apps.partners.models import Retailer, Supplier


@pytest.fixture
def order_with_line():
    retailer = Retailer.objects.create(name="Acme Retail")
    supplier = Supplier.objects.create(name="Widget Co", sla_hours=48)
    order = Order.objects.create(
        retailer=retailer, supplier=supplier, external_po_number="PO-1", ship_to={}
    )
    OrderLine.objects.create(order=order, sku="SKU-1", quantity=1, unit_price_cents=100)
    return order


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "admin:partners_retailer_changelist",
        "admin:partners_supplier_changelist",
        "admin:orders_order_changelist",
        "admin:orders_orderline_changelist",
    ],
)
def test_admin_changelist_loads(admin_client, order_with_line, url_name):
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_order_change_page_shows_lines_inline(admin_client, order_with_line):
    response = admin_client.get(reverse("admin:orders_order_change", args=[order_with_line.pk]))

    assert response.status_code == 200
    assert b"SKU-1" in response.content
