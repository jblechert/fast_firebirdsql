import fast_firebirdsql
import time

start_time = time.time()
conn = fast_firebirdsql.connect(
            host="192.0.2.10",  # 192.0.2.10 - example-server
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED",
        )

# Use new cursor/execute/fetchall interface
cur = conn.cursor()
cur.execute("SELECT WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT FROM ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0")
rows = cur.fetchall()

# Sollte jetzt korrekt ausgeben:
# ('2004430', '02024539', None, '74,5 86,5 5,3/3Konsi HNBR', None)
for row in rows:
    print(row)

print(len(rows))
print(f"{time.time() - start_time:.8f} Sekunden")

# Show performance metrics
metrics = cur.get_last_metrics()
if metrics:
    print(f"Performance metrics: {metrics}")

# Close connection
conn.close()