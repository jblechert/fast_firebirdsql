"""DB-API behaviour tests for fast_firebirdsql (v0.6.0+).

Covers parameter binding, transactions (commit/rollback/autocommit),
cursor.description and cursor.rowcount.
"""

import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from db_config import DB_CONFIG

import fast_firebirdsql

from conftest import drop_table_fresh, requires_write


# --- read-only tests ---------------------------------------------------


def test_connect_and_close():
    conn = fast_firebirdsql.connect(**DB_CONFIG)
    conn.close()
    conn.close()  # double close must not raise


def test_cursor_after_close_raises():
    conn = fast_firebirdsql.connect(**DB_CONFIG)
    conn.close()
    with pytest.raises(RuntimeError):
        conn.cursor()


def test_connect_bad_host_raises_immediately():
    with pytest.raises(RuntimeError):
        fast_firebirdsql.connect(
            host="127.0.0.1",
            database="/nonexistent/no.fdb",
            port=1,
            user="X",
            password="Y",
        )


def test_select_fetchall(conn):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM RDB$DATABASE")
    rows = cur.fetchall()
    assert rows == [(1,)]


def test_select_with_params(conn):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM RDB$DATABASE WHERE 1 = ?", (1,))
    assert cur.fetchall() == [(1,)]
    cur.execute("SELECT 1 FROM RDB$DATABASE WHERE 1 = ?", (2,))
    assert cur.fetchall() == []


def test_param_type_roundtrip(conn):
    cur = conn.cursor()
    ts = datetime.datetime(2026, 7, 11, 12, 30, 45, 123400)
    cur.execute(
        "SELECT CAST(? AS INTEGER), CAST(? AS VARCHAR(50)), "
        "CAST(? AS DOUBLE PRECISION), CAST(? AS TIMESTAMP), CAST(? AS INTEGER) "
        "FROM RDB$DATABASE",
        (42, "hello wörld", 3.5, ts, None),
    )
    row = cur.fetchall()[0]
    assert row == (42, "hello wörld", 3.5, ts, None)


def test_date_param(conn):
    cur = conn.cursor()
    d = datetime.date(2026, 7, 11)
    cur.execute("SELECT CAST(? AS DATE) FROM RDB$DATABASE", (d,))
    result = cur.fetchall()[0][0]
    # DATE columns come back as datetime at midnight
    assert result == datetime.datetime(2026, 7, 11, 0, 0, 0)


def test_decimal_param_exact(conn):
    # Decimal params are sent as plain-notation strings; the server casts
    # them to NUMERIC exactly. Verified via VARCHAR cast (read-only).
    import decimal
    cur = conn.cursor()
    for value in ("12345678.9012", "-0.0001", "0.1", "99999999999999.9999"):
        d = decimal.Decimal(value)
        cur.execute(
            "SELECT CAST(CAST(? AS NUMERIC(18,4)) AS VARCHAR(30)) FROM RDB$DATABASE",
            (d,),
        )
        result = decimal.Decimal(cur.fetchall()[0][0])
        assert result == d, f"{value}: {result} != {d}"


def test_decimal_scientific_notation_param(conn):
    # Decimal('1E+2') must not reach the server in scientific notation
    import decimal
    cur = conn.cursor()
    cur.execute(
        "SELECT CAST(CAST(? AS NUMERIC(18,4)) AS VARCHAR(30)) FROM RDB$DATABASE",
        (decimal.Decimal("1E+2"),),
    )
    assert decimal.Decimal(cur.fetchall()[0][0]) == decimal.Decimal(100)


def test_params_as_list(conn):
    cur = conn.cursor()
    cur.execute("SELECT CAST(? AS INTEGER) FROM RDB$DATABASE", [7])
    assert cur.fetchall() == [(7,)]


def test_string_params_rejected(conn):
    cur = conn.cursor()
    with pytest.raises(TypeError):
        cur.execute("SELECT CAST(? AS VARCHAR(10)) FROM RDB$DATABASE", "abc")


def test_unsupported_param_type_rejected(conn):
    cur = conn.cursor()
    with pytest.raises(TypeError):
        cur.execute("SELECT CAST(? AS INTEGER) FROM RDB$DATABASE", (object(),))


