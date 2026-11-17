import pytest

from apps.orders.models import Order, OrderLine, OrderStatus
from apps.orders.tests.factories import OrderFactory, OrderLineFactory
from apps.partners.tests.factories import RetailerFactory, SupplierFactory

pytestmark = pytest.mark.django_db

URL = "/api/orders"


def as_retailer(retailer):
    """Request headers identifying the caller. T0.4 swaps this for an API key."""
    return {"X-Retailer-Id": str(retailer.pk)}


def payload(supplier, **overrides):
    body = {
        "supplier_id": supplier.pk,
        "external_po_number": "PO-1",
        "ship_to": {"name": "Jane Doe", "line1": "1 Main St", "city": "Austin", "state": "TX"},
        "lines": [
            {"sku": "SKU-1", "quantity": 2, "unit_price_cents": 999},
            {"sku": "SKU-2", "quantity": 1, "unit_price_cents": 0},
        ],
    }
    body.update(overrides)
    return body


def line(**overrides):
    return {"sku": "SKU-1", "quantity": 1, "unit_price_cents": 100, **overrides}


# --- POST /api/orders ---------------------------------------------------------------------


def test_create_order_returns_201_and_persists_order_with_lines(api_client):
    retailer, supplier = RetailerFactory(), SupplierFactory()

    response = api_client.post(URL, payload(supplier), headers=as_retailer(retailer))

    assert response.status_code == 201
    order = Order.objects.get()
    assert order.retailer == retailer
    assert order.status == OrderStatus.RECEIVED
    first, second = order.lines.all()
    assert response.json() == {
        "id": order.pk,
        "supplier_id": supplier.pk,
        "external_po_number": "PO-1",
        "status": "received",
        "ship_to": {"name": "Jane Doe", "line1": "1 Main St", "city": "Austin", "state": "TX"},
        "lines": [
            {
                "id": first.pk,
                "sku": "SKU-1",
                "quantity": 2,
                "unit_price_cents": 999,
                "quantity_shipped": 0,
            },
            {
                "id": second.pk,
                "sku": "SKU-2",
                "quantity": 1,
                "unit_price_cents": 0,
                "quantity_shipped": 0,
            },
        ],
        "created_at": response.json()["created_at"],
        "updated_at": response.json()["updated_at"],
    }


def test_create_order_ignores_status_and_retailer_in_the_body(api_client):
    retailer, other, supplier = RetailerFactory(), RetailerFactory(), SupplierFactory()
    body = payload(supplier, status="shipped", retailer_id=other.pk)

    response = api_client.post(URL, body, headers=as_retailer(retailer))

    assert response.status_code == 201
    order = Order.objects.get()
    assert order.retailer == retailer
    assert order.status == OrderStatus.RECEIVED


def test_create_order_stores_whole_number_floats_as_integers(api_client):
    retailer, supplier = RetailerFactory(), SupplierFactory()
    body = payload(supplier, lines=[line(quantity=2.0, unit_price_cents=100.0)])

    response = api_client.post(URL, body, headers=as_retailer(retailer))

    assert response.status_code == 201
    assert response.json()["lines"][0]["quantity"] == 2
    assert response.json()["lines"][0]["unit_price_cents"] == 100
    saved = OrderLine.objects.get()
    assert (saved.quantity, saved.unit_price_cents) == (2, 100)


@pytest.mark.parametrize(
    ("overrides", "error_field"),
    [
        ({"lines": None}, "lines"),
        ({"lines": []}, "lines"),
        ({"lines": [line(quantity=0)]}, "lines"),
        ({"lines": [line(quantity=2_147_483_648)]}, "lines"),
        ({"lines": [line(unit_price_cents=-1)]}, "lines"),
        ({"lines": [line(unit_price_cents=9.99)]}, "lines"),
        ({"lines": [line(unit_price_cents="free")]}, "lines"),
        ({"lines": [line(sku="")]}, "lines"),
        ({"lines": [line(), {"sku": "SKU-2"}]}, "lines"),
        ({"external_po_number": None}, "external_po_number"),
        ({"external_po_number": ""}, "external_po_number"),
        ({"external_po_number": "x" * 65}, "external_po_number"),
        ({"ship_to": None}, "ship_to"),
        ({"ship_to": {}}, "ship_to"),
        ({"ship_to": "1 Main St"}, "ship_to"),
        ({"supplier_id": None}, "supplier_id"),
        ({"supplier_id": 999_999}, "supplier_id"),
        ({"supplier_id": "widget-co"}, "supplier_id"),
    ],
    ids=[
        "lines_missing",
        "lines_empty",
        "quantity_zero",
        "quantity_too_large",
        "price_negative",
        "price_float",
        "price_not_a_number",
        "sku_blank",
        "second_line_incomplete",
        "po_missing",
        "po_blank",
        "po_too_long",
        "ship_to_missing",
        "ship_to_empty",
        "ship_to_not_an_object",
        "supplier_missing",
        "supplier_unknown",
        "supplier_not_an_id",
    ],
)
def test_create_order_rejects_invalid_input_with_field_errors(api_client, overrides, error_field):
    retailer, supplier = RetailerFactory(), SupplierFactory()
    body = payload(supplier, **overrides)
    # None marks a field to leave out of the request entirely.
    body = {key: value for key, value in body.items() if value is not None}

    response = api_client.post(URL, body, headers=as_retailer(retailer))

    assert response.status_code == 400
    assert list(response.json()) == [error_field]
    assert Order.objects.count() == 0


