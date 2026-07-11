#!/usr/bin/env python3
"""
Analyze where the performance difference between fast_firebirdsql and firebirdsql really comes from.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import time
import sys

def test_connection_overhead():
    """Test just the connection creation overhead"""
    print("=== Connection Creation Overhead Analysis ===")
    
    connection_params = dict(DB_CONFIG)
    
    # Test fast_firebirdsql connection overhead
    print("\n1. fast_firebirdsql connection overhead:")
    import fast_firebirdsql
    
    times = []
    for i in range(3):
        start_time = time.perf_counter()
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        conn.close()
        end_time = time.perf_counter()
        
        connection_time = end_time - start_time
        times.append(connection_time)
        print(f"  Connection {i+1}: {connection_time:.4f}s")
    
    fast_conn_avg = sum(times) / len(times)
    print(f"  Average: {fast_conn_avg:.4f}s")
    
    # Test standard firebirdsql connection overhead
    print("\n2. Standard firebirdsql connection overhead:")
    try:
        import firebirdsql
        
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            conn = firebirdsql.connect(**connection_params)
            cur = conn.cursor()
            conn.close()
            end_time = time.perf_counter()
            
            connection_time = end_time - start_time
            times.append(connection_time)
            print(f"  Connection {i+1}: {connection_time:.4f}s")
        
        std_conn_avg = sum(times) / len(times)
        print(f"  Average: {std_conn_avg:.4f}s")
        
        print(f"\n3. Connection overhead comparison:")
        if fast_conn_avg > std_conn_avg:
            ratio = fast_conn_avg / std_conn_avg
            print(f"  fast_firebirdsql connection is {ratio:.2f}x slower")
        else:
            ratio = std_conn_avg / fast_conn_avg
            print(f"  fast_firebirdsql connection is {ratio:.2f}x faster")
            
    except ImportError:
        print("  Standard firebirdsql not available")

def test_query_execution_overhead():
    """Test the query execution overhead (excluding connection)"""
    print("\n=== Query Execution Overhead Analysis ===")
    
    connection_params = dict(DB_CONFIG)
    
    query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
    
    # Test fast_firebirdsql
    print("\n1. fast_firebirdsql query execution:")
    import fast_firebirdsql
    
    conn = fast_firebirdsql.connect(**connection_params)
    cur = conn.cursor()
    
    # Warm up
    cur.execute(query)
    cur.fetchone()
    
    times = []
    for i in range(5):
        start_time = time.perf_counter()
        cur.execute(query)
        result = cur.fetchone()
        end_time = time.perf_counter()
        
        exec_time = end_time - start_time
        times.append(exec_time)
        print(f"  Execution {i+1}: {exec_time:.4f}s")
    
    fast_exec_avg = sum(times) / len(times)
    print(f"  Average: {fast_exec_avg:.4f}s")
    conn.close()
    
    # Test standard firebirdsql
    print("\n2. Standard firebirdsql query execution:")
    try:
        import firebirdsql
        
        conn = firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        # Warm up
        cur.execute(query)
        cur.fetchone()
        
        times = []
        for i in range(5):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            exec_time = end_time - start_time
            times.append(exec_time)
            print(f"  Execution {i+1}: {exec_time:.4f}s")
        
        std_exec_avg = sum(times) / len(times)
        print(f"  Average: {std_exec_avg:.4f}s")
        conn.close()
        
        print(f"\n3. Query execution comparison:")
        if fast_exec_avg > std_exec_avg:
            ratio = fast_exec_avg / std_exec_avg
            print(f"  fast_firebirdsql execution is {ratio:.2f}x slower")
        else:
            ratio = std_exec_avg / fast_exec_avg
            print(f"  fast_firebirdsql execution is {ratio:.2f}x faster")
            
    except ImportError:
        print("  Standard firebirdsql not available")

def test_rust_python_overhead():
    """Test the Rust-Python conversion overhead"""
    print("\n=== Rust-Python Conversion Overhead Analysis ===")
    
    connection_params = dict(DB_CONFIG)
    
    # Test with different query types to see conversion overhead
    queries = [
        ("Simple integer", "SELECT 1 FROM RDB$DATABASE"),
        ("Simple string", "SELECT 'test' FROM RDB$DATABASE"),
        ("Current timestamp", "SELECT CURRENT_TIMESTAMP FROM RDB$DATABASE"),
        ("MAX query", "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"),
    ]
    
    import fast_firebirdsql
    
    for query_name, query in queries:
        print(f"\n{query_name}: {query}")
        
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            exec_time = end_time - start_time
            times.append(exec_time)
        
        avg_time = sum(times) / len(times)
        print(f"  Average time: {avg_time:.4f}s")
        print(f"  Result type: {type(result[0]) if result and result[0] is not None else 'None'}")
        
        conn.close()

def test_library_import_overhead():
    """Test the library import overhead"""
    print("\n=== Library Import Overhead Analysis ===")
    
    # Test fast_firebirdsql import
    start_time = time.perf_counter()
    import fast_firebirdsql
    end_time = time.perf_counter()
    fast_import_time = end_time - start_time
    print(f"fast_firebirdsql import time: {fast_import_time:.6f}s")
    
    # Test standard firebirdsql import
    try:
        start_time = time.perf_counter()
        import firebirdsql
        end_time = time.perf_counter()
        std_import_time = end_time - start_time
        print(f"firebirdsql import time: {std_import_time:.6f}s")
        
        if fast_import_time > std_import_time:
            ratio = fast_import_time / std_import_time
            print(f"fast_firebirdsql import is {ratio:.2f}x slower")
        else:
            ratio = std_import_time / fast_import_time
            print(f"fast_firebirdsql import is {ratio:.2f}x faster")
            
    except ImportError:
        print("firebirdsql not available for import comparison")

def main():
    """Main analysis function"""
    print("Performance Overhead Source Analysis")
    print("=" * 60)
    
    # Test different sources of overhead
    test_library_import_overhead()
    test_connection_overhead()
    test_query_execution_overhead()
    test_rust_python_overhead()
    
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print("This analysis helps identify where the performance difference comes from:")
    print("1. Library import overhead")
    print("2. Connection creation overhead")
    print("3. Query execution overhead")
    print("4. Data type conversion overhead")
    print("\nThe results will show which component is the main bottleneck.")

if __name__ == "__main__":
    main()
