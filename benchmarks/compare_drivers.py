#!/usr/bin/env python3
"""Honest live performance comparison: firebirdsql (pure Python) vs fast_firebirdsql.

Methodology:
- identical queries, same database, same process
- one warmup round per driver and scenario (server cache, statement prep)
- alternating iterations (A, B, A, B, ...) to neutralise server-side drift
- timed with perf_counter; fetchall() included (full materialisation)
- reports median/mean/min; medians are the robust number, single runs on a
  real network can be skewed by >1s outliers hitting either driver

Requires both drivers installed and a reachable server (.env / db_config.py).
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import firebirdsql
import fast_firebirdsql

BIG_SQL = ("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT "
           "FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
BIG_SQL_PARAM = ("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT "
                 "FROM ARTIKELSTAMMDATEN WHERE MANDANT = ? AND GESPERRT = ?")


def timed(fn):
    t0 = time.perf_counter()
    result = fn()
    return time.perf_counter() - t0, result


def bench_alternating(fn_a, fn_b, iterations, check=None):
    """Warm up both, then alternate A/B. Returns (times_a, times_b)."""
    ra = fn_a()
    rb = fn_b()
    if check:
        check(ra, rb)
    times_a, times_b = [], []
    for _ in range(iterations):
        dt, _ = timed(fn_a)
        times_a.append(dt)
        dt, _ = timed(fn_b)
        times_b.append(dt)
    return times_a, times_b


def run_query(conn, sql, params=None):
    cur = conn.cursor()
    if params is None:
        cur.execute(sql)
    else:
        cur.execute(sql, params)
    return cur.fetchall()


def check_row_count(ra, rb):
    assert len(ra) == len(rb), f"row count differs: {len(ra)} vs {len(rb)}"


def fmt(times):
    return (f"med {statistics.median(times)*1000:8.2f} ms | "
            f"mean {statistics.mean(times)*1000:8.2f} ms | "
            f"min {min(times)*1000:8.2f} ms")


def report(name, times_a, times_b):
    med_a, med_b = statistics.median(times_a), statistics.median(times_b)
    factor = med_a / med_b if med_b > 0 else float("inf")
    print(f"\n### {name}")
    print(f"  firebirdsql       {fmt(times_a)}")
    print(f"  fast_firebirdsql  {fmt(times_b)}")
    print(f"  -> Faktor (Median): {factor:.1f}x")
    return factor


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iterations", type=int, default=None,
                        help="override per-scenario iteration counts (for quick runs)")
    args = parser.parse_args()

    def iters(default):
        return args.iterations if args.iterations else default

    print(f"firebirdsql {getattr(firebirdsql, '__version__', '?')} vs "
          f"fast_firebirdsql {fast_firebirdsql.__version__}")
    print(f"Server: {DB_CONFIG['host']}:{DB_CONFIG['port']}, DB: {DB_CONFIG['database']}")

    results = {}

    ta, tb = bench_alternating(
        lambda: firebirdsql.connect(**DB_CONFIG).close(),
        lambda: fast_firebirdsql.connect(**DB_CONFIG).close(),
        iterations=iters(15),
    )
    results["connect() + close()"] = report("connect() + close()", ta, tb)

    ca = firebirdsql.connect(**DB_CONFIG)
    cb = fast_firebirdsql.connect(**DB_CONFIG)

    scenarios = [
        ("Mini-Query (SELECT 1 FROM RDB$DATABASE)",
         "SELECT 1 FROM RDB$DATABASE", None, iters(100)),
        ("COUNT(*) ARTIKELSTAMMDATEN",
         "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1", None, iters(20)),
        ("100 Zeilen x 5 Spalten",
         BIG_SQL.replace("SELECT ", "SELECT FIRST 100 "), None, iters(30)),
        ("grosser SELECT (alle Zeilen x 5 Spalten)",
         BIG_SQL, None, iters(15)),
        ("grosser SELECT mit ?-Parametern",
         BIG_SQL_PARAM, (1, 0), iters(15)),
    ]

    for name, sql, params, n in scenarios:
        ta, tb = bench_alternating(
            lambda: run_query(ca, sql, params),
            lambda: run_query(cb, sql, params),
            iterations=n,
            check=check_row_count,
        )
        results[name] = report(name, ta, tb)

    # sanity: identical data
    sql100 = BIG_SQL.replace("SELECT ", "SELECT FIRST 100 ")
    ra = run_query(ca, sql100)
    rb = run_query(cb, sql100)
    mismatch = sum(1 for x, y in zip(ra, rb) if tuple(x) != tuple(y))
    print(f"\nDatenabgleich (100 Zeilen): {'identisch' if mismatch == 0 else f'{mismatch} Abweichungen!'}")

    ca.close()
    cb.close()

    print("\n=== Zusammenfassung (Median-Speedup fast vs. pure) ===")
    for name, factor in results.items():
        print(f"  {factor:5.1f}x  {name}")


if __name__ == "__main__":
    main()