def test_description(conn):
    cur = conn.cursor()
    cur.execute("SELECT RDB$RELATION_ID AS REL_ID, RDB$CHARACTER_SET_NAME FROM RDB$DATABASE")
    cur.fetchall()
    assert cur.description is not None
    names = [d[0] for d in cur.description]
    assert names == ["REL_ID", "RDB$CHARACTER_SET_NAME"]
    assert all(len(d) == 7 for d in cur.description)


def test_description_empty_result_is_none(conn):
    # Known limitation: metadata is derived from the first row
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM RDB$DATABASE WHERE 1 = 0")
    cur.fetchall()
    assert cur.description is None


def test_rowcount_select(conn):
    cur = conn.cursor()
    assert cur.rowcount == -1
    cur.execute("SELECT 1 FROM RDB$DATABASE")
    assert cur.rowcount == 1


def test_fetchone_and_fetchmany(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT RDB$RELATION_ID FROM RDB$RELATIONS ORDER BY RDB$RELATION_ID ROWS 5"
    )
    first = cur.fetchone()
    assert first is not None
    rest = cur.fetchmany(2)
    assert len(rest) == 2
    remaining = cur.fetchall()
    assert cur.rowcount == 5


def test_commit_rollback_without_writes(conn):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM RDB$DATABASE")
    cur.fetchall()
    conn.commit()
    conn.rollback()  # no pending transaction: must not raise


def test_text_blob_read(conn):
    # BLOB SUB_TYPE TEXT comes back as str (read-only via CAST)
    cur = conn.cursor()
    cur.execute("SELECT CAST(? AS BLOB SUB_TYPE TEXT) FROM RDB$DATABASE", ("blob-inhalt äöü",))
    assert cur.fetchall() == [("blob-inhalt äöü",)]


def test_wide_select(conn):
    # Guards against any column-count limitation in the row conversion.
    # (Not SELECT * on a system table: those contain BLR blobs, subtype 2,
    # which rsfbclient cannot read.)
    n = 25
    cols = ", ".join(f"CAST({i} AS INTEGER) AS C{i}" for i in range(n))
    cur = conn.cursor()
    cur.execute(f"SELECT {cols} FROM RDB$DATABASE")
    rows = cur.fetchall()
    assert rows == [tuple(range(n))]
    assert [d[0] for d in cur.description] == [f"C{i}" for i in range(n)]


def test_multiple_cursors_share_connection(conn):
    c1 = conn.cursor()
    c2 = conn.cursor()
    c1.execute("SELECT 1 FROM RDB$DATABASE")
    c2.execute("SELECT 2 FROM RDB$DATABASE")
    assert c1.fetchall() == [(1,)]
    assert c2.fetchall() == [(2,)]


# --- write tests (FIREBIRD_ALLOW_WRITE_TESTS=1) ------------------------


@requires_write
def test_insert_with_params_and_rowcount(conn, test_table):
    cur = conn.cursor()
    ts = datetime.datetime(2026, 7, 11, 8, 15, 0)
    cur.execute(
        f"INSERT INTO {test_table} (ID, NAME, TS) VALUES (?, ?, ?)",
        (1, "eins", ts),
    )
    assert cur.rowcount == 1
    cur.execute(f"SELECT ID, NAME, TS FROM {test_table}")
    assert cur.fetchall() == [(1, "eins", ts)]
    conn.rollback()


@requires_write
def test_rollback_undoes_insert(conn, test_table):
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {test_table} (ID, NAME) VALUES (?, ?)", (1, "weg damit"))
    conn.rollback()
    cur.execute(f"SELECT COUNT(*) FROM {test_table}")
    assert cur.fetchall() == [(0,)]


@requires_write
def test_commit_persists_for_other_connection(conn, test_table):
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {test_table} (ID, NAME) VALUES (?, ?)", (2, "bleibt"))
    conn.commit()

    other = fast_firebirdsql.connect(**DB_CONFIG)
    try:
        ocur = other.cursor()
        ocur.execute(f"SELECT ID, NAME FROM {test_table}")
        assert ocur.fetchall() == [(2, "bleibt")]
    finally:
        other.close()

    cur.execute(f"DELETE FROM {test_table}")
    assert cur.rowcount == 1
    conn.commit()


