import factory
from factory.django import DjangoModelFactory

from apps.partners.models import Retailer, Supplier


class RetailerFactory(DjangoModelFactory):
    class Meta:
        model = Retailer

    name = factory.Sequence(lambda n: f"Retailer {n}")


class SupplierFactory(DjangoModelFactory):
    class Meta:
        model = Supplier

    name = factory.Sequence(lambda n: f"Supplier {n}")
    sla_hours = 48
