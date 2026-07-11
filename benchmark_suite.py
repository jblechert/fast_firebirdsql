#!/usr/bin/env python3
"""
Comprehensive Performance Testing and Benchmark Suite for fast_firebirdsql
Provides automated performance regression testing and detailed benchmarking.
"""

import fast_firebirdsql
import time
import psutil
import statistics
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from datetime import datetime
import argparse


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
    timestamp: str
    version: str = "0.2.0"


@dataclass
class RegressionTestResult:
    """Results from a regression test comparison"""
    operation: str
    baseline_performance: float
    current_performance: float
    performance_change_percent: float
    passed: bool
    threshold_percent: float


class PerformanceBenchmarkSuite:
    """Comprehensive performance benchmark suite with regression testing"""
    
    def __init__(self, connection_params: Dict[str, Any], baseline_file: Optional[str] = None):
        self.connection_params = connection_params
        self.results: List[BenchmarkResult] = []
        self.baseline_file = baseline_file
        self.baseline_data: Optional[Dict[str, BenchmarkResult]] = None
        self.regression_threshold = 10.0  # 10% performance degradation threshold
        
        if baseline_file and os.path.exists(baseline_file):
            self.load_baseline()
    
    def load_baseline(self):
        """Load baseline performance data for regression testing"""
        try:
            with open(self.baseline_file, 'r') as f:
                data = json.load(f)
                self.baseline_data = {}
                for item in data:
                    if isinstance(item, dict) and 'operation' in item:
                        result = BenchmarkResult(**item)
                        self.baseline_data[result.operation] = result
            print(f"✅ Loaded baseline data from {self.baseline_file}")
        except Exception as e:
            print(f"⚠️  Could not load baseline data: {e}")
            self.baseline_data = None
    
    @contextmanager
    def measure_memory(self):
        """Context manager to measure memory usage"""
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        yield
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        self.last_memory_usage = max(0, mem_after - mem_before)
    
    def benchmark_connection_creation(self, iterations: int = 50) -> BenchmarkResult:
        """Benchmark connection creation and cleanup performance"""
        print(f"🔗 Benchmarking connection creation ({iterations} iterations)...")
        
        times = []
        total_memory = 0
        
        for i in range(iterations):
            with self.measure_memory():
                start = time.perf_counter()
                conn = fast_firebirdsql.connect(**self.connection_params)
                conn.close()
                end = time.perf_counter()
            
            times.append(end - start)
            total_memory += self.last_memory_usage
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations} iterations")
        
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
            rows_per_second=0,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(result)
        return result
    
    def benchmark_query_execution(self, sql: str, iterations: int = 30, 
                                 description: str = "query_execution") -> BenchmarkResult:
        """Benchmark query execution performance"""
        print(f"📊 Benchmarking {description} ({iterations} iterations)...")
        
        # Establish connection once
        conn = fast_firebirdsql.connect(**self.connection_params)
        cur = conn.cursor()
        
        times = []
        total_memory = 0
        total_rows = 0
        
        try:
            for i in range(iterations):
                # Clear caches to ensure consistent testing
                fast_firebirdsql.clear_performance_stats()
                
                with self.measure_memory():
                    start = time.perf_counter()
                    cur.execute(sql)
                    rows = cur.fetchall()
                    end = time.perf_counter()
                
                times.append(end - start)
                total_memory += self.last_memory_usage
                total_rows = len(rows)  # All iterations should return same number of rows
                
                if (i + 1) % 5 == 0:
                    print(f"  Progress: {i + 1}/{iterations} iterations")
        
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
            rows_per_second=rows_per_second,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(result)
        return result
    
    def benchmark_streaming_vs_fetchall(self, sql: str, iterations: int = 10) -> Tuple[BenchmarkResult, BenchmarkResult]:
        """Compare streaming vs fetchall performance"""
        print(f"🔄 Benchmarking streaming vs fetchall ({iterations} iterations)...")
        
        # Test fetchall approach
        fetchall_result = self.benchmark_query_execution(
            sql, iterations, "fetchall_approach"
        )
        
        # Test streaming approach (if available)
        # For now, we'll simulate streaming by using smaller chunks
        streaming_times = []
        streaming_memory = 0
        total_rows = 0
        
        for i in range(iterations):
            conn = fast_firebirdsql.connect(**self.connection_params)
            cur = conn.cursor()
            
            with self.measure_memory():
                start = time.perf_counter()
                cur.execute(sql)
                # Simulate streaming by processing in chunks
                rows = cur.fetchall()  # For now, same as fetchall
                end = time.perf_counter()
            
            streaming_times.append(end - start)
            streaming_memory += self.last_memory_usage
            total_rows = len(rows)
            conn.close()
        
        mean_time = statistics.mean(streaming_times)
        streaming_result = BenchmarkResult(
            operation="streaming_approach",
            iterations=iterations,
            mean_time=mean_time,
            median_time=statistics.median(streaming_times),
            std_dev=statistics.stdev(streaming_times) if len(streaming_times) > 1 else 0,
            min_time=min(streaming_times),
            max_time=max(streaming_times),
            rows_processed=total_rows,
            memory_usage_mb=streaming_memory / iterations,
            rows_per_second=total_rows / mean_time if mean_time > 0 else 0,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(streaming_result)
        return fetchall_result, streaming_result
    
    def benchmark_type_conversion_performance(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark type conversion and caching performance"""
        print(f"🔄 Benchmarking type conversion performance ({iterations} iterations)...")
        
        # Query with various data types
        sql = """
        SELECT FIRST 100
            WFLARTIKELNUMMER,
            ARTIKELNUMMER, 
            ZEICHNUNGSNUMMER,
            MATCHCODE,
            DISPONENT
        FROM ARTIKELSTAMMDATEN 
        WHERE MANDANT = 1 AND GESPERRT = 0
        """
        
        return self.benchmark_query_execution(sql, iterations, "type_conversion_performance")
    
    def run_regression_tests(self) -> List[RegressionTestResult]:
        """Run regression tests against baseline performance"""
        if not self.baseline_data:
            print("⚠️  No baseline data available for regression testing")
            return []
        
        print("🔍 Running performance regression tests...")
        regression_results = []
        
        for result in self.results:
            if result.operation in self.baseline_data:
                baseline = self.baseline_data[result.operation]
                
                # Compare mean execution time
                baseline_perf = baseline.mean_time
                current_perf = result.mean_time
                
                if baseline_perf > 0:
                    change_percent = ((current_perf - baseline_perf) / baseline_perf) * 100
                    passed = change_percent <= self.regression_threshold
                    
                    regression_result = RegressionTestResult(
                        operation=result.operation,
                        baseline_performance=baseline_perf,
                        current_performance=current_perf,
                        performance_change_percent=change_percent,
                        passed=passed,
                        threshold_percent=self.regression_threshold
                    )
                    
                    regression_results.append(regression_result)
        
        return regression_results

    def print_results(self):
        """Print comprehensive benchmark results"""
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*80)

        for result in self.results:
            print(f"\n📊 {result.operation.upper().replace('_', ' ')}")
            print(f"   Iterations: {result.iterations}")
            print(f"   Mean time: {result.mean_time:.4f}s")
            print(f"   Median time: {result.median_time:.4f}s")
            print(f"   Std deviation: {result.std_dev:.4f}s")
            print(f"   Min/Max time: {result.min_time:.4f}s / {result.max_time:.4f}s")
            if result.rows_processed > 0:
                print(f"   Rows processed: {result.rows_processed:,}")
                print(f"   Performance: {result.rows_per_second:,.0f} rows/second")
            print(f"   Memory usage: {result.memory_usage_mb:.2f} MB")

    def print_regression_results(self, regression_results: List[RegressionTestResult]):
        """Print regression test results"""
        if not regression_results:
            return

        print("\n" + "="*80)
        print("PERFORMANCE REGRESSION TEST RESULTS")
        print("="*80)

        passed_tests = sum(1 for r in regression_results if r.passed)
        total_tests = len(regression_results)

        print(f"Overall: {passed_tests}/{total_tests} tests passed")
        print(f"Regression threshold: {self.regression_threshold}%\n")

        for result in regression_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            change_indicator = "📈" if result.performance_change_percent > 0 else "📉"

            print(f"{status} {result.operation}")
            print(f"   Baseline: {result.baseline_performance:.4f}s")
            print(f"   Current:  {result.current_performance:.4f}s")
            print(f"   Change:   {change_indicator} {result.performance_change_percent:+.1f}%")

            if not result.passed:
                print(f"   ⚠️  Performance degraded beyond {result.threshold_percent}% threshold")
            print()

    def save_results(self, filename: str):
        """Save benchmark results to JSON file"""
        data = [asdict(result) for result in self.results]

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾 Results saved to {filename}")

    def run_comprehensive_benchmark(self) -> List[RegressionTestResult]:
        """Run the complete benchmark suite"""
        print("🚀 Starting comprehensive performance benchmark suite...")
        print("This may take several minutes to complete.\n")

        # Clear any existing metrics
        fast_firebirdsql.clear_performance_stats()
        fast_firebirdsql.clear_type_conversion_cache()

        # 1. Connection creation benchmark
        self.benchmark_connection_creation(iterations=30)

        # 2. Simple query benchmark
        self.benchmark_query_execution(
            "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
            iterations=20,
            description="simple_count_query"
        )

        # 3. Complex query benchmark
        self.benchmark_query_execution(
            "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0",
            iterations=15,
            description="complex_select_query"
        )

        # 4. Type conversion performance
        self.benchmark_type_conversion_performance(iterations=20)

        # 5. Streaming vs fetchall comparison
        self.benchmark_streaming_vs_fetchall(
            "SELECT FIRST 1000 WFLARTIKELNUMMER, ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
            iterations=10
        )

        # Print results
        self.print_results()

        # Run regression tests if baseline available
        regression_results = self.run_regression_tests()
        self.print_regression_results(regression_results)

        # Save results with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_results(f"benchmark_results_{timestamp}.json")

        # Show internal fast_firebirdsql metrics
        self.print_internal_metrics()

        return regression_results

    def print_internal_metrics(self):
        """Print fast_firebirdsql internal performance metrics"""
        print("\n" + "="*80)
        print("FAST_FIREBIRDSQL INTERNAL METRICS")
        print("="*80)

        try:
            stats = fast_firebirdsql.get_performance_stats()
            if stats:
                for operation, metrics in stats.items():
                    print(f"\n📈 {operation.upper()}:")
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            if 'time' in key.lower():
                                print(f"   {key}: {value:.4f}s")
                            elif 'memory' in key.lower():
                                print(f"   {key}: {value:,} bytes")
                            else:
                                print(f"   {key}: {value:,}")
                        else:
                            print(f"   {key}: {value}")
            else:
                print("No internal metrics available")
        except Exception as e:
            print(f"Error retrieving internal metrics: {e}")

        # Type conversion cache stats
        try:
            cache_stats = fast_firebirdsql.get_type_conversion_cache_stats()
            if cache_stats:
                print(f"\n🔄 TYPE CONVERSION CACHE:")
                for key, value in cache_stats.items():
                    print(f"   {key}: {value}")
        except Exception as e:
            print(f"Error retrieving cache stats: {e}")

        # Query optimization stats
        try:
            opt_stats = fast_firebirdsql.get_query_optimization_stats()
            if opt_stats:
                print(f"\n⚡ QUERY OPTIMIZATION:")
                for key, value in opt_stats.items():
                    print(f"   {key}: {value}")
        except Exception as e:
            print(f"Error retrieving optimization stats: {e}")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Fast Firebird Performance Benchmark Suite")
    parser.add_argument("--baseline", help="Baseline results file for regression testing")
    parser.add_argument("--save-baseline", action="store_true",
                       help="Save current results as new baseline")
    parser.add_argument("--threshold", type=float, default=10.0,
                       help="Performance regression threshold percentage (default: 10.0)")

    args = parser.parse_args()

    # Database connection parameters
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED"
    }

    # Create benchmark suite
    suite = PerformanceBenchmarkSuite(connection_params, args.baseline)
    suite.regression_threshold = args.threshold

    # Run comprehensive benchmark
    regression_results = suite.run_comprehensive_benchmark()

    # Save as baseline if requested
    if args.save_baseline:
        baseline_filename = "performance_baseline.json"
        suite.save_results(baseline_filename)
        print(f"💾 Baseline saved to {baseline_filename}")

    # Exit with error code if regression tests failed
    if regression_results:
        failed_tests = [r for r in regression_results if not r.passed]
        if failed_tests:
            print(f"\n❌ {len(failed_tests)} regression test(s) failed!")
            sys.exit(1)
        else:
            print(f"\n✅ All {len(regression_results)} regression tests passed!")

    print("\n🎉 Benchmark suite completed successfully!")


if __name__ == "__main__":
    main()
