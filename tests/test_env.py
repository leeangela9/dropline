import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from dropline.env import env_bool, env_list, env_required

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("value", [None, "", "   "])
def test_env_required_raises_naming_the_variable(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("DROPLINE_TEST_VAR", raising=False)
    else:
        monkeypatch.setenv("DROPLINE_TEST_VAR", value)

    with pytest.raises(ImproperlyConfigured, match="DROPLINE_TEST_VAR"):
        env_required("DROPLINE_TEST_VAR")


def test_env_required_returns_value(monkeypatch):
    monkeypatch.setenv("DROPLINE_TEST_VAR", "abc")

    assert env_required("DROPLINE_TEST_VAR") == "abc"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", True), ("true", True), ("Yes", True), ("0", False), ("false", False), ("", False)],
)
def test_env_bool_parses(monkeypatch, raw, expected):
    monkeypatch.setenv("DROPLINE_TEST_BOOL", raw)

    assert env_bool("DROPLINE_TEST_BOOL") is expected


def test_env_bool_rejects_garbage(monkeypatch):
    monkeypatch.setenv("DROPLINE_TEST_BOOL", "maybe")

    with pytest.raises(ImproperlyConfigured, match="DROPLINE_TEST_BOOL"):
        env_bool("DROPLINE_TEST_BOOL")


def test_env_list_splits_and_trims(monkeypatch):
    monkeypatch.setenv("DROPLINE_TEST_LIST", " a.com, b.com ,,")

    assert env_list("DROPLINE_TEST_LIST") == ["a.com", "b.com"]


def test_app_refuses_to_start_without_secret_key():
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SECRET_KEY"}

    result = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr
