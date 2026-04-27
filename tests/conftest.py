"""Shared fixtures for ACEest API tests (isolated SQLite per test)."""

from __future__ import annotations

import importlib
import os
import sys

import pytest


@pytest.fixture
def aceest_client(tmp_path):
    """Flask test client with a fresh temporary database."""
    db_path = tmp_path / "aceest_test.db"
    os.environ["ACEEST_DB_PATH"] = str(db_path)
    sys.modules.pop("app", None)
    importlib.import_module("app")
    from app import app as flask_app

    return flask_app.test_client()
