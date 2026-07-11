#!/usr/bin/env python3
"""
Test script to analyze and optimize the slow MAX(GEAENDERT_AM) query on AUFPOS table.
"""

import fast_firebirdsql
import time
import sys

def test_slow_max_query():
    """Test the slow MAX query and analyze performance"""
    print("=== Testing MAX(GEAENDERT_AM) Query Performance ===")
    
    # Connection parameters for Family database
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    try:
        # Connect to database
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        print("1. Testing original slow query...")
        
        # The slow query
        slow_query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        # Measure execution time
        start_time = time.perf_counter()
        cur.execute(slow_query)
        result = cur.fetchone()
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        print(f"   Query: {slow_query}")
        print(f"   Result: {result}")
        print(f"   Execution time: {execution_time:.4f} seconds")
        
        if execution_time > 0.1:  # More than 100ms is considered slow for a simple MAX query
            print(f"   ⚠️  Query is slow ({execution_time:.4f}s)")
        else:
            print(f"   ✅ Query is fast ({execution_time:.4f}s)")
        
        print("\n2. Analyzing table structure...")

        # Get table information
        try:
            cur.execute("SELECT COUNT(*) FROM AUFPOS")
            result = cur.fetchone()
            if result:
                row_count = result[0]
                print(f"   AUFPOS table has {row_count:,} rows")
            else:
                print("   Could not get row count")
        except Exception as e:
            print(f"   Could not get row count: {e}")
        
        # Check if GEAENDERT_AM column exists and get its type
        cur.execute("""
            SELECT r.RDB$FIELD_NAME, f.RDB$FIELD_TYPE, f.RDB$FIELD_LENGTH
            FROM RDB$RELATION_FIELDS r
            JOIN RDB$FIELDS f ON r.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME
            WHERE r.RDB$RELATION_NAME = 'AUFPOS' 
            AND r.RDB$FIELD_NAME = 'GEAENDERT_AM'
        """)
        field_info = cur.fetchone()
        if field_info:
            print(f"   GEAENDERT_AM field type: {field_info[1]}, length: {field_info[2]}")
        else:
            print("   ⚠️  GEAENDERT_AM field not found!")
            return
        
        print("\n3. Checking for existing indexes...")
        
        # Check for indexes on GEAENDERT_AM
        cur.execute("""
            SELECT i.RDB$INDEX_NAME, s.RDB$FIELD_NAME
            FROM RDB$INDICES i
            JOIN RDB$INDEX_SEGMENTS s ON i.RDB$INDEX_NAME = s.RDB$INDEX_NAME
            WHERE i.RDB$RELATION_NAME = 'AUFPOS'
            AND s.RDB$FIELD_NAME = 'GEAENDERT_AM'
        """)
        indexes = cur.fetchall()
        
        if indexes:
            print("   Existing indexes on GEAENDERT_AM:")
            for idx in indexes:
                print(f"     - {idx[0]}")
        else:
            print("   ❌ No indexes found on GEAENDERT_AM column")
        
        print("\n4. Testing query plan...")
        
        # Get query execution plan
        try:
            cur.execute(f"SET PLAN ON")
            cur.execute(slow_query)
            # Note: Firebird plan output might not be directly accessible through Python
            print("   Query plan analysis requested")
        except Exception as e:
            print(f"   Could not get query plan: {e}")
        
        print("\n5. Testing alternative query approaches...")
        
        # Test with ORDER BY DESC LIMIT 1 approach
        alt_query = "SELECT GEAENDERT_AM FROM AUFPOS ORDER BY GEAENDERT_AM DESC ROWS 1"
        
        start_time = time.perf_counter()
        cur.execute(alt_query)
        alt_result = cur.fetchone()
        end_time = time.perf_counter()
        
        alt_execution_time = end_time - start_time
        print(f"   Alternative query: {alt_query}")
        print(f"   Result: {alt_result}")
        print(f"   Execution time: {alt_execution_time:.4f} seconds")
        
        if alt_execution_time < execution_time:
            improvement = execution_time / alt_execution_time
            print(f"   🚀 Alternative query is {improvement:.2f}x faster!")
        else:
            print(f"   ⚠️  Alternative query is not faster")
        
        print("\n6. Recommendations:")
        
        if not indexes:
            print("   📝 Create an index on GEAENDERT_AM:")
            print("      CREATE INDEX IDX_AUFPOS_GEAENDERT_AM ON AUFPOS (GEAENDERT_AM);")
        
        if alt_execution_time < execution_time:
            print("   📝 Consider using ORDER BY DESC ROWS 1 instead of MAX() for better performance")
        
        print("   📝 Consider table statistics update:")
        print("      SET STATISTICS INDEX IDX_AUFPOS_GEAENDERT_AM;")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_index_creation():
    """Test creating an index to improve MAX query performance"""
    print("\n=== Testing Index Creation for Optimization ===")
    
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    try:
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        # Check if index already exists
        cur.execute("""
            SELECT RDB$INDEX_NAME 
            FROM RDB$INDICES 
            WHERE RDB$RELATION_NAME = 'AUFPOS' 
            AND RDB$INDEX_NAME = 'IDX_AUFPOS_GEAENDERT_AM'
        """)
        
        existing_index = cur.fetchone()
        
        if existing_index:
            print("   Index IDX_AUFPOS_GEAENDERT_AM already exists")
        else:
            print("   Creating index IDX_AUFPOS_GEAENDERT_AM...")
            
            # Create index
            create_index_sql = "CREATE INDEX IDX_AUFPOS_GEAENDERT_AM ON AUFPOS (GEAENDERT_AM)"
            
            start_time = time.perf_counter()
            cur.execute(create_index_sql)
            conn.commit()
            end_time = time.perf_counter()
            
            print(f"   ✅ Index created in {end_time - start_time:.4f} seconds")
        
        # Update statistics
        print("   Updating index statistics...")
        cur.execute("SET STATISTICS INDEX IDX_AUFPOS_GEAENDERT_AM")
        conn.commit()
        print("   ✅ Statistics updated")
        
        # Test query performance after index creation
        print("   Testing query performance with index...")
        
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        start_time = time.perf_counter()
        cur.execute(query)
        result = cur.fetchone()
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        print(f"   Query execution time with index: {execution_time:.4f} seconds")
        
        if execution_time < 0.1:
            print(f"   🚀 Query is now fast! ({execution_time:.4f}s)")
        else:
            print(f"   ⚠️  Query is still slow ({execution_time:.4f}s)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error during index creation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("MAX Query Optimization Test")
    print("=" * 50)
    
    # Test the slow query first
    test_slow_max_query()
    
    # Ask user if they want to create an index
    if len(sys.argv) > 1 and sys.argv[1] == "--create-index":
        test_index_creation()
    else:
        print("\n💡 To test index creation, run:")
        print("   python test_max_query_optimization.py --create-index")
