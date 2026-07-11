#!/usr/bin/env python3
"""
Test script for memory management optimization features.
Tests the new fetchone, fetchmany methods and streaming capabilities.
"""

import fast_firebird
import time
import gc
import psutil
import os

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def test_memory_management():
    """Test memory management improvements"""
    print("=== Memory Management Optimization Test ===\n")
    
    # Connection parameters
    connection_params = {
        "host": "192.0.2.10",
        "database": "d:\\data\\example.fdb",
        "port": 3050,
        "user": "EXAMPLE_USER",
        "password": "REDACTED",
    }
    
    # Test 1: Traditional fetchall vs new fetchone/fetchmany
    print("Test 1: Memory usage comparison")
    print("-" * 40)
    
    conn = fast_firebird.connect(**connection_params)
    
    # Test fetchall (loads everything into memory)
    print("Testing fetchall (traditional approach):")
    cur1 = conn.cursor()
    
    gc.collect()  # Force garbage collection
    memory_before = get_memory_usage()
    
    start_time = time.perf_counter()
    cur1.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    rows_all = cur1.fetchall()
    end_time = time.perf_counter()
    
    memory_after = get_memory_usage()
    memory_used_fetchall = memory_after - memory_before
    
    print(f"  Rows fetched: {len(rows_all)}")
    print(f"  Time: {end_time - start_time:.4f} seconds")
    print(f"  Memory used: {memory_used_fetchall:.2f} MB")
    
    # Get metrics
    metrics = cur1.get_last_metrics()
    if metrics:
        print(f"  Estimated memory (metrics): {metrics.get('memory_allocated_bytes', 0) / 1024 / 1024:.2f} MB")
    
    # Test fetchone (one row at a time)
    print("\nTesting fetchone (streaming approach):")
    cur2 = conn.cursor()
    
    gc.collect()
    memory_before = get_memory_usage()
    
    start_time = time.perf_counter()
    cur2.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    
    row_count = 0
    sample_rows = []
    while True:
        row = cur2.fetchone()
        if row is None:
            break
        row_count += 1
        if row_count <= 5:  # Keep first 5 rows for comparison
            sample_rows.append(row)
    
    end_time = time.perf_counter()
    memory_after = get_memory_usage()
    memory_used_fetchone = memory_after - memory_before
    
    print(f"  Rows fetched: {row_count}")
    print(f"  Time: {end_time - start_time:.4f} seconds")
    print(f"  Memory used: {memory_used_fetchone:.2f} MB")
    print(f"  Memory savings: {memory_used_fetchall - memory_used_fetchone:.2f} MB")
    
    # Test fetchmany (chunked approach)
    print("\nTesting fetchmany (chunked approach):")
    cur3 = conn.cursor()
    cur3.set_chunk_size(100)  # Set chunk size to 100 rows
    
    gc.collect()
    memory_before = get_memory_usage()
    
    start_time = time.perf_counter()
    cur3.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
    
    row_count = 0
    chunk_count = 0
    while True:
        chunk = cur3.fetchmany(100)
        if not chunk:
            break
        chunk_count += 1
        row_count += len(chunk)
        if chunk_count == 1:
            print(f"  First chunk size: {len(chunk)} rows")
    
    end_time = time.perf_counter()
    memory_after = get_memory_usage()
    memory_used_fetchmany = memory_after - memory_before
    
    print(f"  Rows fetched: {row_count}")
    print(f"  Chunks processed: {chunk_count}")
    print(f"  Time: {end_time - start_time:.4f} seconds")
    print(f"  Memory used: {memory_used_fetchmany:.2f} MB")
    
    # Test 2: Cursor position management
    print("\n" + "=" * 50)
    print("Test 2: Cursor position management")
    print("-" * 40)
    
    cur4 = conn.cursor()
    cur4.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0 ROWS 10")
    
    print(f"Initial position: {cur4.get_position()}")
    print(f"Total rows: {cur4.get_row_count()}")
    
    # Fetch a few rows
    for i in range(3):
        row = cur4.fetchone()
        print(f"Row {i+1}: {row[0] if row else 'None'}, Position: {cur4.get_position()}")
    
    # Reset position
    cur4.reset_position()
    print(f"After reset, position: {cur4.get_position()}")
    
    # Fetch again
    row = cur4.fetchone()
    print(f"First row after reset: {row[0] if row else 'None'}")
    
    # Test 3: Streaming mode configuration
    print("\n" + "=" * 50)
    print("Test 3: Streaming mode configuration")
    print("-" * 40)
    
    cur5 = conn.cursor()
    print(f"Default streaming mode: {cur5.is_streaming_mode()}")
    print(f"Default chunk size: {cur5.get_chunk_size()}")
    
    cur5.set_streaming_mode(True)
    cur5.set_chunk_size(50)
    
    print(f"After configuration - Streaming: {cur5.is_streaming_mode()}")
    print(f"After configuration - Chunk size: {cur5.get_chunk_size()}")
    
    # Verify data consistency
    print("\n" + "=" * 50)
    print("Test 4: Data consistency verification")
    print("-" * 40)
    
    # Compare first few rows from different methods
    print("Comparing first 3 rows from different fetch methods:")
    for i in range(min(3, len(rows_all), len(sample_rows))):
        fetchall_row = rows_all[i]
        fetchone_row = sample_rows[i]
        
        print(f"Row {i+1}:")
        print(f"  fetchall:  {fetchall_row}")
        print(f"  fetchone:  {fetchone_row}")
        print(f"  Match: {fetchall_row == fetchone_row}")
    
    conn.close()
    print("\n=== Memory Management Test Complete ===")

if __name__ == "__main__":
    test_memory_management()
