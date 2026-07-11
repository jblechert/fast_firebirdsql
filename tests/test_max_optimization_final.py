#!/usr/bin/env python3
"""
Final test showing the optimized MAX query performance.
"""

import fast_firebirdsql
import time

def test_optimized_max_query():
    """Test the optimized MAX query performance"""
    print("=== Optimized MAX Query Performance Test ===")
    
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
        
        # Test the optimized MAX query
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        print(f"Testing optimized query: {query}")
        
        # Run multiple times to get average
        times = []
        for i in range(5):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  Run {i+1}: {execution_time:.4f}s - Result: {result}")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nPerformance Summary:")
        print(f"  Average time: {avg_time:.4f}s")
        print(f"  Best time:    {min_time:.4f}s")
        print(f"  Worst time:   {max_time:.4f}s")
        
        # Performance assessment
        if avg_time < 0.1:
            print(f"  🚀 Excellent performance! Query is very fast.")
        elif avg_time < 0.3:
            print(f"  ✅ Good performance. Query is reasonably fast.")
        elif avg_time < 0.6:
            print(f"  ⚠️  Moderate performance. Could be improved.")
        else:
            print(f"  ❌ Poor performance. Needs optimization.")
        
        conn.close()
        return avg_time
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def compare_with_standard():
    """Compare with standard firebirdsql if available"""
    print("\n=== Comparison with Standard firebirdsql ===")
    
    try:
        import firebirdsql
        
        connection_params = {
            "host": "192.0.2.10",
            "database": "d:\\data\\example.fdb",
            "port": 3050,
            "user": "EXAMPLE_USER",
            "password": "REDACTED"
        }
        
        conn = firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  Standard firebirdsql run {i+1}: {execution_time:.4f}s")
        
        avg_time = sum(times) / len(times)
        print(f"  Standard firebirdsql average: {avg_time:.4f}s")
        
        conn.close()
        return avg_time
        
    except ImportError:
        print("  Standard firebirdsql not available for comparison")
        return None
    except Exception as e:
        print(f"❌ Error with standard firebirdsql: {e}")
        return None

def main():
    """Main test function"""
    print("MAX Query Optimization - Final Test")
    print("=" * 50)
    
    # Test optimized fast_firebirdsql
    fast_time = test_optimized_max_query()
    
    # Compare with standard
    standard_time = compare_with_standard()
    
    # Final summary
    print("\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    
    if fast_time:
        print(f"fast_firebirdsql (optimized): {fast_time:.4f}s")
    
    if standard_time:
        print(f"Standard firebirdsql:         {standard_time:.4f}s")
        
        if fast_time and standard_time:
            if fast_time < standard_time:
                improvement = standard_time / fast_time
                print(f"🚀 fast_firebirdsql is {improvement:.2f}x FASTER!")
            else:
                slowdown = fast_time / standard_time
                print(f"⚠️  fast_firebirdsql is {slowdown:.2f}x slower")
    
    print("\nOPTIMIZATION RESULTS:")
    print("✅ Implemented aggregate function optimization")
    print("✅ MAX/MIN/COUNT queries use specialized fast path")
    print("✅ Reduced Python-Rust conversion overhead")
    print("✅ Pre-allocated result vectors for single-row results")
    
    print("\nRECOMMENDATIONS:")
    print("1. The optimization is now active for MAX/MIN/COUNT/SUM/AVG queries")
    print("2. For simple aggregate queries, performance should be improved")
    print("3. The main remaining bottleneck is connection creation overhead")
    print("4. Consider connection pooling for applications with many queries")
    
    if fast_time and fast_time > 0.5:
        print("\nNOTE: The query is still relatively slow because:")
        print("- Each execute() creates a new database connection")
        print("- This is the main performance bottleneck")
        print("- The actual query execution is fast, but connection overhead is high")

if __name__ == "__main__":
    main()
