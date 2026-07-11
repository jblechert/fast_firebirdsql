#!/usr/bin/env python3
"""
Test connection to the bstools.fdb database
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql
import os

def test_bstools_connection():
    """Test connection to the bstools database"""
    print("Testing connection to bstools.fdb database")
    print("=" * 50)
    
    try:
        # Try to connect to the database
        print("Attempting to connect to d:\\data\\tools.fdb...")
        
        # Same server/credentials as the main config, different database file
        bstools_database = os.environ.get("FIREBIRD_BSTOOLS_DATABASE", "d:\\data\\tools.fdb")
        connection_params = [
            {**DB_CONFIG, 'database': bstools_database}
        ]

        for i, params in enumerate(connection_params, 1):
            print(f"\nAttempt {i}: database={params['database']}")
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
