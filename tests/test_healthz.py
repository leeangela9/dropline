from unittest import mock

import pytest
from django.db import OperationalError


@pytest.mark.django_db
def test_healthz_returns_ok_when_database_reachable(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_returns_503_when_database_unreachable(client):
    with mock.patch(
        "dropline.health.connection.cursor",
        side_effect=OperationalError("could not connect to server"),
    ):
        response = client.get("/healthz")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_healthz_needs_no_auth_and_rejects_non_get(client):
    response = client.post("/healthz")

    assert response.status_code == 405
