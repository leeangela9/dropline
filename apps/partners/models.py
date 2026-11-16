from django.db import models


class Retailer(models.Model):
    """A trading partner that places orders and owns the data it sends us."""

    name = models.CharField(max_length=200)
    # Set by API key auth (T0.4). Only the hash is stored, never the raw key.
    api_key_hash = models.CharField(max_length=128, blank=True)
    webhook_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """A trading partner that fulfills orders routed to it."""

    name = models.CharField(max_length=200)
    sla_hours = models.PositiveIntegerField(help_text="Hours allowed to acknowledge an order.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
