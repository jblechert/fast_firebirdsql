import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebird
import time

def test_query(description, sql, expected_columns):
    """Test a query and report results"""
    print(f"\n=== {description} ===")
    print(f"SQL: {sql}")
    print(f"Expected columns: {expected_columns}")
    
    try:
        start_time = time.time()
        
        # Connect to database
        conn = fast_firebird.connect(
            **DB_CONFIG
        )
        
        # Execute query using cursor/execute/fetchall
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        elapsed = time.time() - start_time
        
        # Show results
        print(f"✅ SUCCESS: {len(rows)} rows returned in {elapsed:.4f} seconds")
        
        # Show first few rows and verify column count
        for i, row in enumerate(rows[:2]):
            print(f"Row {i+1}: {row}")
            if i == 0:  # Check column count on first row
                actual_columns = len(row) if hasattr(row, '__len__') else 1
                print(f"Actual columns: {actual_columns}")
                if actual_columns == expected_columns:
                    print("✅ Column count matches expected!")
                else:
                    print(f"❌ Column count mismatch! Expected {expected_columns}, got {actual_columns}")
        
        if len(rows) > 2:
            print(f"... and {len(rows) - 2} more rows")

        # Show performance metrics
        metrics = cur.get_last_metrics()
        if metrics:
            print(f"Performance metrics: {metrics}")

        # Close connection
        conn.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    print("Testing fast_firebird with unlimited column support")
    print("=" * 60)
    
    # Test 1: Single column
    test_query(
        "1 Column - COUNT function",
        "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
        1
    )
    
    # Test 2: Two columns
    test_query(
        "2 Columns - Two fields",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        2
    )
    
    # Test 3: Three columns
    test_query(
        "3 Columns - Three fields",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        3
    )
    
    # Test 4: Four columns
    test_query(
        "4 Columns - Four fields",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        4
    )
    
    # Test 5: Five columns (original)
    test_query(
        "5 Columns - Original query",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        5
    )
    
    # Test 6: Six columns - beyond the old limit!
    test_query(
        "6 Columns - Beyond old limit",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT, WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        6
    )
    
    # Test 7: Seven columns
    test_query(
        "7 Columns - Even more columns",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT, WFLARTIKELNUMMER, ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        7
    )
    
    # Test 8: Eight columns
    test_query(
        "8 Columns - Many columns",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT, WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
        8
    )
    
    # Test 9: Ten columns - stress test
    test_query(
        "10 Columns - Stress test",
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT, WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 2",
        10
    )
    
    # Test 10: Complex aggregates with many columns
    test_query(
        "6 Columns - Complex aggregates",
        "SELECT DISPONENT, COUNT(*), MIN(ARTIKELNUMMER), MAX(ARTIKELNUMMER), SUM(WFLARTIKELNUMMER), AVG(WFLARTIKELNUMMER) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 GROUP BY DISPONENT ROWS 3",
        6
    )

if __name__ == "__main__":
    main()
