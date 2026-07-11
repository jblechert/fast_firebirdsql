import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql
import time
from datetime import datetime

def test_comprehensive_types():
    """Comprehensive test of all data types"""
    print("Testing fast_firebirdsql comprehensive type conversion")
    print("=" * 70)

    try:
        # Connect to database
        conn = fast_firebirdsql.connect(
            **DB_CONFIG
        )
        
        # Test various SQL functions and data types
        test_queries = [
            {
                "name": "Arithmetic Operations",
                "sql": "SELECT WFLARTIKELNUMMER + 1, WFLARTIKELNUMMER * 2, WFLARTIKELNUMMER / 3.0 FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 2",
                "description": "Should return: int, int, float"
            },
            {
                "name": "Aggregation Functions",
                "sql": "SELECT COUNT(*), SUM(WFLARTIKELNUMMER), AVG(WFLARTIKELNUMMER), MIN(WFLARTIKELNUMMER), MAX(WFLARTIKELNUMMER) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
                "description": "Should return: int, int, float, int, int"
            },
            {
                "name": "String Functions",
                "sql": "SELECT UPPER(ARTIKELNUMMER), LOWER(ARTIKELNUMMER), SUBSTRING(ARTIKELNUMMER FROM 1 FOR 3) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 2",
                "description": "Should return: str, str, str"
            },
            {
                "name": "NULL Values Test",
                "sql": "SELECT ZEICHNUNGSNUMMER, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 AND (ZEICHNUNGSNUMMER IS NULL OR DISPONENT IS NULL) ROWS 3",
                "description": "Should handle NULL values properly"
            },
            {
                "name": "Boolean-like Operations",
                "sql": "SELECT CASE WHEN WFLARTIKELNUMMER > 1500000 THEN 1 ELSE 0 END FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
                "description": "Should return integers (0 or 1)"
            },
            {
                "name": "Large Numbers",
                "sql": "SELECT WFLARTIKELNUMMER * 1000000 FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 2",
                "description": "Should handle large integers"
            },
            {
                "name": "VDA LAB Data - Real World Test",
                "sql": "SELECT AUFTRAGSNR, ABLADESTELLE, WERK_NR, PACKMITTEL, PACKMITTEL_LIEF, FUELLMENGE, KONTONUMMER, ADRESSNUMMER, LEINGANG_LS, LAUSGANG_LS, LAUSGANG_LSDATUM, LAUSGANG_MENGE, FORTSCHRITT, MENGE_AUFWEG, LAB_NR_NEU, SACHNUMMER FROM VDA_LAB_ZUSATZDATEN WHERE MANDANT = 1 AND KONTONUMMER IS NOT NULL ROWS 3",
                "description": "Real world data with mixed types including potential datetime fields"
            }
        ]
        
        for test in test_queries:
            print(f"\n=== {test['name']} ===")
            print(f"SQL: {test['sql']}")
            print(f"Expected: {test['description']}")
            
            start_time = time.time()
            cur = conn.cursor()
            cur.execute(test['sql'])
            rows = cur.fetchall()
            elapsed = time.time() - start_time
            
            print(f"✅ SUCCESS: {len(rows)} rows returned in {elapsed:.4f} seconds")
            
            # Show first few rows with type information
            for i, row in enumerate(rows[:3]):
                type_info = []
                for j, value in enumerate(row):
                    if value is None:
                        type_info.append("None")
                    else:
                        type_info.append(f"{type(value).__name__}")
                
                print(f"Row {i+1}: {row}")
                print(f"  Types: {', '.join(type_info)}")
            
            if len(rows) > 3:
                print(f"... and {len(rows) - 3} more rows")
        
        # Test edge cases
        print(f"\n=== Edge Cases ===")
        edge_cases = [
            "SELECT 0",  # Zero
            "SELECT -1",  # Negative number
            "SELECT 3.14159",  # Float
            "SELECT ''",  # Empty string
            "SELECT 'Test with spaces and symbols: !@#$%'",  # Special characters
        ]
        
        for sql in edge_cases:
            try:
                rows = conn.query(sql)
                value = rows[0][0]
                print(f"✅ {sql} -> {repr(value)} ({type(value).__name__})")
            except Exception as e:
                print(f"❌ {sql} -> Error: {e}")
        
        # Performance comparison
        print(f"\n=== Performance Test ===")
        large_query = "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"

        start_time = time.time()
        perf_cur = conn.cursor()
        perf_cur.execute(large_query)
        rows = perf_cur.fetchall()
        elapsed = time.time() - start_time
        
        print(f"✅ Large query: {len(rows)} rows in {elapsed:.4f} seconds")
        print(f"   Performance: {len(rows)/elapsed:.0f} rows/second")
        
        # Check that all rows have correct types
        if rows:
            first_row = rows[0]
            type_pattern = [type(val).__name__ if val is not None else 'None' for val in first_row]
            print(f"   Type pattern: {type_pattern}")
            
            # Verify consistency across all rows
            inconsistent_rows = 0
            for i, row in enumerate(rows[:100]):  # Check first 100 rows
                row_types = [type(val).__name__ if val is not None else 'None' for val in row]
                if row_types != type_pattern:
                    inconsistent_rows += 1
            
            if inconsistent_rows == 0:
                print(f"   ✅ Type consistency: All checked rows have consistent types")
            else:
                print(f"   ⚠️  Type consistency: {inconsistent_rows} rows have different type patterns")

        # Show performance metrics
        metrics = perf_cur.get_last_metrics()
        if metrics:
            print(f"Performance metrics: {metrics}")

        # Close connection
        conn.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_types()
