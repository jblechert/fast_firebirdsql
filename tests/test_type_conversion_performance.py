#!/usr/bin/env python3
"""
Test script for type conversion performance optimizations.
Tests the optimized sqltype_to_python function and caching mechanisms.
"""

import fast_firebird
import time
import gc

def test_type_conversion_performance():
    """Test type conversion performance improvements"""
    print("=== Type Conversion Performance Test ===\n")
    
    # Connection parameters
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED",
    }
    
    conn = fast_firebird.connect(**connection_params)
    
    # Test 1: String conversion performance with caching
    print("Test 1: String conversion performance with caching")
    print("-" * 50)
    
    # Clear cache first
    fast_firebird.clear_type_conversion_cache()
    
    # First run - should populate cache
    print("First run (populating cache):")
    cur1 = conn.cursor()
    
    start_time = time.perf_counter()
    cur1.execute("SELECT ARTIKELNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 1000")
    rows1 = cur1.fetchall()
    first_run_time = time.perf_counter() - start_time
    
    print(f"  Rows: {len(rows1)}")
    print(f"  Time: {first_run_time:.4f} seconds")
    
    # Check cache stats
    cache_stats = fast_firebird.get_type_conversion_cache_stats()
    print(f"  Cache size after first run: {cache_stats['cache_size']}")
    if 'sample_cached_strings' in cache_stats:
        print(f"  Sample cached strings: {cache_stats['sample_cached_strings'][:5]}")
    
    # Second run - should benefit from cache
    print("\nSecond run (using cache):")
    cur2 = conn.cursor()
    
    start_time = time.perf_counter()
    cur2.execute("SELECT ARTIKELNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 1000")
    rows2 = cur2.fetchall()
    second_run_time = time.perf_counter() - start_time
    
    print(f"  Rows: {len(rows2)}")
    print(f"  Time: {second_run_time:.4f} seconds")
    print(f"  Performance improvement: {((first_run_time - second_run_time) / first_run_time * 100):.1f}%")
    
    # Verify data consistency
    print(f"  Data consistency: {rows1[:3] == rows2[:3]}")
    
    # Test 2: Mixed type conversion performance
    print("\n" + "=" * 60)
    print("Test 2: Mixed type conversion performance")
    print("-" * 50)
    
    # Test with various data types
    cur3 = conn.cursor()
    
    start_time = time.perf_counter()
    cur3.execute("""
        SELECT 
            WFLARTIKELNUMMER,           -- Integer
            ARTIKELNUMMER,              -- String
            ZEICHNUNGSNUMMER,           -- String (often NULL)
            MATCHCODE,                  -- String
            DISPONENT                   -- String (often empty)
        FROM ARTIKELSTAMMDATEN 
        WHERE MANDANT = 1 AND GESPERRT = 0 
        ROWS 2000
    """)
    mixed_rows = cur3.fetchall()
    mixed_time = time.perf_counter() - start_time
    
    print(f"  Rows: {len(mixed_rows)}")
    print(f"  Time: {mixed_time:.4f} seconds")
    print(f"  Rows per second: {len(mixed_rows) / mixed_time:.0f}")
    
    # Analyze data types in results
    if mixed_rows:
        sample_row = mixed_rows[0]
        print(f"  Sample row types: {[type(val).__name__ for val in sample_row]}")
        print(f"  Sample row: {sample_row}")
    
    # Test 3: Cache efficiency with repeated queries
    print("\n" + "=" * 60)
    print("Test 3: Cache efficiency with repeated queries")
    print("-" * 50)
    
    # Run the same query multiple times to test cache efficiency
    times = []
    for i in range(5):
        cur = conn.cursor()
        start_time = time.perf_counter()
        cur.execute("SELECT ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 500")
        rows = cur.fetchall()
        elapsed = time.perf_counter() - start_time
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.4f} seconds ({len(rows)} rows)")
    
    avg_time = sum(times) / len(times)
    print(f"  Average time: {avg_time:.4f} seconds")
    print(f"  Time variation: {(max(times) - min(times)):.4f} seconds")
    
    # Final cache stats
    final_cache_stats = fast_firebird.get_type_conversion_cache_stats()
    print(f"  Final cache size: {final_cache_stats['cache_size']}")
    
    # Test 4: Performance metrics comparison
    print("\n" + "=" * 60)
    print("Test 4: Performance metrics comparison")
    print("-" * 50)
    
    # Clear performance stats
    fast_firebird.clear_performance_stats()
    
    # Run a query and check metrics
    cur4 = conn.cursor()
    cur4.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 1000")
    rows4 = cur4.fetchall()
    
    metrics = cur4.get_last_metrics()
    if metrics:
        print(f"  Execution time: {metrics.get('execution_time_ms', 0):.2f} ms")
        print(f"  Fetch time: {metrics.get('fetch_time_ms', 0):.2f} ms")
        print(f"  Total time: {metrics.get('total_time_ms', 0):.2f} ms")
        print(f"  Rows processed: {metrics.get('rows_processed', 0)}")
        print(f"  Memory allocated: {metrics.get('memory_allocated_bytes', 0) / 1024:.1f} KB")
        print(f"  Rows per second: {metrics.get('rows_per_second', 0)}")
    
    # Test 5: Cache memory management
    print("\n" + "=" * 60)
    print("Test 5: Cache memory management")
    print("-" * 50)
    
    # Test cache limits by trying to cache many different strings
    print("Testing cache size limits...")
    initial_cache_size = fast_firebird.get_type_conversion_cache_stats()['cache_size']
    
    # Run queries that should generate many different string values
    for i in range(10):
        cur = conn.cursor()
        cur.execute(f"SELECT ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 AND WFLARTIKELNUMMER > {i * 100000} ROWS 100")
        rows = cur.fetchall()
    
    final_cache_size = fast_firebird.get_type_conversion_cache_stats()['cache_size']
    print(f"  Initial cache size: {initial_cache_size}")
    print(f"  Final cache size: {final_cache_size}")
    print(f"  Cache growth: {final_cache_size - initial_cache_size}")
    print(f"  Cache limit respected: {final_cache_size <= 1000}")
    
    conn.close()
    print("\n=== Type Conversion Performance Test Complete ===")

if __name__ == "__main__":
    test_type_conversion_performance()
