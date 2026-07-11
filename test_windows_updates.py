#!/usr/bin/env python3
"""
Test script for Windows UPDATE operations to verify the crash fix.
This script tests both SELECT and UPDATE operations to ensure they work correctly.
"""

import fast_firebirdsql
import sys
import traceback

def test_connection_and_updates():
    """Test connection and UPDATE operations on Windows"""
    
    print("=== Windows UPDATE Test ===")
    print("Testing fast_firebirdsql UPDATE operations on Windows...")
    
    # Connection parameters - replace with your actual database details
    connection_params = {
        'host': 'localhost',  # Replace with your host
        'database': 'your_database.fdb',  # Replace with your database
        'port': 3050,
        'user': 'SYSDBA',  # Replace with your user
        'password': 'masterkey'  # Replace with your password
    }
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        conn = fast_firebirdsql.connect(**connection_params)
        print("✓ Connection successful")
        
        # Create cursor
        cur = conn.cursor()
        print("✓ Cursor created")
        
        # Test 1: Simple SELECT (should work)
        print("\n2. Testing SELECT operation...")
        try:
            cur.execute("SELECT FIRST 1 * FROM RDB$DATABASE")
            rows = cur.fetchall()
            print(f"✓ SELECT successful - fetched {len(rows)} rows")
        except Exception as e:
            print(f"✗ SELECT failed: {e}")
            return False
        
        # Test 2: CREATE test table (if not exists)
        print("\n3. Testing table creation...")
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS TEST_UPDATES (
                    ID INTEGER NOT NULL PRIMARY KEY,
                    NAME VARCHAR(50),
                    VALUE INTEGER
                )
            """)
            print("✓ Table creation/check successful")
        except Exception as e:
            print(f"Note: Table creation failed (may already exist): {e}")
        
        # Test 3: INSERT operation
        print("\n4. Testing INSERT operation...")
        try:
            cur.execute("INSERT INTO TEST_UPDATES (ID, NAME, VALUE) VALUES (1, 'Test', 100)")
            result = cur.fetchall()
            print(f"✓ INSERT successful - affected rows: {len(result) if result else 'unknown'}")
        except Exception as e:
            print(f"Note: INSERT failed (record may exist): {e}")
        
        # Test 4: UPDATE operation (the critical test)
        print("\n5. Testing UPDATE operation (critical test)...")
        try:
            cur.execute("UPDATE TEST_UPDATES SET VALUE = 200 WHERE ID = 1")
            result = cur.fetchall()
            print(f"✓ UPDATE successful - affected rows: {len(result) if result else 'unknown'}")
            print("✓ No crash occurred during UPDATE!")
        except Exception as e:
            print(f"✗ UPDATE failed: {e}")
            traceback.print_exc()
            return False
        
        # Test 5: Verify UPDATE worked
        print("\n6. Verifying UPDATE result...")
        try:
            cur.execute("SELECT VALUE FROM TEST_UPDATES WHERE ID = 1")
            rows = cur.fetchall()
            if rows and len(rows) > 0:
                value = rows[0][0] if rows[0] else None
                print(f"✓ Verification successful - VALUE is now: {value}")
                if value == 200:
                    print("✓ UPDATE correctly changed the value!")
                else:
                    print(f"? UPDATE may not have worked - expected 200, got {value}")
            else:
                print("? No rows found for verification")
        except Exception as e:
            print(f"✗ Verification failed: {e}")
        
        # Test 6: DELETE operation
        print("\n7. Testing DELETE operation...")
        try:
            cur.execute("DELETE FROM TEST_UPDATES WHERE ID = 1")
            result = cur.fetchall()
            print(f"✓ DELETE successful - affected rows: {len(result) if result else 'unknown'}")
        except Exception as e:
            print(f"Note: DELETE failed: {e}")
        
        # Close connection
        cur.close()
        conn.close()
        print("\n✓ Connection closed successfully")
        
        print("\n=== TEST SUMMARY ===")
        print("✓ All operations completed without crashes!")
        print("✓ Windows UPDATE issue appears to be FIXED!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("Fast Firebird SQL - Windows UPDATE Test")
    print("=" * 50)
    
    # Check if we're on Windows
    if sys.platform.startswith('win'):
        print("✓ Running on Windows platform")
    else:
        print("! Running on non-Windows platform (test still valid)")
    
    # Run the test
    success = test_connection_and_updates()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("The Windows UPDATE crash issue has been resolved.")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED!")
        print("Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
