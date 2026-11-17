import factory
from factory.django import DjangoModelFactory

from apps.orders.models import Order, OrderLine
from apps.partners.tests.factories import RetailerFactory, SupplierFactory


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    retailer = factory.SubFactory(RetailerFactory)
    supplier = factory.SubFactory(SupplierFactory)
    external_po_number = factory.Sequence(lambda n: f"PO-{n:05d}")
    ship_to = factory.LazyFunction(
        lambda: {"name": "Jane Doe", "line1": "1 Main St", "city": "Austin", "state": "TX"}
    )


class OrderLineFactory(DjangoModelFactory):
    class Meta:
        model = OrderLine

    order = factory.SubFactory(OrderFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    quantity = 1
    unit_price_cents = 1000
