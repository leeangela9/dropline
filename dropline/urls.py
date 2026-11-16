from django.urls import path

from dropline.health import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
]
