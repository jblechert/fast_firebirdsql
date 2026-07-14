# fast_firebirdsql

Fast Firebird database access for Python, implemented in Rust
([PyO3](https://pyo3.rs) + [rsfbclient](https://crates.io/crates/rsfbclient)).
Intended as a mostly drop-in replacement for the pure-Python
[`firebirdsql`](https://pypi.org/project/firebirdsql/) driver — change the
import, keep the rest of your code:

```python
import fast_firebirdsql

conn = fast_firebirdsql.connect(
    host="localhost", database="/path/to/db.fdb",
    port=3050, user="SYSDBA", password="masterkey",
)
cur = conn.cursor()
cur.execute("SELECT NAME FROM some_table WHERE ID = ?", (42,))
rows = cur.fetchall()
cur.execute("UPDATE some_table SET NAME = ? WHERE ID = ?", ("neu", 42))
conn.commit()          # or conn.rollback()
conn.close()           # closes with rollback of anything uncommitted
```

Since v0.7.1 the GIL is released during all database I/O (connect,
execute, fetch, commit/rollback), so other Python threads keep running
at full speed while a query is in flight.

Each connection keeps an LRU cache of prepared statements (the source
of the driver's speed advantage on repeated queries). The default size
is 20; workloads alternating between more distinct SQL strings should
raise it: `connect(..., stmt_cache_size=100)`.

## Transactions

Since v0.6.0 this driver follows DB-API semantics, like `firebirdsql`:
statements run inside a transaction (`READ COMMITTED RECORD_VERSION WAIT`)
that is ended by `conn.commit()` or `conn.rollback()`; closing a connection
rolls back uncommitted work. Pass `autocommit=True` to `connect()` to commit
every statement immediately (the behaviour of versions before 0.6.0).

## Parameter binding

`cursor.execute(sql, params)` and `cursor.executemany(sql, param_sets)`
accept qmark-style (`?`) placeholders with a tuple or list of values.
Supported parameter types: `None`, `bool`, `int`, `float`, `str`, `bytes`,
`datetime.datetime`, `datetime.date`, `decimal.Decimal` (sent as an exact
plain-notation string; the server casts it to NUMERIC without precision
loss). Never interpolate untrusted input into SQL strings.

## Known limitations

- `cursor.description` is derived from the first result row; for a SELECT
  that returns no rows it is `None`. Since v0.10.0 `type_code` is the
  numeric Firebird wire type (e.g. 496 for INTEGER, like `firebirdsql`)
  and `internal_size` is filled for fixed-width types;
  `precision`/`scale`/`null_ok` are not exposed by rsfbclient and stay
  `None`.
- NUMERIC/DECIMAL columns come back as `decimal.Decimal` (since v0.9.0),
  but the value passes through a DOUBLE on the wire, so it is exact only
  up to ~15-16 significant digits. For full-precision reads of larger
  values use `CAST(col AS VARCHAR(...))`.
- `INSERT/UPDATE/DELETE ... RETURNING` returns its row (since v0.9.0) and
  sets `rowcount = 1`. Deviation from `firebirdsql`: an UPDATE/DELETE
  RETURNING that matches no row yields an all-`None` tuple instead of
  `None` from `fetchone()`.
- BLOB columns work since v0.6.1: `BLOB SUB_TYPE TEXT` maps to `str`,
  `BLOB SUB_TYPE 0` (binary) to `bytes` — both directions. Only internal
  BLR metadata blobs (subtype 2, e.g. `RDB$VIEW_BLR`) cannot be read, so
  `SELECT *` on some system tables fails with
  `Unsupported column type (520 2)`.
- Statements are routed by their first keyword: only `SELECT`/`WITH`
  return result rows.
- Wheels use the stable ABI (`cp313-abi3`, since v0.11.0): one wheel per
  platform runs on every CPython ≥ 3.13, including future versions.

## Fixes in v0.11.2

- **Deadlock when a connection is shared across threads (fixed).** The
  driver locked its internal connection Mutex *before* releasing the GIL,
  so two Python threads using one connection could deadlock (thread A held
  the Mutex with the GIL released inside a DB call, thread B held the GIL
  blocked on the Mutex). The Mutex is now taken after the GIL is released.
  Concurrent access on a shared connection is fully serialised and no
  longer hangs.
- **Self-healing on fatal connection errors.** After a connection-fatal
  error (socket loss, SQLCODE -902/-901, or a poisoned cursor state -502)
  the connection is discarded and transparently rebuilt on the next call,
  instead of every subsequent statement failing until the app is
  restarted.

## Behaviour changes in v0.9.0 (drop-in compatibility with firebirdsql)

- `INSERT/UPDATE/DELETE ... RETURNING` returns the row (previously the
  RETURNING values were silently discarded).
- NUMERIC/DECIMAL columns are returned as `decimal.Decimal` (previously
  `float`).
- DATE columns are returned as `datetime.date`, TIME columns as
  `datetime.time` (previously both as `datetime.datetime`).
- CHAR(n) values are right-trimmed like `firebirdsql` (previously
  space-padded to the declared length).

## Behaviour changes in v0.6.0

- `conn.commit()`/`conn.rollback()` are real now (previously no-ops with
  per-statement autocommit). Code that never calls `commit()` must pass
  `autocommit=True` or it will lose its writes on `close()`.
- `fetchall()` after an `INSERT`/`UPDATE`/`DELETE` returns `[]`; the
  affected-row count moved to `cursor.rowcount` (previously a fake
  `[(n,)]` result row).
- `connect()` establishes the connection eagerly, so connection errors
  surface at `connect()` instead of at the first `execute()`.

## Building

Requires Rust, [uv](https://docs.astral.sh/uv/) (provides maturin via
`uvx`) and a Firebird client library (`libfbclient`) on the system.
The Makefile targets the production venv (Python 3.13) at
`/home/mjb/src/bstools-venv` by default; override with
`make VENV=/path/to/venv ...`.

```bash
make dev-install   # build (debug) and install into the venv
make install       # build (release) and install into the venv
make wheel         # build a portable manylinux wheel into dist/
make wheel-windows # cross-build a win_amd64 wheel (needs mingw-w64)
make test          # pytest suite (read-only) + legacy scripts (needs a database)
make test-write    # pytest incl. write tests (creates/drops table TEST_FAST_FBSQL)
make benchmark     # full benchmark suite
```

Windows cross-builds bundle `fbclient.dll`/`python313.dll` from
`windows-firebird/` into the wheel; see `docs/README_WINDOWS.md`.

## Test configuration

The test and benchmark scripts need a running Firebird server. Connection
parameters are read from environment variables (optionally via a `.env`
file in the project root, which is gitignored):

```bash
cp .env.example .env   # then edit the values
```

| Variable            | Default        |
|---------------------|----------------|
| `FIREBIRD_HOST`     | `localhost`    |
| `FIREBIRD_DATABASE` | `database.fdb` |
| `FIREBIRD_PORT`     | `3050`         |
| `FIREBIRD_USER`     | `SYSDBA`       |
| `FIREBIRD_PASSWORD` | `masterkey`    |

## Project layout

| Path           | Contents                                              |
|----------------|-------------------------------------------------------|
| `src/lib.rs`   | The entire Rust extension module                      |
| `tests/suite/` | pytest suite (write tests need FIREBIRD_ALLOW_WRITE_TESTS=1) |
| `benchmarks/`  | Benchmark suite, performance test runner and baseline |
| `docs/`        | Windows build notes and benchmark framework docs      |

## License

MIT — see [LICENSE](LICENSE). The wheels redistribute third-party
binaries (Firebird client library under IDPL/IPL, `python313.dll` under
PSF-2.0, LibTomMath under the Unlicense) — see
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
