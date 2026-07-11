import fast_firebirdsql
import time
from datetime import datetime

def test_type_conversion():
    """Test that values are returned with correct Python types"""
    print("Testing fast_firebirdsql type conversion")
    print("=" * 60)

    try:
        # Connect to database
        conn = fast_firebirdsql.connect(
            host="192.0.2.10",
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED"
        )
        
        # Test different data types
        test_queries = [
            {
                "name": "Integer Test",
                "sql": "SELECT WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
                "expected_type": int,
                "description": "Should return integers"
            },
            {
                "name": "String Test", 
                "sql": "SELECT ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 3",
                "expected_type": str,
                "description": "Should return strings"
            },
            {
                "name": "Count Test",
                "sql": "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
                "expected_type": int,
                "description": "COUNT should return integer"
            },
            {
                "name": "Mixed Types Test",
                "sql": "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 2",
                "expected_types": [int, str, str],
                "description": "Should return mixed types: int, str, str"
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
            
            # Check types for first few rows
            for i, row in enumerate(rows[:3]):
                print(f"Row {i+1}: {row}")
                
                if i == 0:  # Check types on first row
                    if 'expected_types' in test:
                        # Multiple column test
                        for j, (value, expected_type) in enumerate(zip(row, test['expected_types'])):
                            actual_type = type(value).__name__
                            expected_name = expected_type.__name__
                            if isinstance(value, expected_type) or value is None:
                                print(f"  ✅ Column {j+1}: {actual_type} (expected {expected_name})")
                            else:
                                print(f"  ❌ Column {j+1}: {actual_type} (expected {expected_name})")
                    else:
                        # Single column test
                        value = row[0]
                        actual_type = type(value).__name__
                        expected_name = test['expected_type'].__name__
                        if isinstance(value, test['expected_type']) or value is None:
                            print(f"  ✅ Type: {actual_type} (expected {expected_name})")
                        else:
                            print(f"  ❌ Type: {actual_type} (expected {expected_name})")
            
            if len(rows) > 3:
                print(f"... and {len(rows) - 3} more rows")
        
        # Test datetime if available (need to find a table with datetime columns)
        print(f"\n=== Datetime Test ===")
        try:
            # Try to find a datetime column - this might fail if no datetime columns exist
            datetime_sql = "SELECT FIRST 1 * FROM RDB$DATABASE"  # Simple test query
            dt_cur = conn.cursor()
            dt_cur.execute(datetime_sql)
            rows = dt_cur.fetchall()
            print(f"✅ Basic query successful: {len(rows)} rows")
        except Exception as e:
            print(f"ℹ️  Datetime test skipped: {e}")

        # Show performance metrics
        metrics = cur.get_last_metrics()
        if metrics:
            print(f"Performance metrics: {metrics}")

        # Close connection
        conn.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_type_conversion()
