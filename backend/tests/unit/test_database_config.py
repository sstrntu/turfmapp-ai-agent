"""
Tests for database connection helper utilities.
"""

from __future__ import annotations

from app.database import _ensure_sslmode


def test_ensure_sslmode_returns_original_for_empty_url():
    """Empty URLs should pass through unchanged."""
    assert _ensure_sslmode("") == ""
    assert _ensure_sslmode(None) is None


def test_ensure_sslmode_disables_ssl_for_local_urls():
    """Local Postgres connections disable SSL by default."""
    url = "postgresql://user:pass@localhost:5432/db"
    assert _ensure_sslmode(url) == f"{url}?sslmode=disable"

    url_with_query = "postgresql://user:pass@127.0.0.1:5432/db?connect_timeout=10"
    assert (
        _ensure_sslmode(url_with_query)
        == f"{url_with_query}&sslmode=disable"
    )


def test_ensure_sslmode_enables_ssl_for_remote_urls():
    """Remote databases default to requiring SSL."""
    remote_url = "postgresql://user:pass@supabase.aws.com:5432/db"
    assert _ensure_sslmode(remote_url) == f"{remote_url}?sslmode=require"

    remote_with_params = (
        "postgresql://user:pass@supabase.aws.com:5432/db?pool=5"
    )
    assert (
        _ensure_sslmode(remote_with_params)
        == f"{remote_with_params}&sslmode=require"
    )


def test_ensure_sslmode_respects_existing_setting():
    """Do not override explicit sslmode parameters."""
    existing = "postgresql://user:pass@db.com:5432/db?sslmode=require"
    assert _ensure_sslmode(existing) == existing
