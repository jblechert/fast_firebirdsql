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
`datetime.datetime`, `datetime.date`. Never interpolate untrusted input
into SQL strings.

## Known limitations

- `cursor.description` is derived from the first result row; for a SELECT
  that returns no rows it is `None`. Only column names and coarse type
  codes are filled in.
- `decimal.Decimal` parameters are not supported (convert to `str` or
  `float`); NUMERIC columns come back as `float`.
- **BLOB columns cannot be read** (`Unsupported column type (520 ...)`),
  a limitation of rsfbclient's native client. Select around them or cast
  (`CAST(blob_col AS VARCHAR(...))`).
- Statements are routed by their first keyword: only `SELECT`/`WITH`
  return result rows.
- **Build currently requires Python ≤ 3.13** (PyO3 0.22). Production runs
  3.13, so this is not a blocker; on newer interpreters the build fails.

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

MIT — see [LICENSE](LICENSE).
