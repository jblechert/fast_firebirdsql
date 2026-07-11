import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import fast_firebirdsql
import time

print("=== Testing NEW firebirdsql-compatible interface ===")
start_time = time.time()

# New firebirdsql-compatible interface
conn = fast_firebirdsql.connect(
    **DB_CONFIG,
)

# Create cursor (like firebirdsql)
cur = conn.cursor()

# Execute query (like firebirdsql)
sql_string = "SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"
cur.execute(sql_string)

# Fetch all results (like firebirdsql)
rows = cur.fetchall()

# Process results
for i, row in enumerate(rows):
    if i < 5:  # Show first 5 rows
        print(row)
    elif i == 5:
        print("...")
        break

print(f"Total rows: {len(rows)}")
print(f"Time with new interface: {time.time() - start_time:.8f} seconds")

# Close connection (like firebirdsql)
conn.close()

print("\n=== Testing SAME interface (demonstrating consistency) ===")
start_time = time.time()

# Same interface - demonstrating that both examples use the same modern interface
conn2 = fast_firebirdsql.connect(
    **DB_CONFIG,
)

# Use cursor/execute/fetchall interface (same as above)
cur2 = conn2.cursor()
cur2.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
rows = cur2.fetchall()

# Process results
for i, row in enumerate(rows):
    if i < 5:  # Show first 5 rows
        print(row)
    elif i == 5:
        print("...")
        break

print(f"Total rows: {len(rows)}")
print(f"Time with consistent interface: {time.time() - start_time:.8f} seconds")

# Show performance metrics
metrics = cur2.get_last_metrics()
if metrics:
    print(f"Performance metrics: {metrics}")

# Close connection
conn2.close()

print("\n✅ Both examples use the same modern interface!")
print("✅ fast_firebirdsql provides consistent, firebirdsql-compatible interface!")

# Show global performance statistics
print("\n=== Global Performance Statistics ===")
global_stats = fast_firebirdsql.get_performance_stats()
for operation, stats in global_stats.items():
    print(f"{operation}: {stats}")
