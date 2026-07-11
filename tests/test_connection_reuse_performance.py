#!/usr/bin/env python3
"""
Test script to validate connection reuse performance improvements.
This script tests the performance before and after connection reuse implementation.
"""

import sys
import os
import time

# Add the target directory to Python path
sys.path.insert(0, '/home/mjb/src/fast_firebirdsql/target/release')

try:
    import fast_firebirdsql
    print("✅ Successfully imported fast_firebirdsql")
except ImportError as e:
    print(f"❌ Failed to import fast_firebirdsql: {e}")
    print("Make sure the library is built with: cargo build --release")
    sys.exit(1)

# Database connection parameters - using the user's actual database
HOST = "192.0.2.10"
DATABASE = "d:\\data\\example.fdb"
PORT = 3050
USER = "EXAMPLE_USER"
PASSWORD = "REDACTED"

def test_connection_reuse():
    """Test connection reuse performance"""
    print("\n🔥 Testing Connection Reuse Performance")
    print("=" * 50)
    
    try:
        # Connect to database
        print(f"Connecting to {HOST}:{PORT}/{DATABASE}")
        conn = fast_firebirdsql.connect(HOST, DATABASE, PORT, USER, PASSWORD)
        cursor = conn.cursor()
        print("✅ Connected successfully")
        
        # Test 1: Simple query performance (should be < 0.01s with connection reuse)
        print("\n📊 Test 1: Simple Query Performance")
        print("-" * 30)
        
        simple_query = "SELECT 1 FROM RDB$DATABASE"
        times = []
        
        for i in range(5):
            start_time = time.time()
            cursor.execute(simple_query)
            result = cursor.fetchone()
            end_time = time.time()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"Run {i+1}: {execution_time:.6f}s - Result: {result}")
        
        avg_time = sum(times) / len(times)
        print(f"\n📈 Average time: {avg_time:.6f}s")
        
        if avg_time < 0.01:
            print("✅ PASS: Simple query < 0.01s (connection reuse working!)")
        else:
            print("❌ FAIL: Simple query >= 0.01s (connection reuse may not be working)")
        
        # Test 2: MAX query performance (should be < 0.50s with connection reuse)
        print("\n📊 Test 2: MAX Query Performance")
        print("-" * 30)
        
        # Use the AUFPOS table that we know exists
        max_query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        times = []
        
        for i in range(3):
            start_time = time.time()
            cursor.execute(max_query)
            result = cursor.fetchone()
            end_time = time.time()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"Run {i+1}: {execution_time:.6f}s - Result: {result}")
        
        avg_time = sum(times) / len(times)
        print(f"\n📈 Average time: {avg_time:.6f}s")
        
        if avg_time < 0.50:
            print("✅ PASS: MAX query < 0.50s (connection reuse working!)")
        else:
            print("❌ FAIL: MAX query >= 0.50s (connection reuse may not be working)")
        
        # Test 3: Connection reuse validation
        print("\n📊 Test 3: Connection Reuse Validation")
        print("-" * 30)
        
        # Execute multiple queries on the same cursor to verify connection reuse
        queries = [
            "SELECT 1 FROM RDB$DATABASE",
            "SELECT 2 FROM RDB$DATABASE", 
            "SELECT 3 FROM RDB$DATABASE",
            "SELECT COUNT(*) FROM AUFPOS",
            "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        ]
        
        total_start = time.time()
        for i, query in enumerate(queries):
            start_time = time.time()
            cursor.execute(query)
            result = cursor.fetchone()
            end_time = time.time()
            
            execution_time = end_time - start_time
            print(f"Query {i+1}: {execution_time:.6f}s - {query[:30]}...")
        
        total_time = time.time() - total_start
        print(f"\n📈 Total time for 5 queries: {total_time:.6f}s")
        print(f"📈 Average per query: {total_time/5:.6f}s")
        
        if total_time < 0.1:  # Should be very fast with connection reuse
            print("✅ PASS: Multiple queries very fast (connection reuse working!)")
        else:
            print("❌ FAIL: Multiple queries slow (connection reuse may not be working)")
        
        # Clean up
        cursor.close()
        conn.close()
        print("\n✅ Connection closed successfully")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_connection_creation_overhead():
    """Test connection creation overhead by creating multiple connections"""
    print("\n🔗 Testing Connection Creation Overhead")
    print("=" * 50)
    
    try:
        times = []
        for i in range(3):
            start_time = time.time()
            conn = fast_firebirdsql.connect(HOST, DATABASE, PORT, USER, PASSWORD)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM RDB$DATABASE")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            end_time = time.time()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"Connection {i+1}: {execution_time:.6f}s")
        
        avg_time = sum(times) / len(times)
        print(f"\n📈 Average connection creation + query: {avg_time:.6f}s")
        
        if avg_time < 0.2:
            print("✅ PASS: Connection creation reasonably fast")
        else:
            print("❌ SLOW: Connection creation is slow")
            
    except Exception as e:
        print(f"❌ Error during connection overhead test: {e}")

if __name__ == "__main__":
    print("🚀 Fast Firebird SQL - Connection Reuse Performance Test")
    print("=" * 60)
    
    test_connection_reuse()
    test_connection_creation_overhead()
    
    print("\n🎯 Test Summary")
    print("=" * 20)
    print("Expected improvements with connection reuse:")
    print("- Simple queries: < 0.01s (was ~0.32s)")
    print("- MAX queries: < 0.50s (was ~0.78s)")
    print("- Multiple queries on same cursor: Very fast")
    print("\nIf tests pass, connection reuse is working! 🎉")
