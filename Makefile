# Makefile for fast_firebirdsql development and testing

# Target environment: the production venv (Python 3.13).
# Override with e.g. `make PYTHON=python3 VENV=/path/to/venv ...`
VENV    ?= /home/mjb/src/bstools-venv
PYTHON  ?= $(VENV)/bin/python
# patchelf only for portable wheels (make wheel); develop installs link system libs
MATURIN ?= VIRTUAL_ENV=$(VENV) uvx maturin

.PHONY: help build build-dev check lint install dev-install test test-performance test-ci benchmark create-baseline clean dev-setup monitor-performance test-all dev release-check

# Default target
help:
	@echo "Fast Firebird SQL Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Build commands:"
	@echo "  build              Build the Rust extension in release mode"
	@echo "  build-dev          Build the Rust extension in debug mode"
	@echo "  install            Build and install into the venv (release)"
	@echo "  dev-install        Build and install into the venv (debug)"
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
	PYO3_PYTHON=$(PYTHON) cargo check

lint:
	@echo "🧹 Running cargo clippy..."
	PYO3_PYTHON=$(PYTHON) cargo clippy -- -D warnings

# Installation commands
install:
	@echo "📦 Installing fast_firebirdsql (release) into $(VENV)..."
	$(MATURIN) develop --uv --release

dev-install:
	@echo "📦 Installing fast_firebirdsql (debug) into $(VENV)..."
	$(MATURIN) develop --uv

wheel:
	@echo "🎡 Building portable release wheel into dist/..."
	VIRTUAL_ENV=$(VENV) uvx --with patchelf maturin build --release -o dist -i $(PYTHON)
	@# patchelf mangles the cached .so in target/ in place; force a relink
	@# so a later `make install` does not pick up the mangled library
	@touch src/lib.rs

wheel-windows:
	@echo "🎡 Cross-building Windows (win_amd64) wheel into dist/..."
	@# Needs mingw-w64 and `rustup target add x86_64-pc-windows-gnu`.
	@# Links against the import libs in windows-firebird/; after installing
	@# the wheel on Windows, run setup_windows_dlls.py once.
	RUSTFLAGS="-L native=$(CURDIR)/windows-firebird" uvx maturin build --release --target x86_64-pc-windows-gnu -o dist -i 3.13

# Test commands
test: dev-install
	@echo "🧪 Running pytest suite (read-only)..."
	$(PYTHON) -m pytest -q

test-write: dev-install
	@echo "🧪 Running pytest suite incl. write tests (creates/drops TEST_FAST_FBSQL)..."
	FIREBIRD_ALLOW_WRITE_TESTS=1 $(PYTHON) -m pytest -q

test-performance: dev-install
	@echo "🚀 Running comprehensive performance tests..."
	$(PYTHON) benchmarks/run_performance_tests.py

test-ci: dev-install
	@echo "⚡ Running CI performance tests..."
	$(PYTHON) benchmarks/run_performance_tests.py --baseline benchmarks/performance_baseline.json

benchmark: dev-install
	@echo "📊 Running full benchmark suite..."
	$(PYTHON) benchmarks/benchmark_suite.py

compare: dev-install
	@echo "⚖️  Comparing against pure-Python firebirdsql..."
	$(PYTHON) benchmarks/compare_drivers.py

create-baseline: dev-install
	@echo "💾 Creating new performance baseline..."
	$(PYTHON) benchmarks/run_performance_tests.py --create-baseline --baseline benchmarks/performance_baseline.json

# Maintenance commands
clean:
	@echo "🧹 Cleaning build artifacts..."
	cargo clean
	rm -rf target/
	rm -rf build/
	rm -f *.so
	rm -f benchmark_results_*.json
	rm -f ci_benchmark_results_*.json

# Performance monitoring
monitor-performance:
	@echo "📈 Starting performance monitoring..."
	$(PYTHON) benchmarks/performance_monitor.py

# Run all tests in sequence
test-all: test test-performance
	@echo "✅ All tests completed!"

# Quick development cycle
dev: clean dev-install test
	@echo "🎉 Development cycle completed!"

# Release preparation
release-check: clean install test test-performance
	@echo "🚀 Release checks completed!"
