from django.contrib import admin

from apps.orders.models import Order, OrderLine


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["external_po_number", "retailer", "supplier", "status", "created_at"]
    list_filter = ["status", "supplier"]
    list_select_related = ["retailer", "supplier"]
    search_fields = ["external_po_number"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [OrderLineInline]


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ["order", "sku", "quantity", "unit_price_cents", "quantity_shipped"]
    list_select_related = ["order__retailer"]
    search_fields = ["sku", "order__external_po_number"]