def test_create_order_reports_which_line_and_field_is_invalid(api_client):
    retailer, supplier = RetailerFactory(), SupplierFactory()
    body = payload(supplier, lines=[line(), line(quantity=0)])

    response = api_client.post(URL, body, headers=as_retailer(retailer))

    assert response.status_code == 400
    # Line errors are keyed by the line's position in the request.
    assert response.json() == {
        "lines": {"1": {"quantity": ["Ensure this value is greater than or equal to 1."]}}
    }


def test_create_order_with_duplicate_po_number_returns_409(api_client):
    retailer, supplier = RetailerFactory(), SupplierFactory()
    existing = OrderFactory(retailer=retailer, external_po_number="PO-1")

    response = api_client.post(
        URL, payload(supplier, external_po_number="PO-1"), headers=as_retailer(retailer)
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "An order with this external_po_number already exists.",
        "code": "duplicate_order",
    }
    assert list(Order.objects.all()) == [existing]
    assert OrderLine.objects.count() == 0


def test_create_order_allows_a_po_number_another_retailer_already_used(api_client):
    retailer, supplier = RetailerFactory(), SupplierFactory()
    OrderFactory(external_po_number="PO-1")

    response = api_client.post(
        URL, payload(supplier, external_po_number="PO-1"), headers=as_retailer(retailer)
    )

    assert response.status_code == 201


# --- GET /api/orders/{id} -----------------------------------------------------------------


def test_get_order_returns_200_with_lines(api_client):
    order = OrderFactory()
    lines = OrderLineFactory.create_batch(2, order=order)

    response = api_client.get(f"{URL}/{order.pk}", headers=as_retailer(order.retailer))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == order.pk
    assert body["external_po_number"] == order.external_po_number
    assert body["status"] == "received"
    assert [item["id"] for item in body["lines"]] == [item.pk for item in lines]


@pytest.mark.parametrize(
    "order_id", ["999999", "abc", "99999999999999999999999999"], ids=["unknown", "text", "huge"]
)
def test_get_order_with_unknown_id_returns_404(api_client, order_id):
    response = api_client.get(f"{URL}/{order_id}", headers=as_retailer(RetailerFactory()))

    assert response.status_code == 404


def test_get_order_owned_by_another_retailer_returns_404(api_client):
    order = OrderFactory()

    response = api_client.get(f"{URL}/{order.pk}", headers=as_retailer(RetailerFactory()))

    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found.", "code": "order_not_found"}


def test_get_order_query_count_does_not_grow_with_lines(api_client, django_assert_num_queries):
    small, large = OrderFactory(), OrderFactory()
    OrderLineFactory(order=small)
    OrderLineFactory.create_batch(8, order=large)

    # Retailer lookup, order, lines.
    for order in (small, large):
        with django_assert_num_queries(3):
            response = api_client.get(f"{URL}/{order.pk}", headers=as_retailer(order.retailer))
        assert len(response.json()["lines"]) == order.lines.count()


# --- Temporary X-Retailer-Id header (replaced by API keys in T0.4) -------------------------


@pytest.mark.parametrize("headers", [{}, {"X-Retailer-Id": "abc"}, {"X-Retailer-Id": "999999"}])
def test_requests_without_a_known_retailer_are_rejected(api_client, headers):
    order = OrderFactory()

    get_response = api_client.get(f"{URL}/{order.pk}", headers=headers)
    post_response = api_client.post(URL, payload(order.supplier), headers=headers)

    assert get_response.status_code == 400
    assert post_response.status_code == 400
    assert list(post_response.json()) == ["X-Retailer-Id"]
    assert Order.objects.count() == 1
