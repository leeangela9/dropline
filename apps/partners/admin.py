from django.contrib import admin

from apps.partners.models import Retailer, Supplier


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ["name", "webhook_url"]
    search_fields = ["name"]
    # Written by API key auth, never typed in by hand.
    readonly_fields = ["api_key_hash"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "sla_hours"]
    search_fields = ["name"]
