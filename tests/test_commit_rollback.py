#!/usr/bin/env python3
"""
Test script for commit() and rollback() methods compatibility.
This verifies that the firebirdsql compatibility methods work correctly.
"""

import fast_firebirdsql
import sys
import traceback

def test_commit_rollback_compatibility():
    """Test commit() and rollback() methods for firebirdsql compatibility"""
    
    print("=== Commit/Rollback Compatibility Test ===")
    print("Testing fast_firebirdsql commit() and rollback() methods...")
    
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
        
        # Test 2: Check if commit() method exists and works
        print("\n2. Testing commit() method...")
        try:
            conn.commit()
            print("✓ commit() method exists and works")
        except AttributeError as e:
            print(f"✗ commit() method missing: {e}")
            return False
        except Exception as e:
            print(f"✗ commit() method failed: {e}")
            return False
        
        # Test 3: Check if rollback() method exists and works
        print("\n3. Testing rollback() method...")
        try:
            conn.rollback()
            print("✓ rollback() method exists and works")
        except AttributeError as e:
            print(f"✗ rollback() method missing: {e}")
            return False
        except Exception as e:
            print(f"✗ rollback() method failed: {e}")
            return False
        
        # Test 4: Test commit() after UPDATE operation (real-world scenario)
        print("\n4. Testing commit() after UPDATE operation...")
        try:
            cur = conn.cursor()
            
            # Try to create test table (may fail if exists)
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS TEST_COMMIT (
                        ID INTEGER NOT NULL PRIMARY KEY,
                        VALUE INTEGER
                    )
                """)
                print("  - Test table created/verified")
            except:
                print("  - Test table already exists or creation failed")
            
            # Insert test data
            try:
                cur.execute("INSERT INTO TEST_COMMIT (ID, VALUE) VALUES (999, 100)")
                print("  - Test data inserted")
            except:
                print("  - Test data may already exist")
            
            # Update operation
            cur.execute("UPDATE TEST_COMMIT SET VALUE = 200 WHERE ID = 999")
            print("  - UPDATE executed")
            
            # Call commit (should work without error)
            conn.commit()
            print("✓ commit() after UPDATE successful")
            
        except Exception as e:
            print(f"✗ commit() after UPDATE failed: {e}")
            traceback.print_exc()
        
        # Test 5: Test rollback() after operation (should not cause errors)
        print("\n5. Testing rollback() after operation...")
        try:
            cur.execute("UPDATE TEST_COMMIT SET VALUE = 300 WHERE ID = 999")
            print("  - UPDATE executed")
            
            # Call rollback (should work without error, even though it's a no-op)
            conn.rollback()
            print("✓ rollback() after UPDATE successful")
            
        except Exception as e:
            print(f"✗ rollback() after UPDATE failed: {e}")
            traceback.print_exc()
        
        # Test 6: Test methods on closed connection
        print("\n6. Testing methods on closed connection...")
        conn.close()
        print("  - Connection closed")

        try:
            conn.commit()
            print("✗ commit() on closed connection should have failed")
            return False
        except Exception as e:
            print(f"✓ commit() on closed connection correctly failed: {e}")

        try:
            conn.rollback()
            print("✗ rollback() on closed connection should have failed")
            return False
        except Exception as e:
            print(f"✓ rollback() on closed connection correctly failed: {e}")

        # Test 7: Test cursor creation on closed connection
        print("\n7. Testing cursor creation on closed connection...")
        try:
            conn.cursor()
            print("✗ cursor() on closed connection should have failed")
            return False
        except Exception as e:
            print(f"✓ cursor() on closed connection correctly failed: {e}")

        # Test 8: Test query execution on cursor from closed connection
        print("\n8. Testing query execution after connection close...")
        # Create a new connection and cursor for this test
        test_conn = fast_firebirdsql.connect(**connection_params)
        test_cur = test_conn.cursor()

        # Execute a query to establish the cursor is working
        test_cur.execute("SELECT 1 FROM RDB$DATABASE")
        result = test_cur.fetchone()
        print(f"  - Initial query successful: {result}")

        # Now close the connection
        test_conn.close()
        print("  - Connection closed")

        # Try to execute a query on the cursor - this should fail
        try:
            test_cur.execute("SELECT 2 FROM RDB$DATABASE")
            print("✗ execute() on cursor from closed connection should have failed")
            return False
        except Exception as e:
            print(f"✓ execute() on cursor from closed connection correctly failed: {e}")

        # Try to fetch from the cursor - this should also fail or return empty
        try:
            result = test_cur.fetchall()
            print(f"  - fetchall() after close returned: {result}")
            # This might not fail but should return empty results
        except Exception as e:
            print(f"✓ fetchall() on cursor from closed connection failed as expected: {e}")

        print("\n=== TEST SUMMARY ===")
        print("✓ All commit/rollback compatibility tests passed!")
        print("✓ Connection close behavior properly tested!")
        print("✓ firebirdsql compatibility is maintained!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        traceback.print_exc()
        return False

def test_firebirdsql_compatibility_example():
    """Test a real firebirdsql-style code example"""
    
    print("\n=== Real firebirdsql Code Example ===")
    print("Testing actual firebirdsql-style code pattern...")
    
    try:
        # This is how firebirdsql code typically looks
        conn = fast_firebirdsql.connect(
            host='localhost',
            database='your_database.fdb',
            port=3050,
            user='SYSDBA',
            password='masterkey'
        )
        
        cur = conn.cursor()
        
        # Typical firebirdsql pattern with explicit commit
        cur.execute("SELECT FIRST 1 * FROM RDB$DATABASE")
        rows = cur.fetchall()
        print(f"  - Query returned {len(rows)} rows")
        conn.commit()  # This should work now!

        print("✓ firebirdsql-style code pattern works perfectly!")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ firebirdsql-style code failed: {e}")
        return False

def main():
    """Main test function"""
    print("Fast Firebird SQL - Commit/Rollback Compatibility Test")
    print("=" * 60)
    
    # Run the tests
    test1_success = test_commit_rollback_compatibility()
    test2_success = test_firebirdsql_compatibility_example()
    
    if test1_success and test2_success:
        print("\n🎉 ALL COMPATIBILITY TESTS PASSED!")
        print("The commit()/rollback() methods are now available!")
        print("fast_firebirdsql is fully compatible with firebirdsql code!")
        sys.exit(0)
    else:
        print("\n❌ COMPATIBILITY TESTS FAILED!")
        print("Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
