#!/usr/bin/env python3
"""
Test script for query optimization features in fast_firebird.
Tests query caching, optimization statistics, and performance improvements.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebird
import time
import sys

def test_query_optimization():
    """Test query optimization features"""
    print("=== Testing Query Optimization Features ===")
    
    # Connection parameters
    connection_params = dict(DB_CONFIG)
    
    try:
        # Clear any existing optimization stats
        fast_firebird.clear_query_optimization_cache()
        fast_firebird.clear_performance_stats()
        
        print("1. Testing basic query execution with optimization...")
        
        # Connect to database
        conn = fast_firebird.connect(**connection_params)
        cur = conn.cursor()
        
        # Check initial optimization status
        opt_status = cur.get_optimization_status()
        print(f"Initial optimization status: {opt_status}")
        
        # Test query
        test_query = "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 LIMIT 100"
        
        # Execute query multiple times to test caching
        print("\n2. Executing query multiple times to test caching...")
        
        execution_times = []
        for i in range(5):
            start_time = time.perf_counter()
            cur.execute(test_query)
            rows = cur.fetchall()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            print(f"Execution {i+1}: {execution_time:.4f}s, {len(rows)} rows")
            
            # Get metrics after each execution
            metrics = cur.get_last_metrics()
            if metrics:
                print(f"  Metrics: {metrics}")
        
        print(f"\nExecution times: {[f'{t:.4f}s' for t in execution_times]}")
        print(f"Average execution time: {sum(execution_times)/len(execution_times):.4f}s")
        
        # Check optimization statistics
        print("\n3. Query optimization statistics:")
        opt_stats = fast_firebird.get_query_optimization_stats()
        print(f"Optimization stats: {opt_stats}")
        
        # Test optimization status after queries
        final_opt_status = cur.get_optimization_status()
        print(f"\nFinal optimization status: {final_opt_status}")
        
        # Test disabling query cache
        print("\n4. Testing with query cache disabled...")
        cur.set_query_cache_enabled(False)
        
        start_time = time.perf_counter()
        cur.execute(test_query)
        rows = cur.fetchall()
        end_time = time.perf_counter()
        
        print(f"Execution with cache disabled: {end_time - start_time:.4f}s, {len(rows)} rows")
        
        # Re-enable cache
        cur.set_query_cache_enabled(True)
        
        # Test different query to verify cache independence
        print("\n5. Testing different query...")
        different_query = "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1"
        
        start_time = time.perf_counter()
        cur.execute(different_query)
        rows = cur.fetchall()
        end_time = time.perf_counter()
        
        print(f"Different query execution: {end_time - start_time:.4f}s, result: {rows[0][0]}")
        
        # Final statistics
        print("\n6. Final statistics:")
        final_opt_stats = fast_firebird.get_query_optimization_stats()
        print(f"Final optimization stats: {final_opt_stats}")
        
        performance_stats = fast_firebird.get_performance_stats()
        print(f"Performance stats: {performance_stats}")
        
        # Test cache clearing
        print("\n7. Testing cache clearing...")
        fast_firebird.clear_query_optimization_cache()
        cleared_stats = fast_firebird.get_query_optimization_stats()
        print(f"Stats after clearing cache: {cleared_stats}")
        
        conn.close()
        print("\n✅ Query optimization tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during query optimization testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_comparison():
    """Compare performance with and without optimization"""
    print("\n=== Performance Comparison Test ===")
    
    connection_params = dict(DB_CONFIG)
    
    try:
        # Clear stats
        fast_firebird.clear_query_optimization_cache()
        fast_firebird.clear_performance_stats()
        
        conn = fast_firebird.connect(**connection_params)
        cur = conn.cursor()
        
        test_query = "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, MATCHCODE FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 LIMIT 50"
        
        # Test with optimization enabled
        print("Testing with optimization enabled...")
        cur.set_query_cache_enabled(True)
        
        optimized_times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(test_query)
            rows = cur.fetchall()
            end_time = time.perf_counter()
            optimized_times.append(end_time - start_time)
            print(f"  Run {i+1}: {end_time - start_time:.4f}s")
        
        # Test with optimization disabled
        print("\nTesting with optimization disabled...")
        cur.set_query_cache_enabled(False)
        
        traditional_times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(test_query)
            rows = cur.fetchall()
            end_time = time.perf_counter()
            traditional_times.append(end_time - start_time)
            print(f"  Run {i+1}: {end_time - start_time:.4f}s")
        
        # Compare results
        avg_optimized = sum(optimized_times) / len(optimized_times)
        avg_traditional = sum(traditional_times) / len(traditional_times)
        
        print(f"\nResults:")
        print(f"Average with optimization: {avg_optimized:.4f}s")
        print(f"Average without optimization: {avg_traditional:.4f}s")
        
        if avg_traditional > avg_optimized:
            improvement = ((avg_traditional - avg_optimized) / avg_traditional) * 100
            print(f"Performance improvement: {improvement:.1f}%")
        else:
            print("No significant performance difference detected")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during performance comparison: {e}")
        return False

if __name__ == "__main__":
    print("Fast Firebird Query Optimization Test Suite")
    print("=" * 50)
    
    success = True
    
    # Run optimization tests
    if not test_query_optimization():
        success = False
    
    # Run performance comparison
    if not test_performance_comparison():
        success = False
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
