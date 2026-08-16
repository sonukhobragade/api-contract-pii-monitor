"""
Shared fixtures.

The database settings are supplied here because Config validates that HOST,
PORT, USERNAME, PASSWORD and DB_NAME are all present before it will build a
connection string. That validation exists so a run cannot silently connect
with an empty password on a trust-auth server, but it means unit tests that
mock psycopg2.connect still have to provide a complete configuration: the
error is raised before any connection is attempted.
"""

import pytest

_TEST_DB_ENV = {
    "HOST": "localhost",
    "PORT": "5432",
    "USERNAME": "test_user",
    "PASSWORD": "test_password",
    "DB_NAME": "test_db",
}


@pytest.fixture(autouse=True)
def _database_env(monkeypatch):
    """Give every test a complete, obviously-fake database configuration."""
    for key, value in _TEST_DB_ENV.items():
        monkeypatch.setenv(key, value)
    # The module-level singleton is built at import time from whatever the
    # environment held then, so refresh it to match.
    import core.config as config_module

    monkeypatch.setattr(config_module.config, "HOST", _TEST_DB_ENV["HOST"], raising=False)
    monkeypatch.setattr(config_module.config, "PORT", _TEST_DB_ENV["PORT"], raising=False)
    monkeypatch.setattr(config_module.config, "USERNAME", _TEST_DB_ENV["USERNAME"], raising=False)
    monkeypatch.setattr(config_module.config, "PASSWORD", _TEST_DB_ENV["PASSWORD"], raising=False)
    monkeypatch.setattr(config_module.config, "DB_NAME", _TEST_DB_ENV["DB_NAME"], raising=False)
    yield
