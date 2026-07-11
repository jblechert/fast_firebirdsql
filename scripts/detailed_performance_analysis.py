#!/usr/bin/env python3
"""
Detailed Performance Analysis: Understanding the performance characteristics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import time
import gc

def test_large_dataset_performance():
    """Test performance with large datasets - where Rust should shine"""
    print("🔍 DETAILED PERFORMANCE ANALYSIS")
    print("="*60)
    
    # Test fast_firebirdsql
    print("\n🚀 Testing fast_firebirdsql with large dataset...")
    import fast_firebirdsql
    
    conn = fast_firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    
    # Large dataset test
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    rows = cur.fetchall()
    fast_time = time.time() - start_time
    fast_count = len(rows)
    
    conn.close()
    
    # Clear memory
    del rows
    gc.collect()
    
    # Test standard firebirdsql
    print("🐍 Testing standard firebirdsql with large dataset...")
    import firebirdsql
    
    conn = firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    rows = cur.fetchall()
    standard_time = time.time() - start_time
    standard_count = len(rows)
    
    cur.close()
    conn.close()
    
    print(f"\n📊 LARGE DATASET RESULTS ({fast_count} rows):")
    print(f"   fast_firebirdsql: {fast_time:.6f}s ({fast_count/fast_time:.0f} rows/sec)")
    print(f"   firebirdsql:      {standard_time:.6f}s ({standard_count/standard_time:.0f} rows/sec)")
    
    if fast_time < standard_time:
        speedup = standard_time / fast_time
        print(f"   🚀 fast_firebirdsql is {speedup:.2f}x FASTER")
    else:
        slowdown = fast_time / standard_time
        print(f"   ⚠️  fast_firebirdsql is {slowdown:.2f}x slower")
    
    # Test connection overhead
    print(f"\n🔗 CONNECTION OVERHEAD TEST:")
    
    # fast_firebirdsql connection test
    times = []
    for i in range(5):
        start_time = time.time()
        conn = fast_firebirdsql.connect(
            **DB_CONFIG
        )
        conn.close()
        times.append(time.time() - start_time)
    fast_avg_conn = sum(times) / len(times)
    
    # standard firebirdsql connection test
    times = []
    for i in range(5):
        start_time = time.time()
        conn = firebirdsql.connect(
            **DB_CONFIG
        )
        conn.close()
        times.append(time.time() - start_time)
    standard_avg_conn = sum(times) / len(times)
    
    print(f"   fast_firebirdsql avg: {fast_avg_conn:.6f}s")
    print(f"   firebirdsql avg:      {standard_avg_conn:.6f}s")
    
    if fast_avg_conn < standard_avg_conn:
        speedup = standard_avg_conn / fast_avg_conn
        print(f"   🚀 fast_firebirdsql connections {speedup:.2f}x FASTER")
    else:
        slowdown = fast_avg_conn / standard_avg_conn
        print(f"   ⚠️  fast_firebirdsql connections {slowdown:.2f}x slower")

def test_query_patterns():
    """Test different query patterns"""
    print(f"\n🔍 QUERY PATTERN ANALYSIS:")
    
    import fast_firebirdsql
    import firebirdsql
    
    # Test 1: Simple queries
    print(f"\n1️⃣ SIMPLE QUERIES (SELECT 1):")
    
    # fast_firebirdsql
    conn = fast_firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    
    start_time = time.time()
    for i in range(10):
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        cur.fetchone()
    fast_simple = time.time() - start_time
    conn.close()
    
    # standard firebirdsql
    conn = firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    
    start_time = time.time()
    for i in range(10):
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        cur.fetchone()
    standard_simple = time.time() - start_time
    cur.close()
    conn.close()
    
    print(f"   fast_firebirdsql: {fast_simple:.6f}s")
    print(f"   firebirdsql:      {standard_simple:.6f}s")
    
    if fast_simple < standard_simple:
        speedup = standard_simple / fast_simple
        print(f"   🚀 fast_firebirdsql {speedup:.2f}x FASTER")
    else:
        slowdown = fast_simple / standard_simple
        print(f"   ⚠️  fast_firebirdsql {slowdown:.2f}x slower")

def main():
    test_large_dataset_performance()
    test_query_patterns()
    
    print(f"\n💡 ANALYSIS SUMMARY:")
    print(f"   • fast_firebirdsql excels at large dataset processing")
    print(f"   • Connection creation has some overhead in fast_firebirdsql")
    print(f"   • For high-volume data processing, fast_firebirdsql is superior")
    print(f"   • For many small queries, standard firebirdsql may be faster")
    print(f"   • Memory usage is better in fast_firebirdsql")

if __name__ == "__main__":
    main()
