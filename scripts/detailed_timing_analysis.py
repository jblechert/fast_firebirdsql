#!/usr/bin/env python3
"""
Detailed timing analysis to understand where exactly the time is spent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql
import firebirdsql
import time

def analyze_fast_firebirdsql():
    """Analyze timing breakdown for fast_firebirdsql"""
    print("=== fast_firebirdsql Timing Analysis ===")
    
    connection_params = dict(DB_CONFIG)
    
    # Test connection creation time
    print("1. Connection creation time:")
    times = []
    for i in range(3):
        start = time.perf_counter()
        conn = fast_firebirdsql.connect(**connection_params)
        end = time.perf_counter()
        times.append(end - start)
        print(f"   Connection {i+1}: {end - start:.6f}s")
        conn.close()
    
    avg_conn_time = sum(times) / len(times)
    print(f"   Average connection time: {avg_conn_time:.6f}s")
    
    # Test cursor creation time
    print("\n2. Cursor creation time:")
    conn = fast_firebirdsql.connect(**connection_params)
    times = []
    for i in range(3):
        start = time.perf_counter()
        cur = conn.cursor()
        end = time.perf_counter()
        times.append(end - start)
        print(f"   Cursor {i+1}: {end - start:.6f}s")
    
    avg_cursor_time = sum(times) / len(times)
    print(f"   Average cursor time: {avg_cursor_time:.6f}s")
    
    # Test query execution time on same cursor
    print("\n3. Query execution time (same cursor):")
    cur = conn.cursor()
    query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
    
    times = []
    for i in range(5):
        start = time.perf_counter()
        cur.execute(query)
        exec_end = time.perf_counter()
        result = cur.fetchone()
        fetch_end = time.perf_counter()
        
        exec_time = exec_end - start
        fetch_time = fetch_end - exec_end
        total_time = fetch_end - start
        
        times.append(total_time)
        print(f"   Query {i+1}: execute={exec_time:.4f}s, fetch={fetch_time:.6f}s, total={total_time:.4f}s")
    
    avg_query_time = sum(times) / len(times)
    print(f"   Average query time: {avg_query_time:.4f}s")
    
    conn.close()
    
    return avg_conn_time, avg_cursor_time, avg_query_time

def analyze_standard_firebirdsql():
    """Analyze timing breakdown for standard firebirdsql"""
    print("\n=== Standard firebirdsql Timing Analysis ===")
    
    try:
        connection_params = dict(DB_CONFIG)
        
        # Test connection creation time
        print("1. Connection creation time:")
        times = []
        for i in range(3):
            start = time.perf_counter()
            conn = firebirdsql.connect(**connection_params)
            end = time.perf_counter()
            times.append(end - start)
            print(f"   Connection {i+1}: {end - start:.6f}s")
            conn.close()
        
        avg_conn_time = sum(times) / len(times)
        print(f"   Average connection time: {avg_conn_time:.6f}s")
        
        # Test cursor creation time
        print("\n2. Cursor creation time:")
        conn = firebirdsql.connect(**connection_params)
        times = []
        for i in range(3):
            start = time.perf_counter()
            cur = conn.cursor()
            end = time.perf_counter()
            times.append(end - start)
            print(f"   Cursor {i+1}: {end - start:.6f}s")
        
        avg_cursor_time = sum(times) / len(times)
        print(f"   Average cursor time: {avg_cursor_time:.6f}s")
        
        # Test query execution time on same cursor
        print("\n3. Query execution time (same cursor):")
        cur = conn.cursor()
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        times = []
        for i in range(5):
            start = time.perf_counter()
            cur.execute(query)
            exec_end = time.perf_counter()
            result = cur.fetchone()
            fetch_end = time.perf_counter()
            
            exec_time = exec_end - start
            fetch_time = fetch_end - exec_end
            total_time = fetch_end - start
            
            times.append(total_time)
            print(f"   Query {i+1}: execute={exec_time:.4f}s, fetch={fetch_time:.6f}s, total={total_time:.4f}s")
        
        avg_query_time = sum(times) / len(times)
        print(f"   Average query time: {avg_query_time:.4f}s")
        
        conn.close()
        
        return avg_conn_time, avg_cursor_time, avg_query_time
        
    except ImportError:
        print("Standard firebirdsql not available")
        return None, None, None

def test_connection_reuse_hypothesis():
    """Test if fast_firebirdsql really creates new connections for each execute"""
    print("\n=== Connection Reuse Test ===")
    
    connection_params = dict(DB_CONFIG)
    
    conn = fast_firebirdsql.connect(**connection_params)
    cur = conn.cursor()
    
    # Test simple queries that should be very fast if connection is reused
    simple_queries = [
        "SELECT 1 FROM RDB$DATABASE",
        "SELECT 2 FROM RDB$DATABASE",
        "SELECT 3 FROM RDB$DATABASE",
    ]
    
    print("Testing simple queries (should be fast if connection is reused):")
    for i, query in enumerate(simple_queries):
        start = time.perf_counter()
        cur.execute(query)
        result = cur.fetchone()
        end = time.perf_counter()
        
        exec_time = end - start
        print(f"   Query {i+1} '{query}': {exec_time:.4f}s")
        
        # If connection reuse worked, these should be much faster than 0.2s
        if exec_time > 0.1:
            print(f"      ❌ Too slow! Connection is likely being recreated")
        else:
            print(f"      ✅ Fast! Connection might be reused")
    
    conn.close()

def main():
    """Main analysis function"""
    print("Detailed Timing Analysis")
    print("=" * 60)
    
    # Analyze both libraries
    fast_conn, fast_cursor, fast_query = analyze_fast_firebirdsql()
    std_conn, std_cursor, std_query = analyze_standard_firebirdsql()
    
    # Test connection reuse hypothesis
    test_connection_reuse_hypothesis()
    
    # Summary
    print("\n" + "=" * 60)
    print("TIMING ANALYSIS SUMMARY")
    print("=" * 60)
    
    if fast_conn and std_conn:
        print(f"Connection creation:")
        print(f"  fast_firebirdsql: {fast_conn:.6f}s")
        print(f"  standard:         {std_conn:.6f}s")
        print(f"  Ratio:            {fast_conn/std_conn:.2f}x")
    
    if fast_cursor and std_cursor:
        print(f"\nCursor creation:")
        print(f"  fast_firebirdsql: {fast_cursor:.6f}s")
        print(f"  standard:         {std_cursor:.6f}s")
        print(f"  Ratio:            {fast_cursor/std_cursor:.2f}x")
    
    if fast_query and std_query:
        print(f"\nQuery execution:")
        print(f"  fast_firebirdsql: {fast_query:.4f}s")
        print(f"  standard:         {std_query:.4f}s")
        print(f"  Ratio:            {fast_query/std_query:.2f}x")
    
    print(f"\nCONCLUSIONS:")
    print(f"- If connection creation times are similar but query times differ,")
    print(f"  then fast_firebirdsql is creating new connections for each execute()")
    print(f"- If simple queries take >0.1s, connection reuse is not working")
    print(f"- The main bottleneck should be identified from these timings")

if __name__ == "__main__":
    main()
