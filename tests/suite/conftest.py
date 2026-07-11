"""Fixtures for the fast_firebirdsql pytest suite.

The suite needs a reachable Firebird server (configured via .env /
environment, see db_config.py). Tests are skipped if the server is not
reachable.

Write tests (INSERT/UPDATE/transactions) create and drop their own table
TEST_FAST_FBSQL. They only run when FIREBIRD_ALLOW_WRITE_TESTS=1 is set,
so that a plain pytest run never writes to the configured database.
"""

import os
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from db_config import DB_CONFIG

import fast_firebirdsql

TEST_TABLE = "TEST_FAST_FBSQL"


def _server_reachable() -> bool:
    try:
        with socket.create_connection((DB_CONFIG["host"], DB_CONFIG["port"]), timeout=3):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    if not _server_reachable():
        skip = pytest.mark.skip(reason=f"Firebird server {DB_CONFIG['host']}:{DB_CONFIG['port']} not reachable")
        for item in items:
            item.add_marker(skip)


requires_write = pytest.mark.skipif(
    os.environ.get("FIREBIRD_ALLOW_WRITE_TESTS") != "1",
    reason="write tests disabled (set FIREBIRD_ALLOW_WRITE_TESTS=1 to enable)",
)


@pytest.fixture
def conn():
    connection = fast_firebirdsql.connect(**DB_CONFIG)
    yield connection
    connection.close()


@pytest.fixture
def autocommit_conn():
    connection = fast_firebirdsql.connect(**DB_CONFIG, autocommit=True)
    yield connection
    connection.close()


@pytest.fixture
def test_table(conn):
    """Create an empty TEST_FAST_FBSQL table and drop it afterwards."""
    cur = conn.cursor()
    # Drop leftovers from an earlier aborted run
    try:
        cur.execute(f"DROP TABLE {TEST_TABLE}")
        conn.commit()
    except RuntimeError:
        conn.rollback()
    cur.execute(
        f"CREATE TABLE {TEST_TABLE} (ID INTEGER NOT NULL, NAME VARCHAR(50), TS TIMESTAMP)"
    )
    conn.commit()
    yield TEST_TABLE
    try:
        cur.execute(f"DROP TABLE {TEST_TABLE}")
        conn.commit()
    except RuntimeError:
        conn.rollback()
