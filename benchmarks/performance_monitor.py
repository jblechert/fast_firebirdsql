#!/usr/bin/env python3
"""
Performance monitoring utilities for fast_firebird.
Provides comprehensive performance testing and benchmarking capabilities.
"""

import fast_firebird
import time
import psutil
import statistics
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark"""
    operation: str
    iterations: int
    mean_time: float
    median_time: float
    std_dev: float
    min_time: float
    max_time: float
    rows_processed: int
    memory_usage_mb: float
    rows_per_second: float


class PerformanceMonitor:
    """Comprehensive performance monitoring for fast_firebird"""
    
    def __init__(self, connection_params: Dict[str, Any]):
        self.connection_params = connection_params
        self.results: List[BenchmarkResult] = []
    
    @contextmanager
    def measure_memory(self):
        """Context manager to measure memory usage"""
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        yield
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        self.last_memory_usage = mem_after - mem_before
    
    def benchmark_connection_creation(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark connection creation overhead"""
        print(f"Benchmarking connection creation ({iterations} iterations)...")
        
        times = []
        total_memory = 0
        
        for i in range(iterations):
            with self.measure_memory():
                start = time.perf_counter()
                conn = fast_firebird.connect(**self.connection_params)
                conn.close()
                end = time.perf_counter()
            
            times.append(end - start)
            total_memory += self.last_memory_usage
            
            if (i + 1) % 10 == 0:
                print(f"  Completed {i + 1}/{iterations} iterations")
        
        result = BenchmarkResult(
            operation="connection_creation",
            iterations=iterations,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            min_time=min(times),
            max_time=max(times),
            rows_processed=0,
            memory_usage_mb=total_memory / iterations,
            rows_per_second=0
        )
        
        self.results.append(result)
        return result
    
    def benchmark_query_execution(self, sql: str, iterations: int = 50, 
                                 description: str = "query_execution") -> BenchmarkResult:
        """Benchmark query execution performance"""
        print(f"Benchmarking {description} ({iterations} iterations)...")
        
        # Establish connection once
        conn = fast_firebird.connect(**self.connection_params)
        cur = conn.cursor()
        
        times = []
        total_memory = 0
        total_rows = 0
        
        try:
            for i in range(iterations):
                with self.measure_memory():
                    start = time.perf_counter()
                    cur.execute(sql)
                    rows = cur.fetchall()
                    end = time.perf_counter()
                
                times.append(end - start)
                total_memory += self.last_memory_usage
                total_rows = len(rows)  # All iterations should return same number of rows
                
                if (i + 1) % 10 == 0:
                    print(f"  Completed {i + 1}/{iterations} iterations")
        
        finally:
            conn.close()
        
        mean_time = statistics.mean(times)
        rows_per_second = total_rows / mean_time if mean_time > 0 else 0
        
        result = BenchmarkResult(
            operation=description,
            iterations=iterations,
            mean_time=mean_time,
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            min_time=min(times),
            max_time=max(times),
            rows_processed=total_rows,
            memory_usage_mb=total_memory / iterations,
            rows_per_second=rows_per_second
        )
        
        self.results.append(result)
        return result
    
    def benchmark_multiple_queries(self, iterations: int = 20) -> BenchmarkResult:
        """Benchmark multiple queries with same connection"""
        print(f"Benchmarking multiple queries per connection ({iterations} iterations)...")
        
        queries = [
            "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
            "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
            "SELECT FIRST 5 WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"
        ]
        
        times = []
        total_memory = 0
        total_rows = 0
        
        for i in range(iterations):
            with self.measure_memory():
                start = time.perf_counter()
                
                conn = fast_firebird.connect(**self.connection_params)
                cur = conn.cursor()
                
                iteration_rows = 0
                for query in queries:
                    cur.execute(query)
                    rows = cur.fetchall()
                    iteration_rows += len(rows)
                
                conn.close()
                end = time.perf_counter()
            
            times.append(end - start)
            total_memory += self.last_memory_usage
            total_rows = iteration_rows
            
            if (i + 1) % 5 == 0:
                print(f"  Completed {i + 1}/{iterations} iterations")
        
        mean_time = statistics.mean(times)
        rows_per_second = total_rows / mean_time if mean_time > 0 else 0
        
        result = BenchmarkResult(
            operation="multiple_queries",
            iterations=iterations,
            mean_time=mean_time,
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            min_time=min(times),
            max_time=max(times),
            rows_processed=total_rows,
            memory_usage_mb=total_memory / iterations,
            rows_per_second=rows_per_second
        )
        
        self.results.append(result)
        return result
    
    def print_results(self):
        """Print formatted benchmark results"""
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*80)
        
        for result in self.results:
            print(f"\n{result.operation.upper().replace('_', ' ')}")
            print("-" * 40)
            print(f"Iterations:        {result.iterations}")
            print(f"Mean time:         {result.mean_time*1000:.2f} ms")
            print(f"Median time:       {result.median_time*1000:.2f} ms")
            print(f"Std deviation:     {result.std_dev*1000:.2f} ms")
            print(f"Min time:          {result.min_time*1000:.2f} ms")
            print(f"Max time:          {result.max_time*1000:.2f} ms")
            if result.rows_processed > 0:
                print(f"Rows processed:    {result.rows_processed}")
                print(f"Rows/second:       {result.rows_per_second:.0f}")
            print(f"Memory usage:      {result.memory_usage_mb:.2f} MB")
    
    def save_results(self, filename: str):
        """Save results to JSON file"""
        data = []
        for result in self.results:
            data.append({
                'operation': result.operation,
                'iterations': result.iterations,
                'mean_time_ms': result.mean_time * 1000,
                'median_time_ms': result.median_time * 1000,
                'std_dev_ms': result.std_dev * 1000,
                'min_time_ms': result.min_time * 1000,
                'max_time_ms': result.max_time * 1000,
                'rows_processed': result.rows_processed,
                'memory_usage_mb': result.memory_usage_mb,
                'rows_per_second': result.rows_per_second,
                'timestamp': time.time()
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults saved to {filename}")


def run_comprehensive_benchmark():
    """Run a comprehensive performance benchmark"""
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }
    
    monitor = PerformanceMonitor(connection_params)
    
    print("Starting comprehensive performance benchmark...")
    print("This may take several minutes to complete.\n")
    
    # Test connection creation overhead
    monitor.benchmark_connection_creation(iterations=50)
    
    # Test simple query
    monitor.benchmark_query_execution(
        "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
        iterations=30,
        description="simple_count_query"
    )
    
    # Test complex query with multiple columns
    monitor.benchmark_query_execution(
        "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
        iterations=20,
        description="complex_multi_column_query"
    )
    
    # Test multiple queries per connection
    monitor.benchmark_multiple_queries(iterations=15)
    
    # Print and save results
    monitor.print_results()
    monitor.save_results(f"benchmark_results_{int(time.time())}.json")
    
    # Show fast_firebird internal metrics
    print("\n" + "="*80)
    print("FAST_FIREBIRD INTERNAL METRICS")
    print("="*80)
    stats = fast_firebird.get_performance_stats()
    for operation, metrics in stats.items():
        print(f"\n{operation.upper()}:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    run_comprehensive_benchmark()