@requires_write
def test_uncommitted_insert_invisible_to_other_connection(conn, test_table):
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {test_table} (ID) VALUES (?)", (3,))

    other = fast_firebirdsql.connect(**DB_CONFIG)
    try:
        ocur = other.cursor()
        ocur.execute(f"SELECT COUNT(*) FROM {test_table}")
        assert ocur.fetchall() == [(0,)]
    finally:
        other.close()
    conn.rollback()


@requires_write
def test_close_rolls_back_open_transaction(test_table, conn):
    writer = fast_firebirdsql.connect(**DB_CONFIG)
    wcur = writer.cursor()
    wcur.execute(f"INSERT INTO {test_table} (ID) VALUES (?)", (4,))
    writer.close()  # DB-API: close without commit rolls back

    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {test_table}")
    assert cur.fetchall() == [(0,)]


@requires_write
def test_executemany(conn, test_table):
    cur = conn.cursor()
    cur.executemany(
        f"INSERT INTO {test_table} (ID, NAME) VALUES (?, ?)",
        [(1, "a"), (2, "b"), (3, "c")],
    )
    assert cur.rowcount == 3
    cur.execute(f"SELECT COUNT(*) FROM {test_table}")
    assert cur.fetchall() == [(3,)]
    conn.rollback()


@requires_write
def test_autocommit_mode(autocommit_conn, test_table, conn):
    # test_table was created via `conn`; make its DDL visible to everyone
    acur = autocommit_conn.cursor()
    acur.execute(f"INSERT INTO {test_table} (ID) VALUES (?)", (5,))
    # no commit on purpose - autocommit must have persisted the row

    cur = conn.cursor()
    cur.execute(f"SELECT ID FROM {test_table}")
    assert cur.fetchall() == [(5,)]
    conn.commit()

    acur.execute(f"DELETE FROM {test_table}")


@requires_write
def test_decimal_column_roundtrip(conn, test_table):
    # Storage is exact (verified via VARCHAR cast); reading the column
    # directly yields float — a documented limitation of rsfbclient
    import decimal
    d = decimal.Decimal("4711.0815")
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {test_table} (ID, AMOUNT) VALUES (?, ?)", (1, d))
    cur.execute(f"SELECT CAST(AMOUNT AS VARCHAR(30)) FROM {test_table}")
    assert decimal.Decimal(cur.fetchall()[0][0]) == d
    cur.execute(f"SELECT AMOUNT FROM {test_table}")
    value = cur.fetchall()[0][0]
    assert isinstance(value, float) and abs(value - float(d)) < 1e-9
    conn.rollback()


@requires_write
def test_blob_roundtrip():
    # Self-contained: blob statements keep the table 'in use' on their own
    # connection, so create/drop happen via separate fresh connections
    table = "TEST_FAST_FBSQL_BLOB"
    drop_table_fresh(table)
    setup = fast_firebirdsql.connect(**DB_CONFIG)
    scur = setup.cursor()
    scur.execute(f"CREATE TABLE {table} (ID INTEGER, TXT BLOB SUB_TYPE TEXT, BIN BLOB SUB_TYPE 0)")
    setup.commit()
    setup.close()

    text_val = "Ein längerer Text mit Umlauten äöü " * 100
    bin_val = bytes(range(256)) * 200  # 51 KB, larger than one blob segment
    conn = fast_firebirdsql.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(f"INSERT INTO {table} (ID, TXT, BIN) VALUES (?, ?, ?)", (1, text_val, bin_val))
        conn.commit()
        cur.execute(f"SELECT TXT, BIN FROM {table}")
        row = cur.fetchall()[0]
        assert row[0] == text_val and isinstance(row[0], str)
        assert row[1] == bin_val and isinstance(row[1], bytes)
    finally:
        conn.close()
        drop_table_fresh(table)


@requires_write
def test_update_rowcount(conn, test_table):
    cur = conn.cursor()
    cur.executemany(
        f"INSERT INTO {test_table} (ID, NAME) VALUES (?, ?)",
        [(1, "x"), (2, "x"), (3, "y")],
    )
    cur.execute(f"UPDATE {test_table} SET NAME = ? WHERE NAME = ?", ("z", "x"))
    assert cur.rowcount == 2
    conn.rollback()
