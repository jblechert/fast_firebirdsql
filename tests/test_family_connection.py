#!/usr/bin/env python3
"""
Test connection to the family.fdb database
"""

import fast_firebirdsql
import sys

def test_family_connection():
    """Test connection to the family database"""
    print("Testing connection to family.fdb database")
    print("=" * 50)
    
    try:
        # Try to connect to the database
        print("Attempting to connect to d:\\data\\example.fdb...")
        
        # Try different connection parameters
        connection_params = [
            {
                'host': '192.0.2.10',
                'database': 'd:\\data\\example.fdb',
                'port': 3050,
                'user': 'EXAMPLE_USER',
                'password': 'REDACTED'
            },
            {
                'host': '192.0.2.10',
                'database': 'd:/data/example.fdb',
                'port': 3050,
                'user': 'EXAMPLE_USER',
                'password': 'REDACTED'
            },
            {
                'host': '192.0.2.10',
                'database': 'd:\\data\\example.fdb',
                'port': 3050,
                'user': 'SYSDBA',
                'password': 'masterkey'
            }
        ]
        
        for i, params in enumerate(connection_params, 1):
            print(f"\nAttempt {i}: {params}")
            try:
                conn = fast_firebirdsql.connect(**params)
                print("✅ Connection successful!")
                
                # Test basic functionality
                cursor = conn.cursor()
                print("✅ Cursor created successfully!")
                
                # Try a simple query
                cursor.execute("SELECT 1 FROM RDB$DATABASE")
                result = cursor.fetchone()
                print(f"✅ Simple query executed successfully: {result}")
                
                # Try to get some table information
                cursor.execute("SELECT COUNT(*) FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG = 0")
                table_count = cursor.fetchone()
                print(f"✅ User tables count: {table_count}")

                # Close connection (cursor.close() not implemented yet)
                conn.close()
                print("✅ Connection closed successfully!")
                
                return True
                
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                continue
        
        print("\n❌ All connection attempts failed")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_family_connection()
    sys.exit(0 if success else 1)
