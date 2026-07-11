# Makefile for fast_firebirdsql development and testing

.PHONY: help build test test-performance test-ci benchmark clean install dev-install

# Default target
help:
	@echo "Fast Firebird SQL Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Build commands:"
	@echo "  build              Build the Rust extension in release mode"
	@echo "  build-dev          Build the Rust extension in debug mode"
	@echo "  install            Install the package using maturin"
	@echo "  dev-install        Install in development mode"
	@echo ""
	@echo "Test commands:"
	@echo "  test               Run all basic tests"
	@echo "  test-performance   Run comprehensive performance tests"
	@echo "  test-ci            Run lightweight CI performance tests"
	@echo "  benchmark          Run full benchmark suite"
	@echo "  create-baseline    Create new performance baseline"
	@echo ""
	@echo "Maintenance commands:"
	@echo "  clean              Clean build artifacts"
	@echo "  check              Check code with cargo check"
	@echo "  lint               Run cargo clippy for linting"

# Build commands
build:
	@echo "🔨 Building fast_firebirdsql in release mode..."
	cargo build --release

build-dev:
	@echo "🔨 Building fast_firebirdsql in debug mode..."
	cargo build

check:
	@echo "🔍 Checking code with cargo..."
	cargo check

lint:
	@echo "🧹 Running cargo clippy..."
	cargo clippy -- -D warnings

# Installation commands
install: build
	@echo "📦 Installing fast_firebirdsql..."
	maturin develop --release

dev-install: build-dev
	@echo "📦 Installing fast_firebirdsql in development mode..."
	maturin develop

# Test commands
test: dev-install
	@echo "🧪 Running basic functionality tests..."
	python tests/test_imports.py
	python tests/test_firebirdsql_compatibility.py
	python tests/test_v0_2_0.py

test-performance: dev-install
	@echo "🚀 Running comprehensive performance tests..."
	python benchmarks/run_performance_tests.py

test-ci: dev-install
	@echo "⚡ Running CI performance tests..."
	python benchmarks/run_performance_tests.py --baseline benchmarks/performance_baseline.json

benchmark: dev-install
	@echo "📊 Running full benchmark suite..."
	python benchmarks/benchmark_suite.py

create-baseline: dev-install
	@echo "💾 Creating new performance baseline..."
	python benchmarks/run_performance_tests.py --create-baseline --baseline benchmarks/performance_baseline.json

# Maintenance commands
clean:
	@echo "🧹 Cleaning build artifacts..."
	cargo clean
	rm -rf target/
	rm -rf build/
	rm -rf dist/
	rm -f *.so
	rm -f benchmark_results_*.json
	rm -f ci_benchmark_results_*.json

# Development workflow
dev-setup:
	@echo "🛠️  Setting up development environment..."
	pip install maturin psutil
	$(MAKE) dev-install

# Performance monitoring
monitor-performance:
	@echo "📈 Starting performance monitoring..."
	python benchmarks/performance_monitor.py

# Run all tests in sequence
test-all: test test-performance
	@echo "✅ All tests completed!"

# Quick development cycle
dev: clean dev-install test
	@echo "🎉 Development cycle completed!"

# Release preparation
release-check: clean build install test test-performance
	@echo "🚀 Release checks completed!"
