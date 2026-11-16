from django.db import models

from apps.partners.models import Retailer, Supplier


class OrderStatus(models.TextChoices):
    RECEIVED = "received"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    INVOICED = "invoiced"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class Order(models.Model):
    """A retailer's purchase order, routed to one supplier."""

    retailer = models.ForeignKey(Retailer, on_delete=models.PROTECT, related_name="orders")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="orders")
    external_po_number = models.CharField(max_length=64)
    # Change status only through order_state.transition() once T1.2 lands.
    status = models.CharField(
        max_length=32, choices=OrderStatus.choices, default=OrderStatus.RECEIVED
    )
    ship_to = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["retailer", "external_po_number"],
                name="orders_order_unique_retailer_po",
            ),
        ]

    def __str__(self):
        return f"{self.external_po_number} ({self.retailer})"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    # Plain string until T1.4 replaces it with a foreign key to Product.
    sku = models.CharField(max_length=64)
    quantity = models.IntegerField()
    unit_price_cents = models.IntegerField()
    quantity_shipped = models.IntegerField(default=0)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="orders_orderline_quantity_gte_1",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price_cents__gte=0),
                name="orders_orderline_unit_price_cents_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_shipped__gte=0),
                name="orders_orderline_quantity_shipped_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.sku} x {self.quantity}"
