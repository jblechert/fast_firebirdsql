#!/usr/bin/env python3
"""
Test script to verify firebirdsql compatibility of fast_firebirdsql module.
This tests the new execute/fetchall interface and close functionality.
"""

import fast_firebirdsql
import time

def test_new_interface():
    """Test the new firebirdsql-compatible interface"""
    print("Testing new firebirdsql-compatible interface")
    print("=" * 60)
    
    try:
        start_time = time.time()
        
        # Connect to database (same as before)
        conn = fast_firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )
        
        # Create cursor (new firebirdsql-compatible method)
        cur = conn.cursor()
        
        # Execute query (new firebirdsql-compatible method)
        sql_string = "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"
        cur.execute(sql_string)
        
        # Fetch all results (new firebirdsql-compatible method)
        rows = cur.fetchall()
        
        elapsed = time.time() - start_time
        
        # Show results
        print(f"✅ SUCCESS: {len(rows)} rows returned in {elapsed:.4f} seconds")
        
        # Show first few rows
        for i, row in enumerate(rows[:3]):
            print(f"Row {i+1}: {row}")
        
        if len(rows) > 3:
            print(f"... and {len(rows) - 3} more rows")
        
        # Test close functionality
        conn.close()
        print("✅ Connection closed successfully")
        
        # Test that cursor creation fails after close
        try:
            conn.cursor()
            print("❌ ERROR: Should not be able to create cursor after close")
        except Exception as e:
            print(f"✅ Correctly prevented cursor creation after close: {e}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_performance_metrics():
    """Test the new performance metrics functionality"""
    print("\nTesting performance metrics functionality")
    print("=" * 60)

    try:
        start_time = time.time()

        # Clear any existing metrics
        fast_firebirdsql.clear_performance_stats()

        # Connect to database
        conn = fast_firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )

        # Create cursor and execute query
        cur = conn.cursor()
        cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
        rows = cur.fetchall()

        elapsed = time.time() - start_time

        # Show results
        print(f"✅ SUCCESS: {len(rows)} rows returned in {elapsed:.4f} seconds")

        # Show first few rows
        for i, row in enumerate(rows[:3]):
            print(f"Row {i+1}: {row}")

        if len(rows) > 3:
            print(f"... and {len(rows) - 3} more rows")

        # Test performance metrics
        last_metrics = cur.get_last_metrics()
        if last_metrics:
            print(f"✅ Last query metrics: {last_metrics}")
        else:
            print("❌ No metrics available")

        # Test global performance stats
        global_stats = fast_firebirdsql.get_performance_stats()
        if global_stats:
            print(f"✅ Global performance stats: {global_stats}")
        else:
            print("❌ No global stats available")

        conn.close()
        print("✅ Performance metrics test passed")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_multiple_queries():
    """Test multiple queries with the same cursor"""
    print("\nTesting multiple queries with same cursor")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = fast_firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )
        
        cur = conn.cursor()
        
        # First query
        cur.execute("SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1")
        result1 = cur.fetchall()
        print(f"Query 1 result: {result1}")
        
        # Second query
        cur.execute("SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
        result2 = cur.fetchall()
        print(f"Query 2 result: {result2}")
        
        # Third query (using Firebird's FIRST syntax instead of LIMIT)
        cur.execute("SELECT FIRST 5 WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
        result3 = cur.fetchall()
        print(f"Query 3 result: {result3}")
        
        conn.close()
        print("✅ Multiple queries test passed")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_interface()
    test_performance_metrics()
    test_multiple_queries()
    print("\n" + "=" * 60)
    print("All tests completed!")
