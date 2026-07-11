import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql
import time

def test_query(description, sql, expected_columns):
    """Test a query and report results"""
    print(f"\n=== {description} ===")
    print(f"SQL: {sql}")
    print(f"Expected columns: {expected_columns}")
    
    try:
        start_time = time.time()
        
        # Connect to database
        conn = fast_firebirdsql.connect(
            **DB_CONFIG
        )
        
        # Execute query using cursor/execute/fetchall
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        elapsed = time.time() - start_time
        
        # Show results
        print(f"✅ SUCCESS: {len(rows)} rows returned in {elapsed:.4f} seconds")
        
        # Show first few rows
        for i, row in enumerate(rows[:3]):
            print(f"Row {i+1}: {row}")
            if i == 0:  # Check column count on first row
                actual_columns = len(row) if hasattr(row, '__len__') else 1
                print(f"Actual columns: {actual_columns}")
        
        if len(rows) > 3:
            print(f"... and {len(rows) - 3} more rows")

        # Show performance metrics
        metrics = cur.get_last_metrics()
        if metrics:
            print(f"Performance metrics: {metrics}")

        # Close connection
        conn.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    print("Testing fast_firebirdsql with various column counts")
    print("=" * 60)
    
    # Test 1: Single column - COUNT
    test_query(
        "1 Column - COUNT function",
        "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
        1
    )
    
    # Test 2: Single column - SUM
    test_query(
        "1 Column - SUM function", 
        "SELECT SUM(WFLARTIKELNUMMER) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
        1
    )
    
    # Test 3: Single column - simple field
    test_query(
        "1 Column - Single field",
        "SELECT ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 5",
        1
    )
    
    # Test 4: Two columns
    test_query(
        "2 Columns - Two fields",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 5",
        2
    )
    
    # Test 5: Three columns
    test_query(
        "3 Columns - Three fields",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 5",
        3
    )
    
    # Test 6: Four columns
    test_query(
        "4 Columns - Four fields",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 5",
        4
    )
    
    # Test 7: Five columns (original query)
    test_query(
        "5 Columns - Original query",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 5",
        5
    )
    
    # Test 8: COUNT with GROUP BY (2 columns)
    test_query(
        "2 Columns - COUNT with GROUP BY",
        "SELECT DISPONENT, COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 GROUP BY DISPONENT ROWS 5",
        2
    )
    
    # Test 9: Multiple aggregates (3 columns)
    test_query(
        "3 Columns - Multiple aggregates",
        "SELECT DISPONENT, COUNT(*), SUM(WFLARTIKELNUMMER) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 GROUP BY DISPONENT ROWS 5",
        3
    )
    
    # Test 10: Complex query with functions (4 columns)
    test_query(
        "4 Columns - Complex with functions",
        "SELECT DISPONENT, COUNT(*), MIN(ARTIKELNUMMER), MAX(ARTIKELNUMMER) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 GROUP BY DISPONENT ROWS 5",
        4
    )

if __name__ == "__main__":
    main()
