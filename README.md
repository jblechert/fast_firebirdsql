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
cur.execute("SELECT * FROM some_table")
rows = cur.fetchall()
conn.close()
```

## Known limitations

Read this before relying on the "drop-in" claim:

- **Autocommit only.** Every `INSERT`/`UPDATE`/`DELETE`/`MERGE` commits
  immediately in its own transaction. `conn.commit()` and `conn.rollback()`
  exist for API compatibility but are **no-ops** — there is no way to roll
  back a statement that has been executed.
- **No parameter binding.** `cursor.execute(sql, params)` is not supported;
  only plain SQL strings. Do not interpolate untrusted input into queries.
- `cursor.description` and `cursor.rowcount` are not implemented.
- **Build currently requires Python ≤ 3.13** (PyO3 0.22). Upgrading PyO3 is
  planned; on newer interpreters the build fails.

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
make test          # basic functionality tests (needs a reachable database)
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

| Path          | Contents                                              |
|---------------|-------------------------------------------------------|
| `src/lib.rs`  | The entire Rust extension module                      |
| `tests/`      | Print-based test scripts (no pytest yet)              |
| `benchmarks/` | Benchmark suite, performance test runner and baseline |
| `scripts/`    | One-off debug/analysis scripts and demos              |
| `docs/`       | Historical development notes and Windows instructions |

## License

MIT — see [LICENSE](LICENSE).
