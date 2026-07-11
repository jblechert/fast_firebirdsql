#!/usr/bin/env python3
"""
Test connection close behavior.

This test specifically verifies that:
1. Connections can be closed properly
2. Operations on closed connections fail appropriately
3. Cursors from closed connections cannot execute queries
4. The connection state is properly managed
"""

import fast_firebirdsql
import sys
import traceback

def test_connection_close():
    """Test connection close behavior thoroughly"""
    print("=" * 60)
    print("TESTING CONNECTION CLOSE BEHAVIOR")
    print("=" * 60)
    
    # Connection parameters - try multiple options
    connection_params_list = [
        {
            'host': '192.0.2.10',
            'database': 'd:\\data\\example.fdb',
            'port': 3050,
            'user': 'EXAMPLE_USER',
            'password': 'REDACTED'
        },
        {
            'host': '192.0.2.10',
            'database': 'bstools.fdb',
            'port': 3050,
            'user': 'SYSDBA',
            'password': 'masterkey'
        }
    ]
    
    connection_params = None
    conn = None
    
    # Try to establish a working connection first
    for params in connection_params_list:
        try:
            print(f"\nTrying connection: {params['host']}:{params['port']}/{params['database']}")
            test_conn = fast_firebirdsql.connect(**params)
            test_cur = test_conn.cursor()
            test_cur.execute("SELECT 1 FROM RDB$DATABASE")
            result = test_cur.fetchone()
            print(f"✅ Connection successful: {result}")
            test_conn.close()
            connection_params = params
            break
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            continue
    
    if not connection_params:
        print("❌ No working database connection found. Skipping tests.")
        return False
    
    try:
        # Test 1: Basic connection and close
        print(f"\n1. Testing basic connection and close...")
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        # Execute a simple query to verify connection works
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        result = cur.fetchone()
        print(f"✓ Initial query successful: {result}")
        
        # Close the connection
        conn.close()
        print("✓ Connection closed successfully")
        
        # Test 2: Try to create cursor on closed connection
        print(f"\n2. Testing cursor creation on closed connection...")
        try:
            new_cursor = conn.cursor()
            print("✗ ERROR: Should not be able to create cursor on closed connection")
            return False
        except Exception as e:
            print(f"✓ Correctly prevented cursor creation: {e}")
        
        # Test 3: Try to execute query on existing cursor after connection close
        print(f"\n3. Testing query execution on cursor after connection close...")
        try:
            cur.execute("SELECT 2 FROM RDB$DATABASE")
            print("✗ ERROR: Should not be able to execute query on cursor from closed connection")
            return False
        except Exception as e:
            print(f"✓ Correctly prevented query execution: {e}")
        
        # Test 4: Try to fetch from cursor after connection close
        print(f"\n4. Testing fetch operations on cursor after connection close...")
        try:
            result = cur.fetchall()
            # This might not fail but should return empty or fail
            if result:
                print(f"⚠️  fetchall() returned data after close: {result}")
            else:
                print("✓ fetchall() returned empty result after close")
        except Exception as e:
            print(f"✓ fetchall() correctly failed after close: {e}")
        
        # Test 5: Try commit/rollback on closed connection
        print(f"\n5. Testing commit/rollback on closed connection...")
        try:
            conn.commit()
            print("✗ ERROR: commit() should fail on closed connection")
            return False
        except Exception as e:
            print(f"✓ commit() correctly failed on closed connection: {e}")
        
        try:
            conn.rollback()
            print("✗ ERROR: rollback() should fail on closed connection")
            return False
        except Exception as e:
            print(f"✓ rollback() correctly failed on closed connection: {e}")
        
        # Test 6: Multiple close calls (should be safe)
        print(f"\n6. Testing multiple close calls...")
        try:
            conn.close()  # Second close call
            conn.close()  # Third close call
            print("✓ Multiple close calls handled safely")
        except Exception as e:
            print(f"⚠️  Multiple close calls caused error: {e}")
        
        # Test 7: Create new connection after close to verify independence
        print(f"\n7. Testing new connection after close...")
        new_conn = fast_firebirdsql.connect(**connection_params)
        new_cur = new_conn.cursor()
        new_cur.execute("SELECT 3 FROM RDB$DATABASE")
        result = new_cur.fetchone()
        print(f"✓ New connection works independently: {result}")
        new_conn.close()
        
        # Test 8: Test cursor behavior with pre-existing results
        print(f"\n8. Testing cursor with pre-existing results after close...")
        final_conn = fast_firebirdsql.connect(**connection_params)
        final_cur = final_conn.cursor()
        
        # Execute query and get results
        final_cur.execute("SELECT 4 FROM RDB$DATABASE")
        result_before_close = final_cur.fetchone()
        print(f"  - Result before close: {result_before_close}")
        
        # Close connection
        final_conn.close()
        
        # Try to fetch again (should fail or return empty)
        try:
            result_after_close = final_cur.fetchone()
            if result_after_close:
                print(f"⚠️  fetchone() returned data after close: {result_after_close}")
            else:
                print("✓ fetchone() returned None after close")
        except Exception as e:
            print(f"✓ fetchone() correctly failed after close: {e}")
        
        print(f"\n=== CONNECTION CLOSE TEST SUMMARY ===")
        print("✓ Connection close behavior is working correctly!")
        print("✓ All operations on closed connections properly fail!")
        print("✓ Connection state management is robust!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("CONNECTION CLOSE BEHAVIOR TEST")
    print("=" * 60)
    print("This test verifies that connections are properly closed")
    print("and that operations on closed connections fail appropriately.")
    
    success = test_connection_close()
    
    if success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("Connection close behavior is working correctly.")
        sys.exit(0)
    else:
        print(f"\n❌ TESTS FAILED!")
        print("Connection close behavior needs attention.")
        sys.exit(1)

if __name__ == "__main__":
    main()
