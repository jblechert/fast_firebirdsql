#!/usr/bin/env python3
"""
Performance Comparison: fast_firebirdsql vs standard firebirdsql
Direct head-to-head performance testing with the same queries and data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import time
import sys
import gc
import psutil
import os

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def test_fast_firebirdsql():
    """Test fast_firebirdsql performance"""
    print("🚀 Testing fast_firebirdsql...")
    
    import fast_firebirdsql
    
    results = {}
    
    # Connection test
    start_time = time.time()
    conn = fast_firebirdsql.connect(
        **DB_CONFIG
    )
    connection_time = time.time() - start_time
    results['connection_time'] = connection_time
    
    cur = conn.cursor()
    
    # Test 1: Simple count query
    start_time = time.time()
    cur.execute("SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    count_result = cur.fetchone()
    count_time = time.time() - start_time
    results['count_query_time'] = count_time
    results['count_result'] = count_result[0]
    
    # Test 2: Complex select query (first 100 rows)
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 100")
    rows_100 = cur.fetchall()
    select_100_time = time.time() - start_time
    results['select_100_time'] = select_100_time
    results['select_100_count'] = len(rows_100)
    
    # Test 3: Large select query (all rows)
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    all_rows = cur.fetchall()
    select_all_time = time.time() - start_time
    results['select_all_time'] = select_all_time
    results['select_all_count'] = len(all_rows)
    
    # Test 4: Multiple small queries
    start_time = time.time()
    for i in range(10):
        cur.execute("SELECT COUNT(*) FROM RDB$DATABASE")
        cur.fetchone()
    multiple_queries_time = time.time() - start_time
    results['multiple_queries_time'] = multiple_queries_time
    
    conn.close()
    
    results['memory_usage'] = get_memory_usage()
    results['module'] = 'fast_firebirdsql'
    results['version'] = fast_firebirdsql.__version__
    
    return results

def test_standard_firebirdsql():
    """Test standard firebirdsql performance"""
    print("🐍 Testing standard firebirdsql...")
    
    import firebirdsql
    
    results = {}
    
    # Connection test
    start_time = time.time()
    conn = firebirdsql.connect(
        **DB_CONFIG
    )
    connection_time = time.time() - start_time
    results['connection_time'] = connection_time
    
    cur = conn.cursor()
    
    # Test 1: Simple count query
    start_time = time.time()
    cur.execute("SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    count_result = cur.fetchone()
    count_time = time.time() - start_time
    results['count_query_time'] = count_time
    results['count_result'] = count_result[0]
    
    # Test 2: Complex select query (first 100 rows)
    start_time = time.time()
    cur.execute("SELECT FIRST 100 WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    rows_100 = cur.fetchall()
    select_100_time = time.time() - start_time
    results['select_100_time'] = select_100_time
    results['select_100_count'] = len(rows_100)
    
    # Test 3: Large select query (all rows)
    start_time = time.time()
    cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    all_rows = cur.fetchall()
    select_all_time = time.time() - start_time
    results['select_all_time'] = select_all_time
    results['select_all_count'] = len(all_rows)
    
    # Test 4: Multiple small queries
    start_time = time.time()
    for i in range(10):
        cur.execute("SELECT COUNT(*) FROM RDB$DATABASE")
        cur.fetchone()
    multiple_queries_time = time.time() - start_time
    results['multiple_queries_time'] = multiple_queries_time
    
    cur.close()
    conn.close()
    
    results['memory_usage'] = get_memory_usage()
    results['module'] = 'firebirdsql'
    results['version'] = getattr(firebirdsql, '__version__', 'unknown')
    
    return results

def print_comparison(fast_results, standard_results):
    """Print detailed comparison results"""
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON RESULTS")
    print("="*80)
    
    print(f"\n📊 MODULE VERSIONS:")
    print(f"   fast_firebirdsql: {fast_results['version']}")
    print(f"   firebirdsql:      {standard_results['version']}")
    
    print(f"\n🔗 CONNECTION TIME:")
    print(f"   fast_firebirdsql: {fast_results['connection_time']:.6f}s")
    print(f"   firebirdsql:      {standard_results['connection_time']:.6f}s")
    speedup = standard_results['connection_time'] / fast_results['connection_time']
    print(f"   ⚡ Speedup:       {speedup:.2f}x faster")
    
    print(f"\n📊 COUNT QUERY (1 row):")
    print(f"   fast_firebirdsql: {fast_results['count_query_time']:.6f}s")
    print(f"   firebirdsql:      {standard_results['count_query_time']:.6f}s")
    speedup = standard_results['count_query_time'] / fast_results['count_query_time']
    print(f"   ⚡ Speedup:       {speedup:.2f}x faster")
    
    print(f"\n📊 SELECT 100 ROWS:")
    print(f"   fast_firebirdsql: {fast_results['select_100_time']:.6f}s ({fast_results['select_100_count']} rows)")
    print(f"   firebirdsql:      {standard_results['select_100_time']:.6f}s ({standard_results['select_100_count']} rows)")
    speedup = standard_results['select_100_time'] / fast_results['select_100_time']
    print(f"   ⚡ Speedup:       {speedup:.2f}x faster")
    
    print(f"\n📊 SELECT ALL ROWS:")
    print(f"   fast_firebirdsql: {fast_results['select_all_time']:.6f}s ({fast_results['select_all_count']} rows)")
    print(f"   firebirdsql:      {standard_results['select_all_time']:.6f}s ({standard_results['select_all_count']} rows)")
    speedup = standard_results['select_all_time'] / fast_results['select_all_time']
    print(f"   ⚡ Speedup:       {speedup:.2f}x faster")
    
    # Calculate rows per second
    fast_rps = fast_results['select_all_count'] / fast_results['select_all_time']
    standard_rps = standard_results['select_all_count'] / standard_results['select_all_time']
    print(f"   📈 fast_firebirdsql: {fast_rps:.0f} rows/second")
    print(f"   📈 firebirdsql:      {standard_rps:.0f} rows/second")
    
    print(f"\n📊 MULTIPLE QUERIES (10x COUNT):")
    print(f"   fast_firebirdsql: {fast_results['multiple_queries_time']:.6f}s")
    print(f"   firebirdsql:      {standard_results['multiple_queries_time']:.6f}s")
    speedup = standard_results['multiple_queries_time'] / fast_results['multiple_queries_time']
    print(f"   ⚡ Speedup:       {speedup:.2f}x faster")
    
    print(f"\n💾 MEMORY USAGE:")
    print(f"   fast_firebirdsql: {fast_results['memory_usage']:.1f} MB")
    print(f"   firebirdsql:      {standard_results['memory_usage']:.1f} MB")
    
    # Overall performance summary
    total_fast = (fast_results['connection_time'] + fast_results['count_query_time'] + 
                  fast_results['select_100_time'] + fast_results['select_all_time'] + 
                  fast_results['multiple_queries_time'])
    total_standard = (standard_results['connection_time'] + standard_results['count_query_time'] + 
                      standard_results['select_100_time'] + standard_results['select_all_time'] + 
                      standard_results['multiple_queries_time'])
    
    overall_speedup = total_standard / total_fast
    
    print(f"\n🏆 OVERALL PERFORMANCE:")
    print(f"   Total time fast_firebirdsql: {total_fast:.6f}s")
    print(f"   Total time firebirdsql:      {total_standard:.6f}s")
    print(f"   🚀 Overall speedup:          {overall_speedup:.2f}x faster")
    
    print("\n" + "="*80)

def main():
    """Run the performance comparison"""
    print("🔥 FAST_FIREBIRDSQL vs FIREBIRDSQL PERFORMANCE COMPARISON")
    print("="*80)
    
    # Clear memory before starting
    gc.collect()
    
    try:
        # Test fast_firebirdsql
        fast_results = test_fast_firebirdsql()
        
        # Clear memory between tests
        gc.collect()
        
        # Test standard firebirdsql
        standard_results = test_standard_firebirdsql()
        
        # Print comparison
        print_comparison(fast_results, standard_results)
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
