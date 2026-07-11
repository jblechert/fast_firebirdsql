#!/usr/bin/env python3
"""
Debug why fetchone() returns None for most queries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql

def debug_results():
    """Debug result processing"""
    print("=== Debugging Result Processing ===")
    
    connection_params = dict(DB_CONFIG)
    
    conn = fast_firebirdsql.connect(**connection_params)
    cur = conn.cursor()
    
    # Test simple queries
    queries = [
        "SELECT 1 FROM RDB$DATABASE",
        "SELECT 'hello' FROM RDB$DATABASE",
        "SELECT CURRENT_TIMESTAMP FROM RDB$DATABASE",
        "SELECT COUNT(*) FROM RDB$DATABASE",
    ]
    
    for query in queries:
        print(f"\nTesting: {query}")
        try:
            cur.execute(query)
            print(f"  Execute successful")
            
            # Try fetchone
            result = cur.fetchone()
            print(f"  fetchone(): {result}")
            
            # Try fetchall
            cur.execute(query)  # Re-execute
            results = cur.fetchall()
            print(f"  fetchall(): {results}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test the problematic MAX query
    print(f"\nTesting MAX query:")
    try:
        cur.execute("SELECT MAX(GEAENDERT_AM) FROM AUFPOS")
        print(f"  Execute successful")
        
        result = cur.fetchone()
        print(f"  fetchone(): {result}")
        
        # Re-execute and try fetchall
        cur.execute("SELECT MAX(GEAENDERT_AM) FROM AUFPOS")
        results = cur.fetchall()
        print(f"  fetchall(): {results}")
        
    except Exception as e:
        print(f"  Error: {e}")
    
    conn.close()

if __name__ == "__main__":
    debug_results()
