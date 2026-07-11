#!/usr/bin/env python3
"""
Investigate why query execution is slow in fast_firebirdsql.
"""

import time
import fast_firebirdsql

def test_connection_reuse_hypothesis():
    """Test if fast_firebirdsql really creates new connections for each query"""
    print("=== Testing Connection Reuse Hypothesis ===")
    
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    conn = fast_firebirdsql.connect(**connection_params)
    cur = conn.cursor()
    
    # Test multiple queries on the same cursor
    queries = [
        "SELECT 1 FROM RDB$DATABASE",
        "SELECT 2 FROM RDB$DATABASE", 
        "SELECT 3 FROM RDB$DATABASE",
        "SELECT COUNT(*) FROM RDB$DATABASE",
        "SELECT CURRENT_TIMESTAMP FROM RDB$DATABASE"
    ]
    
    print("Testing multiple queries on same cursor:")
    for i, query in enumerate(queries, 1):
        start_time = time.perf_counter()
        cur.execute(query)
        result = cur.fetchone()
        end_time = time.perf_counter()
        
        exec_time = end_time - start_time
        print(f"  Query {i}: {exec_time:.4f}s - {query}")
    
    conn.close()
    
    print("\nIf times are similar (~0.3s each), it confirms each execute() creates a new connection")

def test_simple_vs_complex_queries():
    """Compare simple vs complex queries to isolate the overhead"""
    print("\n=== Simple vs Complex Query Comparison ===")
    
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    queries = [
        ("Simplest", "SELECT 1 FROM RDB$DATABASE"),
        ("Simple string", "SELECT 'hello' FROM RDB$DATABASE"),
        ("System query", "SELECT COUNT(*) FROM RDB$DATABASE"),
        ("Table count", "SELECT COUNT(*) FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG = 0"),
        ("Complex MAX", "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"),
    ]
    
    conn = fast_firebirdsql.connect(**connection_params)
    cur = conn.cursor()
    
    for query_name, query in queries:
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        print(f"{query_name:15}: {avg_time:.4f}s avg - {query}")
    
    conn.close()

def test_fetchone_vs_fetchall_overhead():
    """Test if fetchall vs fetchone makes a difference"""
    print("\n=== fetchone() vs fetchall() Overhead ===")
    
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
    
    conn = fast_firebirdsql.connect(**connection_params)
    cur = conn.cursor()
    
    # Test fetchone()
    print("Testing fetchone():")
    times = []
    for i in range(3):
        start_time = time.perf_counter()
        cur.execute(query)
        result = cur.fetchone()
        end_time = time.perf_counter()
        times.append(end_time - start_time)
    
    fetchone_avg = sum(times) / len(times)
    print(f"  fetchone() average: {fetchone_avg:.4f}s")
    
    # Test fetchall()
    print("Testing fetchall():")
    times = []
    for i in range(3):
        start_time = time.perf_counter()
        cur.execute(query)
        result = cur.fetchall()
        end_time = time.perf_counter()
        times.append(end_time - start_time)
    
    fetchall_avg = sum(times) / len(times)
    print(f"  fetchall() average: {fetchall_avg:.4f}s")
    
    if fetchone_avg < fetchall_avg:
        ratio = fetchall_avg / fetchone_avg
        print(f"  fetchone() is {ratio:.2f}x faster")
    else:
        ratio = fetchone_avg / fetchall_avg
        print(f"  fetchall() is {ratio:.2f}x faster")
    
    conn.close()

def test_timing_breakdown():
    """Break down timing to see where time is spent"""
    print("\n=== Detailed Timing Breakdown ===")
    
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
    
    # Time connection creation
    start_time = time.perf_counter()
    conn = fast_firebirdsql.connect(**connection_params)
    conn_time = time.perf_counter() - start_time
    
    # Time cursor creation
    start_time = time.perf_counter()
    cur = conn.cursor()
    cursor_time = time.perf_counter() - start_time
    
    # Time query execution only
    start_time = time.perf_counter()
    cur.execute(query)
    execute_time = time.perf_counter() - start_time
    
    # Time result fetching only
    start_time = time.perf_counter()
    result = cur.fetchone()
    fetch_time = time.perf_counter() - start_time
    
    # Time connection closing
    start_time = time.perf_counter()
    conn.close()
    close_time = time.perf_counter() - start_time
    
    total_time = conn_time + cursor_time + execute_time + fetch_time + close_time
    
    print(f"Connection creation: {conn_time:.6f}s ({conn_time/total_time*100:.1f}%)")
    print(f"Cursor creation:     {cursor_time:.6f}s ({cursor_time/total_time*100:.1f}%)")
    print(f"Query execution:     {execute_time:.6f}s ({execute_time/total_time*100:.1f}%)")
    print(f"Result fetching:     {fetch_time:.6f}s ({fetch_time/total_time*100:.1f}%)")
    print(f"Connection closing:  {close_time:.6f}s ({close_time/total_time*100:.1f}%)")
    print(f"Total time:          {total_time:.6f}s")
    print(f"Result: {result}")

def main():
    """Main investigation function"""
    print("Query Overhead Investigation")
    print("=" * 50)
    
    test_connection_reuse_hypothesis()
    test_simple_vs_complex_queries()
    test_fetchone_vs_fetchall_overhead()
    test_timing_breakdown()
    
    print("\n" + "=" * 50)
    print("INVESTIGATION CONCLUSIONS")
    print("=" * 50)
    print("This investigation should reveal:")
    print("1. Whether each execute() really creates a new connection")
    print("2. How much overhead comes from simple vs complex queries")
    print("3. Whether fetch method affects performance")
    print("4. Where exactly the time is spent in the execution pipeline")

if __name__ == "__main__":
    main()
