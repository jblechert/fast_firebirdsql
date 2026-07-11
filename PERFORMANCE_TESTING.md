# Performance Testing Framework

This document describes the comprehensive performance testing and benchmarking framework for fast_firebirdsql.

## Overview

The performance testing framework provides:

- **Automated Performance Benchmarks**: Comprehensive testing of all major operations
- **Regression Testing**: Automated detection of performance degradations
- **Memory Leak Detection**: Stress testing to identify memory issues
- **CI/CD Integration**: Lightweight tests suitable for continuous integration
- **Detailed Metrics**: In-depth analysis of performance characteristics

## Components

### 1. Benchmark Suite (`benchmark_suite.py`)

The main benchmarking framework that provides comprehensive performance testing:

```bash
# Run full benchmark suite
python benchmark_suite.py

# Run with baseline comparison
python benchmark_suite.py --baseline performance_baseline.json

# Save current results as new baseline
python benchmark_suite.py --save-baseline

# Set custom regression threshold (default: 10%)
python benchmark_suite.py --threshold 15.0
```

**Features:**
- Connection creation benchmarks
- Query execution performance testing
- Type conversion optimization testing
- Memory usage analysis
- Statistical analysis (mean, median, std dev)
- Regression testing against baselines

### 2. Automated Test Runner (`run_performance_tests.py`)

Automated test runner suitable for CI/CD pipelines:

```bash
# Run all performance tests
python run_performance_tests.py

# Run with baseline regression testing
python run_performance_tests.py --baseline performance_baseline.json

# Create new baseline from current run
python run_performance_tests.py --create-baseline
```

**Features:**
- Dependency checking
- Basic functionality validation
- Lightweight performance benchmarks
- Memory stress testing
- Automated pass/fail determination
- Summary reporting

### 3. Development Makefile

Convenient commands for development and testing:

```bash
# Show all available commands
make help

# Development setup
make dev-setup

# Run all tests
make test-all

# Run performance tests
make test-performance

# Run CI tests
make test-ci

# Create performance baseline
make create-baseline

# Full development cycle
make dev
```

## Test Categories

### Connection Performance
- Connection creation time
- Connection cleanup efficiency
- Connection reuse optimization

### Query Execution
- Simple queries (COUNT, basic SELECT)
- Complex queries (multi-column SELECT with WHERE)
- Large result set handling
- Type conversion performance

### Memory Management
- Memory usage per operation
- Memory leak detection
- Garbage collection efficiency
- Large dataset handling

### Optimization Features
- Query caching effectiveness
- Type conversion caching
- Prepared statement performance
- Streaming vs. fetchall comparison

## Regression Testing

The framework supports automated regression testing by comparing current performance against established baselines:

### Creating a Baseline
```bash
# Run benchmark and save as baseline
python benchmark_suite.py --save-baseline

# Or use the test runner
python run_performance_tests.py --create-baseline
```

### Running Regression Tests
```bash
# Compare against baseline
python benchmark_suite.py --baseline performance_baseline.json

# Set custom threshold (default: 10% degradation)
python benchmark_suite.py --baseline performance_baseline.json --threshold 5.0
```

### Regression Criteria
- **Pass**: Performance within threshold of baseline
- **Fail**: Performance degraded beyond threshold
- **Metrics**: Mean execution time comparison
- **Threshold**: Configurable percentage (default: 10%)

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Performance Tests
on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install maturin psutil
          make dev-install
      - name: Run performance tests
        run: make test-ci
```

### Exit Codes
- **0**: All tests passed
- **1**: Tests failed (functionality or regression)

## Metrics and Analysis

### Performance Metrics
- **Execution Time**: Mean, median, min, max, standard deviation
- **Throughput**: Rows processed per second
- **Memory Usage**: Peak memory consumption per operation
- **Efficiency**: Memory per row, time per row

### Internal Metrics
The framework also captures fast_firebirdsql's internal metrics:
- Connection time breakdown
- Query execution phases
- Type conversion statistics
- Cache hit/miss ratios

### Output Formats
- **Console**: Human-readable summary
- **JSON**: Machine-readable detailed results
- **Regression Reports**: Pass/fail with change percentages

## Best Practices

### For Development
1. **Run tests before commits**: `make test-all`
2. **Create baselines for major changes**: `make create-baseline`
3. **Monitor performance trends**: Regular benchmark runs
4. **Investigate regressions**: Check failed tests immediately

### For CI/CD
1. **Use lightweight tests**: `make test-ci`
2. **Set appropriate thresholds**: Balance sensitivity vs. noise
3. **Store baselines**: Version control baseline files
4. **Fail builds on regressions**: Enforce performance standards

### For Benchmarking
1. **Consistent environment**: Same hardware, OS, database state
2. **Multiple iterations**: Statistical significance
3. **Warm-up runs**: Account for JIT compilation, caching
4. **Isolated testing**: Minimal background processes

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Install required dependencies
pip install psutil maturin

# Rebuild and install fast_firebird
make dev-install
```

**Database Connection Failures**
- Verify database server is running
- Check connection parameters in test files
- Ensure network connectivity

**Memory Test Failures**
- Close other applications
- Check for actual memory leaks in code
- Adjust memory thresholds if needed

**Performance Regressions**
- Identify specific operations affected
- Compare with previous versions
- Check for environmental factors
- Review recent code changes

### Debug Mode
Add debug output to tests:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- **Parallel execution testing**: Multi-threaded performance
- **Database size scaling**: Performance vs. data volume
- **Network latency simulation**: Remote database testing
- **Comparative benchmarks**: Against other database libraries
- **Automated performance reports**: Trend analysis over time
