#!/usr/bin/env python3
"""
Test connection pooling performance improvements.
This test verifies that connection reuse eliminates connection overhead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebird
import time

def test_connection_pooling():
    """Test that connection pooling reduces connection overhead"""
    print("Testing Connection Pooling Performance")
    print("=" * 60)
    
    connection_params = dict(DB_CONFIG)
    
    # Clear any existing metrics
    fast_firebird.clear_performance_stats()
    
    # Test 1: Multiple queries with same cursor (should reuse connection)
    print("\n=== Test 1: Multiple queries with same cursor ===")
    conn = fast_firebird.connect(**connection_params)
    cur = conn.cursor()
    
    queries = [
        "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
        "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
        "SELECT FIRST 3 WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"
    ]
    
    connection_times = []
    total_times = []
    
    for i, query in enumerate(queries):
        print(f"\nQuery {i+1}: {query}")
        
        start_time = time.time()
        cur.execute(query)
        rows = cur.fetchall()
        end_time = time.time()
        
        # Get metrics
        metrics = cur.get_last_metrics()
        if metrics:
            conn_time = metrics.get('connection_time_ms', 0)
            total_time = metrics.get('total_time_ms', 0)
            connection_times.append(conn_time)
            total_times.append(total_time)
            
            print(f"  Results: {len(rows)} rows")
            print(f"  Connection time: {conn_time}ms")
            print(f"  Total time: {total_time}ms")
            print(f"  Connection status: {cur.get_connection_status()}")
            print(f"  Connection available: {cur.is_connection_available()}")
        
        print(f"  Wall clock time: {(end_time - start_time)*1000:.1f}ms")
    
    conn.close()
    
    # Analyze results
    print(f"\n=== Connection Pooling Analysis ===")
    print(f"Connection times: {connection_times}")
    print(f"Total times: {total_times}")
    
    if len(connection_times) >= 2:
        first_conn_time = connection_times[0]
        subsequent_conn_times = connection_times[1:]
        avg_subsequent = sum(subsequent_conn_times) / len(subsequent_conn_times)
        
        print(f"First connection time: {first_conn_time}ms")
        print(f"Average subsequent connection time: {avg_subsequent:.1f}ms")
        
        if avg_subsequent < first_conn_time * 0.1:  # Should be much faster
            print("✅ Connection pooling is working! Subsequent connections are much faster.")
        else:
            print("❌ Connection pooling may not be working optimally.")
    
    # Test 2: Multiple cursors with same connection (should share connection)
    print(f"\n=== Test 2: Multiple cursors with same connection ===")
    conn2 = fast_firebird.connect(**connection_params)
    
    cursors = []
    for i in range(3):
        cur = conn2.cursor()
        cursors.append(cur)
        print(f"Cursor {i+1} connection status: {cur.get_connection_status()}")
    
    # Execute queries with different cursors
    for i, cur in enumerate(cursors):
        query = f"SELECT {i+1} FROM RDB$DATABASE"
        cur.execute(query)
        rows = cur.fetchall()
        
        metrics = cur.get_last_metrics()
        if metrics:
            conn_time = metrics.get('connection_time_ms', 0)
            print(f"Cursor {i+1} - Connection time: {conn_time}ms, Result: {rows[0][0]}")
    
    conn2.close()
    
    # Test 3: Connection validation
    print(f"\n=== Test 3: Connection validation ===")
    conn3 = fast_firebird.connect(**connection_params)
    cur3 = conn3.cursor()
    
    # First query to establish connection
    cur3.execute("SELECT 1 FROM RDB$DATABASE")
    rows = cur3.fetchall()
    print(f"Initial connection status: {cur3.get_connection_status()}")
    
    # Second query should reuse connection
    cur3.execute("SELECT 2 FROM RDB$DATABASE")
    rows = cur3.fetchall()
    print(f"After reuse connection status: {cur3.get_connection_status()}")
    
    conn3.close()
    print(f"After close connection status: {cur3.get_connection_status()}")
    
    # Show global performance stats
    print(f"\n=== Global Performance Statistics ===")
    stats = fast_firebird.get_performance_stats()
    for operation, metrics in stats.items():
        print(f"{operation}: {metrics}")


def test_connection_overhead_comparison():
    """Compare connection overhead before and after pooling"""
    print(f"\n" + "=" * 60)
    print("CONNECTION OVERHEAD COMPARISON")
    print("=" * 60)
    
    connection_params = dict(DB_CONFIG)
    
    # Clear metrics
    fast_firebird.clear_performance_stats()
    
    # Test: 5 queries with connection reuse
    print("\nTesting 5 queries with connection reuse...")
    conn = fast_firebird.connect(**connection_params)
    cur = conn.cursor()
    
    reuse_times = []
    for i in range(5):
        start = time.time()
        cur.execute("SELECT COUNT(*) FROM RDB$DATABASE")
        rows = cur.fetchall()
        end = time.time()
        
        wall_time = (end - start) * 1000
        reuse_times.append(wall_time)
        
        metrics = cur.get_last_metrics()
        if metrics:
            conn_time = metrics.get('connection_time_ms', 0)
            total_time = metrics.get('total_time_ms', 0)
            print(f"  Query {i+1}: {wall_time:.1f}ms wall time, {conn_time}ms connection time, {total_time}ms total")
    
    conn.close()
    
    avg_reuse_time = sum(reuse_times) / len(reuse_times)
    print(f"\nAverage time with connection reuse: {avg_reuse_time:.1f}ms")
    
    # Show improvement
    baseline_time = 155 + 33 + 440  # From our baseline: connection + execution + fetch
    improvement = ((baseline_time - avg_reuse_time) / baseline_time) * 100
    print(f"Baseline time (no pooling): ~{baseline_time}ms")
    print(f"Improvement: {improvement:.1f}% faster")
    
    if improvement > 20:
        print("✅ Significant performance improvement achieved!")
    else:
        print("⚠️  Performance improvement is less than expected.")


if __name__ == "__main__":
    test_connection_pooling()
    test_connection_overhead_comparison()
    print(f"\n🎉 Connection pooling tests completed!")
