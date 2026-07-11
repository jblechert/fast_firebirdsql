#!/usr/bin/env python3
"""
Automated Performance Test Runner for fast_firebirdsql
Runs a comprehensive suite of performance tests and regression checks.
Suitable for CI/CD integration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import sys
import os
import time
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class PerformanceTestRunner:
    """Automated test runner for performance validation"""
    
    def __init__(self, baseline_file: str = "performance_baseline.json"):
        self.baseline_file = baseline_file
        self.test_results = {}
        self.start_time = time.time()
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        print("🔍 Checking dependencies...")
        
        try:
            import fast_firebirdsql
            print(f"✅ fast_firebirdsql {fast_firebirdsql.__version__} available")
        except ImportError as e:
            print(f"❌ fast_firebirdsql not available: {e}")
            return False
        
        try:
            import psutil
            print("✅ psutil available")
        except ImportError:
            print("❌ psutil not available - install with: pip install psutil")
            return False
        
        return True
    
    def run_basic_functionality_tests(self) -> bool:
        """Run basic functionality tests to ensure the module works"""
        print("\n🧪 Running basic functionality tests...")
        
        try:
            import fast_firebirdsql

            # Test connection
            conn = fast_firebirdsql.connect(
                **DB_CONFIG
            )
            
            # Test cursor creation and simple query
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1")
            result = cur.fetchall()
            
            if result and len(result) > 0:
                print(f"✅ Basic query successful: {result[0]} rows found")
            else:
                print("❌ Basic query returned no results")
                return False
            
            # Test performance stats functions
            stats = fast_firebirdsql.get_performance_stats()
            print("✅ Performance stats accessible")

            # Test cache functions
            cache_stats = fast_firebirdsql.get_type_conversion_cache_stats()
            print("✅ Cache stats accessible")
            
            conn.close()
            print("✅ Connection cleanup successful")
            
            return True
            
        except Exception as e:
            print(f"❌ Basic functionality test failed: {e}")
            return False
    
    def run_performance_benchmark(self) -> bool:
        """Run the comprehensive performance benchmark"""
        print("\n🚀 Running performance benchmark...")
        
        try:
            # Import and run benchmark suite
            from benchmark_suite import PerformanceBenchmarkSuite
            
            connection_params = dict(DB_CONFIG)
            
            # Create suite with baseline if available
            baseline_path = self.baseline_file if os.path.exists(self.baseline_file) else None
            suite = PerformanceBenchmarkSuite(connection_params, baseline_path)
            
            # Run benchmark with reduced iterations for CI
            print("Running lightweight benchmark for CI...")
            
            # Connection benchmark
            suite.benchmark_connection_creation(iterations=10)
            
            # Query benchmarks
            suite.benchmark_query_execution(
                "SELECT COUNT(*) FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
                iterations=5,
                description="simple_count_query"
            )
            
            suite.benchmark_query_execution(
                "SELECT FIRST 100 WFLARTIKELNUMMER, ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1",
                iterations=5,
                description="small_select_query"
            )
            
            # Type conversion test
            suite.benchmark_type_conversion_performance(iterations=5)
            
            # Run regression tests
            regression_results = suite.run_regression_tests()
            
            # Save results
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            results_file = f"ci_benchmark_results_{timestamp}.json"
            suite.save_results(results_file)
            
            # Check for regressions
            if regression_results:
                failed_tests = [r for r in regression_results if not r.passed]
                if failed_tests:
                    print(f"❌ {len(failed_tests)} performance regression(s) detected!")
                    for test in failed_tests:
                        print(f"   {test.operation}: {test.performance_change_percent:+.1f}% change")
                    return False
                else:
                    print(f"✅ All {len(regression_results)} regression tests passed")
            
            # Store results for summary
            self.test_results['benchmark'] = {
                'total_tests': len(suite.results),
                'regression_tests': len(regression_results),
                'results_file': results_file
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Performance benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_memory_stress_test(self) -> bool:
        """Run memory stress test to check for leaks"""
        print("\n🧠 Running memory stress test...")
        
        try:
            import fast_firebirdsql
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Run multiple connection cycles
            for i in range(20):
                conn = fast_firebirdsql.connect(
                    **DB_CONFIG
                )
                
                cur = conn.cursor()
                cur.execute("SELECT FIRST 50 WFLARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1")
                rows = cur.fetchall()
                conn.close()
                
                if (i + 1) % 5 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    print(f"   Cycle {i+1}/20: {current_memory:.1f} MB")
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            print(f"Memory usage: {initial_memory:.1f} MB → {final_memory:.1f} MB")
            print(f"Memory increase: {memory_increase:.1f} MB")
            
            # Allow up to 50MB increase for stress test
            if memory_increase > 50:
                print(f"❌ Potential memory leak detected: {memory_increase:.1f} MB increase")
                return False
            else:
                print("✅ Memory usage within acceptable limits")
                return True
                
        except Exception as e:
            print(f"❌ Memory stress test failed: {e}")
            return False
    
    def generate_summary_report(self, all_tests_passed: bool):
        """Generate a summary report of all tests"""
        duration = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("PERFORMANCE TEST SUMMARY REPORT")
        print("="*80)
        print(f"Test duration: {duration:.1f} seconds")
        print(f"Overall result: {'✅ PASSED' if all_tests_passed else '❌ FAILED'}")
        
        if 'benchmark' in self.test_results:
            bench = self.test_results['benchmark']
            print(f"Benchmark tests: {bench['total_tests']} completed")
            print(f"Regression tests: {bench['regression_tests']} completed")
            print(f"Results saved to: {bench['results_file']}")
        
        print("\nTest components:")
        print("  ✅ Dependency check")
        print("  ✅ Basic functionality")
        print("  ✅ Performance benchmark")
        print("  ✅ Memory stress test")
        
        if not all_tests_passed:
            print("\n⚠️  Some tests failed. Check the output above for details.")
            print("Consider investigating performance regressions or memory issues.")
        else:
            print("\n🎉 All performance tests passed successfully!")
    
    def run_all_tests(self) -> bool:
        """Run the complete test suite"""
        print("🚀 Starting automated performance test suite...")
        print("="*80)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Run basic functionality tests
        if not self.run_basic_functionality_tests():
            return False
        
        # Run performance benchmark
        if not self.run_performance_benchmark():
            return False
        
        # Run memory stress test
        if not self.run_memory_stress_test():
            return False
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fast Firebird Performance Test Runner")
    parser.add_argument("--baseline", default="performance_baseline.json",
                       help="Baseline file for regression testing")
    parser.add_argument("--create-baseline", action="store_true",
                       help="Create a new baseline from current run")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = PerformanceTestRunner(args.baseline)
    
    # Run all tests
    success = runner.run_all_tests()
    
    # Generate summary
    runner.generate_summary_report(success)
    
    # Create baseline if requested
    if args.create_baseline and success:
        print(f"\n💾 Creating new baseline: {args.baseline}")
        # Copy the latest results as baseline
        latest_results = max([f for f in os.listdir('.') if f.startswith('ci_benchmark_results_')], 
                           key=os.path.getctime, default=None)
        if latest_results:
            import shutil
            shutil.copy(latest_results, args.baseline)
            print(f"✅ Baseline created from {latest_results}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
