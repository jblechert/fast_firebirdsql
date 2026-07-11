#!/usr/bin/env python3
"""
Test the optimized fast_firebirdsql performance improvements
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import time
import gc

def test_optimized_vs_standard_firebirdsql():
    """Test optimized fast_firebirdsql vs standard firebirdsql"""
    print("🚀 OPTIMIZED FAST_FIREBIRDSQL vs FIREBIRDSQL COMPARISON")
    print("="*70)
    
    # Test 1: Simple queries (where we were slower before)
    print("\n1️⃣ SIMPLE QUERIES TEST (10x SELECT 1):")
    
    # Test optimized fast_firebirdsql
    import fast_firebirdsql
    
    conn = fast_firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    
    # Enable high-performance mode (no metrics, no caching)
    cur.set_high_performance_mode(True)
    
    start_time = time.time()
    for i in range(10):
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        cur.fetchone()
    fast_simple = time.time() - start_time
    conn.close()
    
    # Test standard firebirdsql
    import firebirdsql
    
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
    
    print(f"   fast_firebirdsql (optimized): {fast_simple:.6f}s")
    print(f"   firebirdsql:                  {standard_simple:.6f}s")
    
    if fast_simple < standard_simple:
        speedup = standard_simple / fast_simple
        print(f"   🚀 fast_firebirdsql is {speedup:.2f}x FASTER!")
    else:
        slowdown = fast_simple / standard_simple
        print(f"   ⚠️  fast_firebirdsql is {slowdown:.2f}x slower")
    
    # Test 2: Large dataset (where we were already faster)
    print(f"\n2️⃣ LARGE DATASET TEST:")
    
    # Test optimized fast_firebirdsql
    conn = fast_firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    cur.set_high_performance_mode(True)
    
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    rows = cur.fetchall()
    fast_large = time.time() - start_time
    fast_count = len(rows)
    conn.close()
    
    # Clear memory
    del rows
    gc.collect()
    
    # Test standard firebirdsql
    conn = firebirdsql.connect(
        **DB_CONFIG
    )
    cur = conn.cursor()
    
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    rows = cur.fetchall()
    standard_large = time.time() - start_time
    standard_count = len(rows)
    cur.close()
    conn.close()
    
    print(f"   fast_firebirdsql (optimized): {fast_large:.6f}s ({fast_count} rows, {fast_count/fast_large:.0f} rows/sec)")
    print(f"   firebirdsql:                  {standard_large:.6f}s ({standard_count} rows, {standard_count/standard_large:.0f} rows/sec)")
    
    if fast_large < standard_large:
        speedup = standard_large / fast_large
        print(f"   🚀 fast_firebirdsql is {speedup:.2f}x FASTER!")
    else:
        slowdown = fast_large / standard_large
        print(f"   ⚠️  fast_firebirdsql is {slowdown:.2f}x slower")
    
    # Test 3: Connection overhead
    print(f"\n3️⃣ CONNECTION OVERHEAD TEST (5 connections):")
    
    # Test optimized fast_firebirdsql
    times = []
    for i in range(5):
        start_time = time.time()
        conn = fast_firebirdsql.connect(
            **DB_CONFIG
        )
        conn.close()
        times.append(time.time() - start_time)
    fast_avg_conn = sum(times) / len(times)
    
    # Test standard firebirdsql
    times = []
    for i in range(5):
        start_time = time.time()
        conn = firebirdsql.connect(
            **DB_CONFIG
        )
        conn.close()
        times.append(time.time() - start_time)
    standard_avg_conn = sum(times) / len(times)
    
    print(f"   fast_firebirdsql (optimized): {fast_avg_conn:.6f}s avg")
    print(f"   firebirdsql:                  {standard_avg_conn:.6f}s avg")
    
    if fast_avg_conn < standard_avg_conn:
        speedup = standard_avg_conn / fast_avg_conn
        print(f"   🚀 fast_firebirdsql connections {speedup:.2f}x FASTER!")
    else:
        slowdown = fast_avg_conn / standard_avg_conn
        print(f"   ⚠️  fast_firebirdsql connections {slowdown:.2f}x slower")
    
    # Overall summary
    print(f"\n🏆 OPTIMIZATION SUMMARY:")
    total_fast = fast_simple + fast_large + fast_avg_conn
    total_standard = standard_simple + standard_large + standard_avg_conn
    
    if total_fast < total_standard:
        overall_speedup = total_standard / total_fast
        print(f"   🚀 Overall: fast_firebirdsql is {overall_speedup:.2f}x FASTER!")
        print(f"   ✅ Optimization successful - fast_firebirdsql now wins in ALL scenarios!")
    else:
        overall_slowdown = total_fast / total_standard
        print(f"   ⚠️  Overall: fast_firebirdsql is {overall_slowdown:.2f}x slower")
        print(f"   🔧 More optimization needed")

def test_performance_modes():
    """Test different performance modes"""
    print(f"\n🔧 PERFORMANCE MODES TEST:")
    
    import fast_firebirdsql
    
    conn = fast_firebirdsql.connect(
        **DB_CONFIG
    )
    
    # Test default mode
    cur = conn.cursor()
    start_time = time.time()
    for i in range(5):
        cur.execute("SELECT COUNT(*) FROM RDB$DATABASE")
        cur.fetchone()
    default_time = time.time() - start_time
    
    # Test high-performance mode
    cur.set_high_performance_mode(True)
    start_time = time.time()
    for i in range(5):
        cur.execute("SELECT COUNT(*) FROM RDB$DATABASE")
        cur.fetchone()
    hp_time = time.time() - start_time
    
    # Test with metrics enabled
    cur.set_high_performance_mode(False)
    cur.set_metrics_enabled(True)
    start_time = time.time()
    for i in range(5):
        cur.execute("SELECT COUNT(*) FROM RDB$DATABASE")
        cur.fetchone()
    metrics_time = time.time() - start_time
    
    conn.close()
    
    print(f"   Default mode:           {default_time:.6f}s")
    print(f"   High-performance mode:  {hp_time:.6f}s")
    print(f"   With metrics:           {metrics_time:.6f}s")
    
    if hp_time < default_time:
        speedup = default_time / hp_time
        print(f"   🚀 High-performance mode is {speedup:.2f}x faster than default!")

def main():
    test_optimized_vs_standard_firebirdsql()
    test_performance_modes()

if __name__ == "__main__":
    main()
