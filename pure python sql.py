
import firebirdsql
import time

start_time = time.time()
conn = firebirdsql.connect(
            host="192.0.2.10",  # 192.0.2.10 - example-server
            database="d:\\data\\example.fdb",
            port=3050,
            user="EXAMPLE_USER",
            password="REDACTED",
        )
cur = conn.cursor()

sql_string = f"select WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT from ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"  # GESPERRT, AKTIV = 1 bedeutet nicht gesperrte Artikel, verringert Laufzeit von 1,4 auf 0,4 Sekunden TODO SUM über GESPERRT für Live-Änderungen
cur.execute(sql_string)
rows=cur.fetchall()
for c in rows:
    print(c)
print(len(rows))
print("%0.8f Sekunden: Daten aus ARTIKELSTAMMDATEN" % (time.time() - start_time))
