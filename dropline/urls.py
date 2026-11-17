from django.contrib import admin
from django.urls import include, path

from dropline.health import healthz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.orders.urls")),
    path("healthz", healthz, name="healthz"),
]
