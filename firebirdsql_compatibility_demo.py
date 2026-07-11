#!/usr/bin/env python3
"""
Demonstration of firebirdsql compatibility.
This shows how fast_firebirdsql can now be used as a drop-in replacement for firebirdsql.
"""

import fast_firebirdsql
import time

def demo_firebirdsql_style():
    """Demonstrate using fast_firebirdsql exactly like firebirdsql"""
    print("Using fast_firebirdsql with firebirdsql-style interface:")
    print("=" * 60)

    start_time = time.time()

    # This is now identical to how you would use firebirdsql:
    # import firebirdsql
    # conn = firebirdsql.connect(...)

    conn = fast_firebirdsql.connect(
        host="192.0.2.10",  # 192.0.2.10 - example-server
        database="d:\\data\\example.fdb",
        port=3050,
        user="EXAMPLE_USER",
        password="REDACTED",
    )
    
    # Create cursor (just like firebirdsql)
    cur = conn.cursor()
    
    # Execute query (just like firebirdsql)
    sql_string = "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"
    cur.execute(sql_string)
    
    # Fetch results (just like firebirdsql)
    rows = cur.fetchall()
    
    # Process results (just like firebirdsql)
    for i, row in enumerate(rows[:5]):  # Show first 5 rows
        print(f"Row {i+1}: {row}")
    
    print(f"\nTotal rows: {len(rows)}")
    print(f"Time: {time.time() - start_time:.4f} seconds")
    
    # Close connection (just like firebirdsql)
    conn.close()
    print("Connection closed.")

def show_code_comparison():
    """Show side-by-side code comparison"""
    print("\n" + "=" * 80)
    print("CODE COMPARISON:")
    print("=" * 80)
    
    firebirdsql_code = '''
# Original firebirdsql code:
import firebirdsql
conn = firebirdsql.connect(host="...", database="...", port=3050, user="...", password="...")
cur = conn.cursor()
cur.execute("SELECT * FROM table")
rows = cur.fetchall()
conn.close()
'''
    
    fast_firebird_code = '''
# fast_firebird code (identical interface):
import fast_firebird
conn = fast_firebird.connect(host="...", database="...", port=3050, user="...", password="...")
cur = conn.cursor()
cur.execute("SELECT * FROM table")
rows = cur.fetchall()
conn.close()
'''
    
    print("BEFORE (firebirdsql):")
    print(firebirdsql_code)
    print("AFTER (fast_firebird):")
    print(fast_firebird_code)
    print("✅ Only the import statement needs to change!")

if __name__ == "__main__":
    demo_firebirdsql_style()
    show_code_comparison()
