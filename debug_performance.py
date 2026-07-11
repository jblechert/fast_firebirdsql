#!/usr/bin/env python3
"""
Debug Performance Issues in fast_firebirdsql
"""

import time
import fast_firebirdsql
import firebirdsql

def test_connection_behavior():
    """Test if connection is actually being established"""
    print("🔍 Testing connection behavior...")
    
    # Test fast_firebirdsql
    print("\n📊 fast_firebirdsql connection test:")
    start = time.time()
    try:
        conn = fast_firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )
        connect_time = time.time() - start
        print(f"   Connection time: {connect_time:.6f}s")
        
        # Test if connection is real
        cur = conn.cursor()
        start = time.time()
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        result = cur.fetchone()
        query_time = time.time() - start
        print(f"   First query time: {query_time:.6f}s")
        print(f"   Result: {result}")
        
        # Test second query (should be faster if caching works)
        start = time.time()
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        result = cur.fetchone()
        query_time2 = time.time() - start
        print(f"   Second query time: {query_time2:.6f}s")
        
        conn.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test standard firebirdsql
    print("\n📊 firebirdsql connection test:")
    start = time.time()
    try:
        conn = firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )
        connect_time = time.time() - start
        print(f"   Connection time: {connect_time:.6f}s")
        
        # Test if connection is real
        cur = conn.cursor()
        start = time.time()
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        result = cur.fetchone()
        query_time = time.time() - start
        print(f"   First query time: {query_time:.6f}s")
        print(f"   Result: {result}")
        
        # Test second query
        start = time.time()
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        result = cur.fetchone()
        query_time2 = time.time() - start
        print(f"   Second query time: {query_time2:.6f}s")
        
        conn.close()
        
    except Exception as e:
        print(f"   Error: {e}")

def test_query_patterns():
    """Test different query patterns"""
    print("\n🔍 Testing query patterns...")
    
    # Test with fast_firebirdsql
    print("\n📊 fast_firebirdsql query patterns:")
    conn = fast_firebirdsql.connect(
        host="192.0.2.10",
        database="d:\\data\\example.fdb",
        port=3050,
        user="EXAMPLE_USER",
        password="REDACTED"
    )
    cur = conn.cursor()
    
    # Simple queries
    queries = [
        "SELECT COUNT(*) FROM RDB$DATABASE",
        "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
        "SELECT FIRST 10 WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
        "SELECT FIRST 100 WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1"
    ]
    
    for i, query in enumerate(queries):
        start = time.time()
        cur.execute(query)
        result = cur.fetchall()
        query_time = time.time() - start
        print(f"   Query {i+1}: {query_time:.6f}s ({len(result)} rows)")
    
    conn.close()
    
    # Test with standard firebirdsql
    print("\n📊 firebirdsql query patterns:")
    conn = firebirdsql.connect(
        host="192.0.2.10",
        database="d:\\data\\example.fdb",
        port=3050,
        user="EXAMPLE_USER",
        password="REDACTED"
    )
    cur = conn.cursor()
    
    for i, query in enumerate(queries):
        start = time.time()
        cur.execute(query)
        result = cur.fetchall()
        query_time = time.time() - start
        print(f"   Query {i+1}: {query_time:.6f}s ({len(result)} rows)")
    
    conn.close()

def test_warmup_effect():
    """Test if there's a warmup effect"""
    print("\n🔍 Testing warmup effect...")
    
    print("\n📊 fast_firebirdsql warmup test:")
    for run in range(3):
        conn = fast_firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )
        cur = conn.cursor()
        
        start = time.time()
        cur.execute("SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1")
        result = cur.fetchone()
        query_time = time.time() - start
        result_value = result[0] if isinstance(result, (list, tuple)) and len(result) > 0 else result
        print(f"   Run {run+1}: {query_time:.6f}s (result: {result_value})")
        
        conn.close()

if __name__ == "__main__":
    test_connection_behavior()
    test_query_patterns()
    test_warmup_effect()
