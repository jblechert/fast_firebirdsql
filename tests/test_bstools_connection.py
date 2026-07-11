#!/usr/bin/env python3
"""
Test connection to the bstools.fdb database
"""

import fast_firebirdsql
import sys

def test_bstools_connection():
    """Test connection to the bstools database"""
    print("Testing connection to bstools.fdb database")
    print("=" * 50)
    
    try:
        # Try to connect to the database
        print("Attempting to connect to d:\\data\\tools.fdb...")
        
        # Try different connection parameters and database paths
        connection_params = [
            {
                'host': '192.0.2.10',
                'database': 'd:\\data\\tools.fdb',
                'port': 3050,
                'user': 'SYSDBA',
                'password': 'masterkey'
            },
            {
                'host': '192.0.2.10',
                'database': 'd:/data/tools.fdb',
                'port': 3050,
                'user': 'SYSDBA',
                'password': 'masterkey'
            },
            {
                'host': '192.0.2.10',
                'database': 'c:\\data\\tools.fdb',
                'port': 3050,
                'user': 'SYSDBA',
                'password': 'masterkey'
            },
            {
                'host': '192.0.2.10',
                'database': 'c:/data/tools.fdb',
                'port': 3050,
                'user': 'SYSDBA',
                'password': 'masterkey'
            },
            {
                'host': '192.0.2.10',
                'database': '\\\\192.0.2.10\\d$\\data\\tools.fdb',
                'port': 3050,
                'user': 'SYSDBA',
                'password': 'masterkey'
            },
            {
                'host': '192.0.2.10',
                'database': 'bstools.fdb',
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
                
                # Close connection
                cursor.close()
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
    success = test_bstools_connection()
    sys.exit(0 if success else 1)
