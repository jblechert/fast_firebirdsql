#!/usr/bin/env python3
"""
Optimize the MAX(GEAENDERT_AM) query by addressing performance bottlenecks
in the fast_firebirdsql implementation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql
import time
import sys

def test_current_performance():
    """Test current performance of the MAX query"""
    print("=== Current Performance Analysis ===")
    
    connection_params = dict(DB_CONFIG)
    
    try:
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        # Test the slow query
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        print(f"Testing query: {query}")
        
        # Run multiple times to get average
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  Run {i+1}: {execution_time:.4f}s - Result: {result}")
        
        avg_time = sum(times) / len(times)
        print(f"  Average time: {avg_time:.4f}s")
        
        conn.close()
        return avg_time
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_high_performance_mode():
    """Test with high-performance mode enabled"""
    print("\n=== High-Performance Mode Test ===")
    
    connection_params = dict(DB_CONFIG)
    
    try:
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        # Enable high-performance mode (disables metrics and caching)
        cur.set_high_performance_mode(True)
        print("High-performance mode enabled (no metrics, no caching)")
        
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        # Run multiple times
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  Run {i+1}: {execution_time:.4f}s - Result: {result}")
        
        avg_time = sum(times) / len(times)
        print(f"  Average time: {avg_time:.4f}s")
        
        conn.close()
        return avg_time
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_ultra_fast_execution():
    """Test with ultra-fast execution method"""
    print("\n=== Ultra-Fast Execution Test ===")
    
    connection_params = dict(DB_CONFIG)
    
    try:
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        # Use ultra-fast execution if available
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            try:
                # Try ultra-fast method
                cur.execute_ultra_fast(query)
            except AttributeError:
                # Fall back to regular execute
                print("  Ultra-fast method not available, using regular execute")
                cur.execute(query)
            
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  Run {i+1}: {execution_time:.4f}s - Result: {result}")
        
        avg_time = sum(times) / len(times)
        print(f"  Average time: {avg_time:.4f}s")
        
        conn.close()
        return avg_time
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_connection_reuse():
    """Test performance with connection reuse simulation"""
    print("\n=== Connection Reuse Simulation ===")
    
    connection_params = dict(DB_CONFIG)
    
    try:
        # Create connection once
        conn = fast_firebirdsql.connect(**connection_params)
        cur = conn.cursor()
        cur.set_high_performance_mode(True)
        
        query = "SELECT MAX(GEAENDERT_AM) FROM AUFPOS"
        
        print("Testing multiple queries on same connection...")
        
        # Run multiple queries quickly
        times = []
        for i in range(5):
            start_time = time.perf_counter()
            cur.execute(query)
            result = cur.fetchone()
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  Query {i+1}: {execution_time:.4f}s")
        
        avg_time = sum(times) / len(times)
        print(f"  Average time: {avg_time:.4f}s")
        
        conn.close()
        return avg_time
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def compare_with_standard_firebirdsql():
    """Compare with standard firebirdsql library"""
    print("\n=== Comparison with Standard firebirdsql ===")
    
    try:
        import firebirdsql
        
        connection_params = dict(DB_CONFIG)
        
        # Test standard firebirdsql
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
    """Main optimization test"""
    print("MAX Query Performance Optimization")
    print("=" * 50)
    
    # Test current performance
    current_time = test_current_performance()
    
    # Test high-performance mode
    hp_time = test_high_performance_mode()
    
    # Test ultra-fast execution
    ultra_time = test_ultra_fast_execution()
    
    # Test connection reuse
    reuse_time = test_connection_reuse()
    
    # Compare with standard library
    standard_time = compare_with_standard_firebirdsql()
    
    # Summary
    print("\n" + "=" * 50)
    print("PERFORMANCE SUMMARY")
    print("=" * 50)
    
    if current_time:
        print(f"Current implementation:     {current_time:.4f}s")
    
    if hp_time:
        print(f"High-performance mode:      {hp_time:.4f}s")
        if current_time:
            improvement = current_time / hp_time
            print(f"  → {improvement:.2f}x faster than current")
    
    if ultra_time:
        print(f"Ultra-fast execution:       {ultra_time:.4f}s")
        if current_time:
            improvement = current_time / ultra_time
            print(f"  → {improvement:.2f}x faster than current")
    
    if reuse_time:
        print(f"Connection reuse:           {reuse_time:.4f}s")
        if current_time:
            improvement = current_time / reuse_time
            print(f"  → {improvement:.2f}x faster than current")
    
    if standard_time:
        print(f"Standard firebirdsql:       {standard_time:.4f}s")
        if current_time:
            if standard_time < current_time:
                ratio = current_time / standard_time
                print(f"  → Standard is {ratio:.2f}x faster")
            else:
                ratio = standard_time / current_time
                print(f"  → fast_firebirdsql is {ratio:.2f}x faster")
    
    print("\nRECOMMENDations:")
    print("1. Use cur.set_high_performance_mode(True) for simple queries")
    print("2. Reuse connections when possible")
    print("3. Consider implementing connection pooling")
    print("4. The main bottleneck appears to be connection creation overhead")

if __name__ == "__main__":
    main()
