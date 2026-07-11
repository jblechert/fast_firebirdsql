"""Module surface tests (no database required).

Replaces the legacy test_imports.py / test_rename.py scripts.
"""

import pytest

import fast_firebirdsql

pytestmark = pytest.mark.nodb


def test_version_exposed():
    assert fast_firebirdsql.__version__
    parts = fast_firebirdsql.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_api_surface():
    for name in (
        "connect",
        "FirebirdConnection",
        "FirebirdCursor",
        "get_performance_stats",
        "clear_performance_stats",
        "get_type_conversion_cache_stats",
        "clear_type_conversion_cache",
        "get_query_optimization_stats",
        "clear_query_optimization_cache",
    ):
        assert hasattr(fast_firebirdsql, name), f"missing symbol: {name}"


def test_cursor_methods_exist():
    for name in (
        "execute",
        "executemany",
        "fetchall",
        "fetchone",
        "fetchmany",
        "close",
    ):
        assert hasattr(fast_firebirdsql.FirebirdCursor, name), f"missing method: {name}"
