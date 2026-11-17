"""Request and response shapes for orders. Validation only: nothing here writes to the database."""

from rest_framework import serializers

from apps.orders.models import Order, OrderLine
from apps.partners.models import Supplier

# Largest value a Postgres integer column holds. Without the cap, bigger input is a 500.
MAX_INTEGER = 2_147_483_647


class OrderLineInputSerializer(serializers.Serializer):
    # IntegerField accepts a whole-number float such as 100.0 and stores 100. A value
    # with a fraction, such as 9.99, is a 400.
    sku = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_INTEGER)
    unit_price_cents = serializers.IntegerField(min_value=0, max_value=MAX_INTEGER)


class OrderCreateSerializer(serializers.Serializer):
    """Input for creating an order. The retailer is never part of the body."""

    supplier_id = serializers.PrimaryKeyRelatedField(
        source="supplier", queryset=Supplier.objects.all()
    )
    external_po_number = serializers.CharField(max_length=64)
    ship_to = serializers.DictField(allow_empty=False)
    lines = OrderLineInputSerializer(many=True, allow_empty=False)


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ["id", "sku", "quantity", "unit_price_cents", "quantity_shipped"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Output for an order. Expects `lines` to be prefetched when serializing many."""

    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "supplier_id",
            "external_po_number",
            "status",
            "ship_to",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
